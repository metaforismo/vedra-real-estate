from __future__ import annotations

import asyncio
import ipaddress
import socket
import urllib.robotparser
from urllib.parse import urlsplit, urlunsplit, urljoin

import httpx

BOT = 'VedraPreviewBot/0.1'


class SourceBlocked(RuntimeError):
    pass


class SafeFetcher:
    """Exact host allowlist, DNS-to-public-IP pinning, manual redirects, size limits.

    DNS is resolved once per request and the vetted IP is used for TCP. The original
    host is supplied as both Host and TLS SNI: validation is not a check-then-resolve.
    No cookies, authorization, environment proxies or user-controlled headers.
    """
    def __init__(self, domain: str, settings, *, transport=None):
        self.domain=domain.lower()
        self.settings=settings
        self.transport=transport
        self.robots=None
        self.last_request=0.0
        self.delay=settings.request_delay
        self.request_lock=asyncio.Lock()
        self.request_count=0

    def validate_url(self, url: str):
        try:
            parts=urlsplit(url)
            port=parts.port
        except ValueError as exc:
            raise SourceBlocked('URL non valido.') from exc
        if parts.scheme not in ('http','https') or parts.username or parts.password:
            raise SourceBlocked('Sono ammesse soltanto URL HTTP(S) senza credenziali.')
        if parts.hostname!=self.domain or self.domain not in self.settings.live_domains:
            raise SourceBlocked('Dominio non presente nella allowlist del server.')
        if port not in (None,80,443):
            raise SourceBlocked('Porta non consentita.')
        if '\\' in url or any(ord(c)<32 for c in url):
            raise SourceBlocked('URL non valido.')
        return parts

    async def resolve(self, host: str, port: int) -> str:
        infos=await asyncio.to_thread(socket.getaddrinfo,host,port,type=socket.SOCK_STREAM)
        addresses=list(dict.fromkeys(item[4][0] for item in infos))
        if not addresses:
            raise SourceBlocked('Il dominio non risolve.')
        for address in addresses:
            ip=ipaddress.ip_address(address)
            if not ip.is_global or (ip.version==6 and ip.ipv4_mapped and not ip.ipv4_mapped.is_global):
                raise SourceBlocked('Indirizzo privato, riservato o locale non consentito.')
        return addresses[0]

    async def raw(self, url: str, *, limit: int | None=None, enforce_robots: bool=False) -> tuple[int,dict,bytes,str]:
        async with self.request_lock:
            return await self._raw(url,limit=limit,enforce_robots=enforce_robots)

    async def _raw(self, url: str, *, limit: int | None=None, enforce_robots: bool=False) -> tuple[int,dict,bytes,str]:
        for _ in range(5):
            self.request_count+=1
            if self.request_count>200:
                raise SourceBlocked('Budget massimo di 200 richieste per fonte e run raggiunto.')
            if enforce_robots and self.robots and not self.robots.can_fetch(BOT,url):
                raise SourceBlocked('Il redirect porta a un percorso escluso da robots.txt.')
            p=self.validate_url(url)
            port=p.port or (443 if p.scheme=='https' else 80)
            address=await self.resolve(p.hostname,port)
            authority=f'[{address}]' if ':' in address else address
            pinned=urlunsplit((p.scheme, f'{authority}:{port}',p.path or '/',p.query,''))
            host=p.hostname + (f':{p.port}' if p.port else '')
            elapsed=asyncio.get_running_loop().time()-self.last_request
            await asyncio.sleep(max(0,self.delay-elapsed))
            async with httpx.AsyncClient(timeout=20,follow_redirects=False,trust_env=False,transport=self.transport) as client:
                async with client.stream('GET',pinned,headers={'Host':host,'User-Agent':BOT,'Accept':'text/html,application/xhtml+xml,text/plain,application/json;q=0.8'},extensions={'sni_hostname':p.hostname}) as response:
                    headers=dict(response.headers)
                    if response.status_code in (301,302,303,307,308):
                        url=urljoin(url,headers.get('location',''))
                        self.validate_url(url)
                        self.last_request=asyncio.get_running_loop().time()
                        continue
                    chunks=[]
                    length=0
                    async for chunk in response.aiter_bytes():
                        length+=len(chunk)
                        if length>(limit or self.settings.max_html_bytes):
                            raise SourceBlocked('Risposta oltre il limite di dimensione.')
                        chunks.append(chunk)
                    self.last_request=asyncio.get_running_loop().time()
                    return response.status_code,headers,b''.join(chunks),url
        raise SourceBlocked('Troppi redirect.')

    async def check_robots(self, url: str) -> None:
        self.validate_url(url)
        if self.robots is None:
            p=urlsplit(url)
            robots_url=urlunsplit((p.scheme,p.netloc,'/robots.txt','',''))
            status,_,body,_=await self.raw(robots_url,limit=500_000)
            if status==404:
                body=b'User-agent: *\nAllow: /'
            elif status!=200:
                raise SourceBlocked(f'robots.txt non verificabile (HTTP {status}).')
            robot=urllib.robotparser.RobotFileParser()
            robot.parse(body.decode('utf-8',errors='replace').splitlines())
            self.robots=robot
            self.delay=max(self.delay,robot.crawl_delay(BOT) or robot.crawl_delay('*') or 0)
        if not self.robots.can_fetch(BOT,url):
            raise SourceBlocked('Accesso escluso da robots.txt. Nessun tentativo di aggiramento.')

    async def get(self, url: str) -> tuple[str,str]:
        await self.check_robots(url)
        status,headers,body,final=await self.raw(url,enforce_robots=True)
        if status in (401,403,429):
            raise SourceBlocked(f'Fonte bloccata o limitata (HTTP {status}).')
        if status!=200:
            raise SourceBlocked(f'La fonte risponde HTTP {status}.')
        content_type=headers.get('content-type','').lower()
        if not any(t in content_type for t in ('html','text/plain','application/json')):
            raise SourceBlocked('Formato non supportato dal connettore HTML.')
        text=body.decode('utf-8',errors='replace')
        lower=text.lower()
        indicators=('cf-chl-','verify you are human','verifica di essere un essere umano','captcha challenge','access denied','unusual traffic')
        if any(x in lower for x in indicators):
            raise SourceBlocked('Challenge anti-bot rilevata. Il connettore si arresta.')
        return text,final

    async def rendered(self, url: str) -> tuple[str,str]:
        if not self.settings.browser_enabled:
            raise SourceBlocked('Rendering browser disabilitato. Abilita BROWSER_ENABLED e installa Chromium.')
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise SourceBlocked('Installa l’extra browser e Chromium per Playwright.') from exc
        await self.check_robots(url)
        # Every browser HTTP request is fulfilled through the same pinned fetcher.
        # No service workers, websocket, cross-origin requests, media or downloads.
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True)
            context=await browser.new_context(service_workers='block',accept_downloads=False)
            await context.route_web_socket('**/*',lambda ws: ws.close())
            errors=[]
            async def route_request(route):
                request=route.request
                if request.method!='GET' or request.resource_type in ('image','media','font','websocket'):
                    return await route.abort()
                try:
                    await self.check_robots(request.url)
                    status,headers,body,_=await self.raw(request.url,enforce_robots=True)
                    if status in (401,403,429):
                        raise SourceBlocked(f'Browser bloccato (HTTP {status}).')
                    safe_headers={'content-type':headers.get('content-type','text/plain')}
                    if request.resource_type=='document':
                        safe_headers['Content-Security-Policy']="default-src 'self' 'unsafe-inline'; connect-src 'self'; worker-src 'none'; frame-src 'none'; object-src 'none'; img-src 'none'; media-src 'none'"
                    await route.fulfill(status=status,headers=safe_headers,body=body)
                except Exception as exc:
                    if request.resource_type=='document': errors.append(str(exc))
                    await route.abort()
            await context.route('**/*',route_request)
            page=await context.new_page()
            try:
                await page.goto(url,wait_until='domcontentloaded',timeout=45000)
                await page.wait_for_timeout(1500)
                text=await page.content()
                if errors:
                    raise SourceBlocked(errors[0])
                if len(text.encode())>self.settings.max_html_bytes:
                    raise SourceBlocked('Pagina renderizzata troppo grande.')
                if any(x in text.lower() for x in ('cf-chl-','verify you are human','captcha challenge')):
                    raise SourceBlocked('Challenge anti-bot rilevata.')
                return text,page.url
            finally:
                await context.close()
                await browser.close()
