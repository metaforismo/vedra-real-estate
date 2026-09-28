"""Portal alert emails: status for Fonti, .eml upload and an on-demand check of the dedicated mailbox."""
import asyncio
import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from ..security import require_editor
from ..services.operations import audit
from ..services.portal_alerts import AlertRejected, check_mailbox, ingest, ingest_html, reap_stale_claims, status

router = APIRouter(prefix='/api/portal-alerts')


class AlertUpload(BaseModel):
    # One file per request: the body stays within the API limit and each file reports its own outcome.
    name: str = Field(default='', max_length=200)
    eml_base64: str | None = Field(default=None, max_length=4_900_000)
    html: str | None = Field(default=None, max_length=2_000_000)

    @model_validator(mode='after')
    def one_payload(self):
        if bool(self.eml_base64) == bool(self.html):
            raise ValueError('Invia un file .eml oppure il testo HTML di un avviso.')
        return self


@router.get('')
def alerts_status(request: Request, user=Depends(require_editor)):
    return status(request.app.state.db, request.app.state.settings)


@router.post('/upload')
def upload(body: AlertUpload, request: Request, user=Depends(require_editor)):
    db, settings = request.app.state.db, request.app.state.settings
    reap_stale_claims(db)
    try:
        if body.html:
            result = ingest_html(db, settings, body.html)
        else:
            try:
                raw = base64.b64decode(body.eml_base64, validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(422, 'File non leggibile: carica l’email salvata in formato .eml.')
            result = ingest(db, settings, raw, channel='upload')
    except AlertRejected as exc:
        raise HTTPException(413, str(exc))
    if result['status'] == 'rejected':
        raise HTTPException(422, 'Email non leggibile: salvala di nuovo dal programma di posta in formato .eml.')
    audit(db, user['id'], 'portal_alert_upload', None, {k: result.get(k) for k in ('status', 'cards', 'created', 'updated')})
    result.pop('property_ids', None)
    return {**result, 'name': body.name}


@router.post('/check')
async def check_now(request: Request, user=Depends(require_editor)):
    db, settings = request.app.state.db, request.app.state.settings
    if not settings.alerts_imap_configured:
        raise HTTPException(409, 'Casella degli avvisi non configurata sul server.')
    # imaplib blocks: run the read-only pass off the event loop.
    result = await asyncio.to_thread(check_mailbox, db, settings)
    audit(db, user['id'], 'portal_alert_check', None, {k: result[k] for k in ('read', 'ignored', 'created', 'updated')})
    return result
