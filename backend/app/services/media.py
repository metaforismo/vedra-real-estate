"""Authenticated raster delivery from recorded listing URLs and approved hosts."""
import asyncio
from dataclasses import replace
from hashlib import sha256
import time
from urllib.parse import urlsplit

from ..connectors.safe_http import SafeFetcher, SourceBlocked, retry_seconds

CACHE_TTL = 3600
CACHE_FILES = 64
MAX_IMAGE_BYTES = 3_000_000


def raster_type(body: bytes) -> str | None:
    if body.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if body.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if body.startswith(b'RIFF') and body[8:12] == b'WEBP':
        return 'image/webp'
    return None


class ImageStore:
    def __init__(self, settings):
        self.settings = replace(settings, live_domains=settings.image_domains)
        self.root = settings.data_dir / 'image-cache'
        self.domain_locks = {domain: asyncio.Lock() for domain in settings.image_domains}
        self.last_request: dict[str, float] = {}
        self.blocked_until: dict[str, float] = {}
        self.slots = asyncio.Semaphore(3)

    async def get(self, url: str) -> tuple[bytes, str]:
        domain = urlsplit(url).hostname
        if domain not in self.domain_locks:
            raise SourceBlocked('Dominio immagini non autorizzato.')
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / sha256(url.encode()).hexdigest()
        async with self.slots, self.domain_locks[domain]:
            # Each image gets its own request budget, but host pacing survives requests.
            fetcher = SafeFetcher(domain, self.settings)
            fetcher.last_request = self.last_request.get(domain, 0)
            fetcher.validate_url(url)
            if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL:
                body = path.read_bytes()
                mime = raster_type(body)
                if mime and len(body) <= MAX_IMAGE_BYTES:
                    return body, mime
            if self.blocked_until.get(domain, 0) > time.monotonic():
                raise SourceBlocked('Fonte immagini temporaneamente in pausa.')
            try:
                await fetcher.check_robots(url)
                status, headers, body, _ = await fetcher.raw(
                    url, limit=MAX_IMAGE_BYTES, enforce_robots=True)
                if status in (401, 403, 429):
                    raise SourceBlocked('Fonte immagini bloccata o limitata.',
                                        retry_after=retry_seconds(headers.get('retry-after', '')))
                mime = raster_type(body)
                if status != 200 or not mime:
                    raise SourceBlocked('Foto non disponibile o formato non supportato.')
            except SourceBlocked as exc:
                self.blocked_until[domain] = time.monotonic() + max(300, exc.retry_after)
                raise
            finally:
                self.last_request[domain] = fetcher.last_request
            cached = sorted((p for p in self.root.iterdir() if p.is_file()),
                            key=lambda p: p.stat().st_mtime)
            for old in cached[:max(0, len(cached) - CACHE_FILES + 1)]:
                old.unlink(missing_ok=True)
            path.write_bytes(body)
            # Bytes avoid an eviction/FileResponse race after releasing the semaphore.
            return body, mime
