import asyncio

import pytest

from app.connectors.safe_http import SourceBlocked
from app.services import media


class RasterFetcher:
    instances = []
    status = 200

    def __init__(self, domain, settings):
        self.last_request = 0
        self.request_count = 0
        self.instances.append(self)

    def validate_url(self, url):
        return None

    async def check_robots(self, url):
        self.request_count += 1

    async def raw(self, url, **kwargs):
        self.request_count += 1
        self.last_request = 42
        return self.status, {'retry-after': '600'}, b'\x89PNG\r\n\x1a\nfixture', url


@pytest.fixture
def image_store(settings, monkeypatch):
    settings.image_domains = ['images.example.test']
    RasterFetcher.instances = []
    RasterFetcher.status = 200
    monkeypatch.setattr(media, 'SafeFetcher', RasterFetcher)
    return media.ImageStore(settings)


def test_image_cache_is_bounded_and_request_budget_is_not_lifetime(image_store):
    async def run():
        for i in range(102):
            body, mime = await image_store.get(f'https://images.example.test/{i}.png')
            assert body.startswith(b'\x89PNG') and mime == 'image/png'
        assert len(list(image_store.root.iterdir())) == media.CACHE_FILES
        assert max(f.request_count for f in RasterFetcher.instances) == 2
        body, _ = await image_store.get('https://images.example.test/101.png')
        assert body and RasterFetcher.instances[-1].request_count == 0
    asyncio.run(run())


def test_image_backoff_prevents_repeated_upstream_requests(image_store):
    async def run():
        RasterFetcher.status = 429
        with pytest.raises(SourceBlocked):
            await image_store.get('https://images.example.test/a.png')
        RasterFetcher.status = 200
        with pytest.raises(SourceBlocked, match='pausa'):
            await image_store.get('https://images.example.test/b.png')
        assert RasterFetcher.instances[-1].request_count == 0
    asyncio.run(run())


def test_image_url_must_be_allowlisted(image_store):
    with pytest.raises(SourceBlocked, match='autorizzato'):
        asyncio.run(image_store.get('https://other.example.test/a.png'))
    assert RasterFetcher.instances == []
