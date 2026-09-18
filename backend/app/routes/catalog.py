"""Archive explorer, immutable evidence timeline and atomic team triage."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from ..catalog_schemas import BulkReview, CatalogExport, CatalogQuery, CatalogSelection
from ..db import dump, now, uid
from ..security import current_user, require_editor
from ..services import catalog
from ..services.history import observation_history
from .product import property_or_404

router = APIRouter(prefix='/api')


@router.get('/catalog')
def search(request: Request, query: CatalogQuery = Query(), user=Depends(current_user)):
    return catalog.search(request.app.state.db, query)


@router.get('/catalog/facets')
def facets(request: Request, user=Depends(current_user)):
    return catalog.facets(request.app.state.db)


@router.post('/catalog/selection')
def selection(body: CatalogSelection, request: Request, user=Depends(current_user)):
    rows = catalog.by_ids(request.app.state.db, body.ids)
    if len(rows) != len(body.ids):
        raise HTTPException(409, 'La selezione è cambiata. Ricarica gli annunci prima di continuare.')
    return {'items':rows}


@router.post('/catalog/review')
def bulk_review(body: BulkReview, request: Request, user=Depends(require_editor)):
    db, timestamp = request.app.state.db, now()
    updated = []
    with db.transaction() as con:
        db.begin_write(con)
        for item in body.items:
            p = con.execute('''SELECT p.review_status,COALESCE(w.version,0) version FROM properties p
                LEFT JOIN deal_work w ON w.property_id=p.id WHERE p.id=? AND p.is_demo=0''', (item.id,)).fetchone()
            if not p or p['version'] != item.version:
                raise HTTPException(409, 'Un annuncio è stato aggiornato o rimosso. Nessuna modifica applicata; ricarica la selezione.')
            if p['review_status'] == body.stage and not body.note:
                continue
            con.execute('UPDATE properties SET review_status=? WHERE id=?', (body.stage, item.id))
            con.execute('''INSERT INTO deal_work(property_id,version,updated_at,updated_by) VALUES(?,?,?,?)
                ON CONFLICT(property_id) DO UPDATE SET version=excluded.version,
                updated_at=excluded.updated_at,updated_by=excluded.updated_by''', (item.id,item.version+1,timestamp,user['id']))
            if body.note:
                con.execute('INSERT INTO notes VALUES(?,?,?,?,?)', (uid(),item.id,user['id'],body.note,timestamp))
            con.execute('INSERT INTO audit_log(user_id,action,target_id,details,created_at) VALUES(?,?,?,?,?)',
                        (user['id'],'deal.bulk_review',item.id,dump({'from':p['review_status'],'to':body.stage,'note_added':bool(body.note)}),timestamp))
            updated.append(item.id)
    return {'updated':updated, 'count':len(updated), 'notice':'Revisione applicata. Assegnazioni, scadenze e checklist sono state conservate.'}


@router.get('/properties/{ident}/history')
def history(ident: str, request: Request, before: str | None = None,
            limit: int = Query(default=30, ge=1, le=50), user=Depends(current_user)):
    db = request.app.state.db
    property_or_404(db, ident)
    return observation_history(db, ident, before, limit)


@router.post('/catalog/export')
def export(body: CatalogExport, request: Request, user=Depends(current_user)):
    from ..services.exports import export_csv, export_xlsx
    rows = catalog.export_rows(request.app.state.db, body.filters)
    if not rows:
        raise ValueError('Nessun annuncio corrisponde ai filtri.')
    data = export_csv(rows) if body.format == 'csv' else export_xlsx(rows)
    mime = 'text/csv; charset=utf-8' if body.format == 'csv' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return Response(data, media_type=mime, headers={
        'Content-Disposition':f'attachment; filename="vedra-opportunita.{body.format}"',
        'X-Vedra-Export-Count':str(len(rows)),
    })
