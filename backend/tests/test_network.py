import socket
import httpx
import pytest
from app.connectors.safe_http import SafeFetcher,SourceBlocked

@pytest.mark.parametrize('url',['http://127.0.0.1/x','http://169.254.169.254/latest/meta-data','http://catalog.example:8080/x','file:///etc/passwd','https://user:secret@catalog.example/a','https://catalog.example.evil/x','https://catalog.example/\\x'])
def test_url_boundary(settings,url):
    with pytest.raises(SourceBlocked):SafeFetcher('catalog.example',settings).validate_url(url)

@pytest.mark.parametrize('ip',['127.0.0.1','10.1.2.3','169.254.169.254','::1','::ffff:127.0.0.1','192.168.1.1'])
async def test_dns_private_denied(settings,monkeypatch,ip):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(socket.AF_INET,socket.SOCK_STREAM,0,'',(ip,80))])
    with pytest.raises(SourceBlocked):await SafeFetcher('catalog.example',settings).resolve('catalog.example',80)

async def test_mixed_public_private_dns_denied(settings,monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(2,1,0,'',('93.184.216.34',80)),(2,1,0,'',('127.0.0.1',80))])
    with pytest.raises(SourceBlocked):await SafeFetcher('catalog.example',settings).resolve('catalog.example',80)


def make_fetch(settings,handler):
    f=SafeFetcher('catalog.example',settings,transport=httpx.MockTransport(handler))
    async def resolve(*_):return '93.184.216.34'
    f.resolve=resolve
    return f

async def test_public_ip_pinned_with_sni(settings):
    calls=[]
    def handler(req):
        calls.append(req)
        assert req.url.host=='93.184.216.34'
        assert req.headers['host']=='catalog.example'
        assert req.extensions['sni_hostname']=='catalog.example'
        return httpx.Response(200,text='User-agent: *\nAllow: /' if req.url.path=='/robots.txt' else '<h1>Test</h1>',headers={'content-type':'text/html'})
    text,url=await make_fetch(settings,handler).get('https://catalog.example/p/1')
    assert text=='<h1>Test</h1>' and len(calls)==2 and url=='https://catalog.example/p/1'

async def test_robots_blocks_before_listing(settings):
    calls=[]
    def handler(req):
        calls.append(req.url.path);return httpx.Response(200,text='User-agent: *\nDisallow: /private',headers={'content-type':'text/plain'})
    with pytest.raises(SourceBlocked):await make_fetch(settings,handler).get('https://catalog.example/private/1')
    assert calls==['/robots.txt']

@pytest.mark.parametrize('status',[401,403,429])
async def test_explicit_block_no_retry(settings,status):
    def handler(req):return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(status,headers={'content-type':'text/html'})
    f=make_fetch(settings,handler)
    with pytest.raises(SourceBlocked):await f.get('https://catalog.example/p/1')
    assert f.request_count==2

@pytest.mark.parametrize('message',['Verify you are human','Please enable JS and disable any ad blocker'])
async def test_challenge_is_not_parsed(settings,message):
    def handler(req):return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(200,text=message,headers={'content-type':'text/html'})
    with pytest.raises(SourceBlocked):await make_fetch(settings,handler).get('https://catalog.example/p/1')

async def test_redirect_cannot_bypass_robots(settings):
    calls=[]
    def handler(req):
        calls.append(req.url.path)
        if req.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nDisallow: /private')
        return httpx.Response(302,headers={'location':'/private/1'})
    with pytest.raises(SourceBlocked):await make_fetch(settings,handler).get('https://catalog.example/start')
    assert '/private/1' not in calls

async def test_redirect_to_private_host_rejected(settings):
    def handler(req):return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(302,headers={'location':'http://127.0.0.1/'})
    with pytest.raises(SourceBlocked):await make_fetch(settings,handler).get('https://catalog.example/start')

async def test_response_size_limit(settings):
    settings.max_html_bytes=100
    def handler(req):return httpx.Response(404) if req.url.path=='/robots.txt' else httpx.Response(200,text='x'*101,headers={'content-type':'text/html'})
    with pytest.raises(SourceBlocked):await make_fetch(settings,handler).get('https://catalog.example/p/1')

async def test_request_budget(settings):
    f=make_fetch(settings,lambda req:httpx.Response(200));f.request_count=200
    with pytest.raises(SourceBlocked):await f.raw('https://catalog.example/p/1')

async def test_browser_opt_in(settings):
    with pytest.raises(SourceBlocked):await SafeFetcher('catalog.example',settings).rendered('https://catalog.example/p/1')
