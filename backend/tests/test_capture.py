from pathlib import Path

LISTING = (Path(__file__).parent / 'fixtures/html/listing.html').read_text()
EXT = {'Origin': 'chrome-extension://abcdefghijklmnop'}


from contextlib import contextmanager


@contextmanager
def without_session(client):
    # The extension never has the dashboard cookie: drop it for the duration of the block.
    jar = dict(client.cookies)
    client.cookies.clear()
    try:
        yield client
    finally:
        client.cookies.update(jar)


def token(client):
    response = client.post('/api/capture/tokens', json={'label': 'Chrome di Valentina'})
    assert response.status_code == 201 and response.json()['token'].startswith('vcap_')
    return response.json()


def test_extension_sends_a_listing_with_its_own_token(api):
    app, client, _ = api
    created = token(client)
    headers = {**EXT, 'Authorization': 'Bearer ' + created['token'], 'X-CSRF-Token': ''}
    with without_session(client) as bare:
        response = bare.post('/api/capture', json={'url': 'https://www.immobiliare.it/annunci/123456/', 'html': LISTING}, headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body['created'] and body['title']
        again = bare.post('/api/capture', json={'url': 'https://www.immobiliare.it/annunci/123456/', 'html': LISTING}, headers=headers)
        assert again.json()['property_id'] == body['property_id'] and not again.json()['created']
    source = app.state.db.one("SELECT * FROM sources WHERE id='capture-www-immobiliare-it'")
    assert source['kind'] == 'import' and source['name'] == 'Navigazione · immobiliare.it'
    listed = client.get('/api/capture/tokens').json()
    assert listed[0]['last_used_at'] and 'token' not in listed[0]


def test_capture_rejects_bad_tokens_origins_and_non_listing_pages(api):
    app, client, _ = api
    created = token(client)
    with without_session(client) as bare:
        assert bare.post('/api/capture', json={'url': 'https://x.example/1', 'html': LISTING}, headers={**EXT, 'Authorization': 'Bearer vcap_wrong'}).status_code == 401
        good = {'Authorization': 'Bearer ' + created['token']}
        assert bare.post('/api/capture', json={'url': 'https://x.example/1', 'html': LISTING}, headers={**good, 'Origin': 'https://evil.example'}).status_code == 403
        page = '<html><head><title>Mutui</title></head><body><h1>Calcola la rata</h1></body></html>'
        response = bare.post('/api/capture', json={'url': 'https://x.example/mutui', 'html': page}, headers={**EXT, **good})
        assert response.status_code == 422 and 'scheda di un immobile' in response.json()['detail']
        assert bare.post('/api/capture', json={'url': 'javascript:alert(1)//', 'html': LISTING}, headers={**EXT, **good}).status_code == 422
    client.delete(f"/api/capture/tokens/{created['id']}")
    with without_session(client) as bare:
        assert bare.post('/api/capture', json={'url': 'https://x.example/1', 'html': LISTING}, headers={**EXT, 'Authorization': 'Bearer ' + created['token']}).status_code == 401
