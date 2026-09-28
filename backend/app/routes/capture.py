"""Endpoints for the Vedra Capture browser extension and its personal tokens."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..security import require_editor
from ..services.capture import CaptureRejected, capture, create_token, user_for_token

router = APIRouter(prefix='/api/capture')


class TokenInput(BaseModel):
    label: str = Field(default='Browser', max_length=80)


class CaptureInput(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    html: str = Field(min_length=20, max_length=3_500_000)


@router.get('/tokens')
def tokens(request: Request, user=Depends(require_editor)):
    return request.app.state.db.all('SELECT id,label,created_at,last_used_at FROM capture_tokens WHERE user_id=? ORDER BY created_at DESC', (user['id'],))


@router.post('/tokens', status_code=201)
def add_token(body: TokenInput, request: Request, user=Depends(require_editor)):
    # Shown once: only its hash is stored.
    return create_token(request.app.state.db, user['id'], body.label)


@router.delete('/tokens/{ident}', status_code=204)
def delete_token(ident: str, request: Request, user=Depends(require_editor)):
    request.app.state.db.execute('DELETE FROM capture_tokens WHERE id=? AND user_id=?', (ident, user['id']))


@router.post('')
async def receive(body: CaptureInput, request: Request):
    # Bearer token, no cookies: the extension never holds the dashboard session.
    token = request.headers.get('authorization', '').removeprefix('Bearer ').strip()
    user = user_for_token(request.app.state.db, token)
    if not user or user['role'] not in ('admin', 'analyst'):
        raise HTTPException(401, 'Token di Vedra Capture non valido: generane uno in Impostazioni.')
    try:
        return await capture(request.app.state.engine, user, body.url, body.html)
    except CaptureRejected as exc:
        raise HTTPException(422, str(exc))
