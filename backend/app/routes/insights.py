import httpx

from fastapi import Depends, HTTPException
from fastapi.responses import Response

from ..connectors.safe_http import SourceBlocked
from ..db import load
from ..security import current_user
from ..services.insights import workspace_insights
from ..services.media import ImageStore


def register(app, db, settings):
    images = ImageStore(settings)

    @app.get('/api/insights')
    def insights(user=Depends(current_user)):
        return workspace_insights(db)

    @app.get('/api/properties/{ident}/image')
    async def property_image(ident: str, index:int=0, user=Depends(current_user)):
        row = db.one('SELECT images FROM properties WHERE id=? AND is_demo=0', (ident,))
        if not row:
            raise HTTPException(404, 'Immobile non trovato.')
        urls = load(row['images'], [])
        if not urls or not 0<=index<len(urls):
            raise HTTPException(404, 'Foto non disponibile.')
        try:
            body, mime = await images.get(urls[index])
        except (SourceBlocked, ValueError, OSError, httpx.HTTPError):
            raise HTTPException(404, 'Foto non disponibile o dominio non autorizzato.') from None
        return Response(body, media_type=mime, headers={'Cache-Control': 'private, no-store'})
