from __future__ import annotations

import asyncio
import math
import ipaddress
import socket
import urllib.robotparser
from contextlib import AsyncExitStack
from urllib.parse import urlsplit, urlunsplit, urljoin

import httpx

CHALLENGE_INDICATORS = ('cf-chl-', 'verify you are human', 'verifica di essere un essere umano',
    'captcha challenge', 'access denied', 'unusual traffic',
    'please enable js and disable any ad blocker', 'access is temporarily restricted',
    'we detected unusual activity from your device or network')

BOT = 'VedraPreviewBot/0.1'  # Stable identity: preserve existing source permissions/robots rules.


class SourceBlocked(RuntimeError):
    def __init__(self,message,retry_after=0):
        super().__init__(message)
        self.retry_after=retry_after


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
            raise SourceBlocked(f'Fonte bloccata o limitata (HTTP {status}).', retry_after=retry_seconds(headers.get('retry-after','')))
        if status!=200:
            raise SourceBlocked(f'La fonte risponde HTTP {status}.')
        content_type=headers.get('content-type','').lower()
        if not any(t in content_type for t in ('html','text/plain','application/json','application/xml','text/xml')):
            raise SourceBlocked('Formato non supportato dal connettore HTML.')
        text=body.decode('utf-8',errors='replace')
        lower=text.lower()
        if any(x in lower for x in CHALLENGE_INDICATORS):
            raise SourceBlocked('Challenge anti-bot rilevata. Il connettore si arresta.')
        return text,final

    async def rendered(self, url: str) -> tuple[str,str]:
        return await self._browser(url,native=False)

    async def browse(self, url: str) -> tuple[str,str]:
        return await self._browser(url,native=True)

    async def _browser(self, url: str, *, native: bool) -> tuple[str,str]:
        if not self.settings.browser_enabled:
            raise SourceBlocked('Rendering browser disabilitato. Abilita BROWSER_ENABLED e installa Chromium.')
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise SourceBlocked('Installa l’extra browser e Chromium per Playwright.') from exc
        await self.check_robots(url)
        launch_args=[]
        if native:
            p=self.validate_url(url)
            address=await self.resolve(p.hostname,p.port or (443 if p.scheme=='https' else 80))
            address=f'[{address}]' if ':' in address else address
            # Chromium connects to the vetted IP while preserving URL origin/TLS.
            # The catch-all denies alternate DNS, including rebinding on redirects.
            launch_args=[f'--host-resolver-rules=MAP {self.domain} {address}, MAP * ~NOTFOUND',
                         '--no-proxy-server','--force-webrtc-ip-handling-policy=disable_non_proxied_udp']
        # Native navigation pins Chromium DNS; legacy rendering pins each HTTP
        # delivery. Both enforce the same source boundary and readonly methods.
        async with async_playwright() as pw, AsyncExitStack() as cleanup:
            browser=await pw.chromium.launch(headless=True, chromium_sandbox=True,args=launch_args,
                **({'executable_path':self.settings.browser_executable} if self.settings.browser_executable else {}))
            cleanup.push_async_callback(browser.close)
            context=await browser.new_context(service_workers='block',accept_downloads=False)
            cleanup.push_async_callback(context.close)
            if native:
                # These transports bypass Playwright's HTTP routing. They are not
                # needed for catalog pages and must not reach local network peers.
                await context.add_init_script("""for (const name of ['RTCPeerConnection','webkitRTCPeerConnection','WebTransport','Worker','SharedWorker']) {
                    Object.defineProperty(globalThis, name, {value: undefined, configurable: false, writable: false});
                }""")
            await context.route_web_socket('**/*',lambda ws: ws.close())
            errors=[]
            page=await context.new_page()
            async def route_request(route):
                request=route.request
                if request.method!='GET' or request.resource_type in ('image','media','font','websocket'):
                    return await route.abort()
                try:
                    if native and request.frame.page!=page:
                        return await route.abort()
                    await self.check_robots(request.url)
                    if native:
                        self.request_count+=1
                        if self.request_count>200:raise SourceBlocked('Budget browser raggiunto.')
                        # Keep source pacing also for real Chromium requests.
                        async with self.request_lock:
                            elapsed=asyncio.get_running_loop().time()-self.last_request
                            await asyncio.sleep(max(0,self.delay-elapsed))
                            self.last_request=asyncio.get_running_loop().time()
                        return await route.continue_()
                    status,headers,body,_=await self.raw(request.url,enforce_robots=True)
                    if status in (401,403,429):
                        raise SourceBlocked(f'Browser bloccato (HTTP {status}).')
                    if request.resource_type=='document' and status!=200:
                        raise SourceBlocked(f'La fonte risponde HTTP {status}.')
                    safe_headers={'content-type':headers.get('content-type','text/plain')}
                    if request.resource_type=='document':
                        safe_headers['Content-Security-Policy']="default-src 'self' 'unsafe-inline'; connect-src 'self'; worker-src 'none'; frame-src 'none'; object-src 'none'; img-src 'none'; media-src 'none'"
                    await route.fulfill(status=status,headers=safe_headers,body=body)
                except Exception as exc:
                    if request.resource_type=='document': errors.append(str(exc))
                    await route.abort()
            await context.route('**/*',route_request)
            if native:
                # Playwright routing handles only the first URL of a redirect
                # chain. Pause Chromium's response before it follows Location.
                session=await context.new_cdp_session(page)
                redirects=0
                async def inspect_response(event):
                    nonlocal redirects
                    try:
                        if event.get('responseStatusCode') in (301,302,303,307,308):
                            redirects+=1
                            if redirects>10:raise SourceBlocked('Troppi redirect nel browser.')
                            location=next((h['value'] for h in event.get('responseHeaders',[]) if h['name'].lower()=='location'),'')
                            if not location:raise SourceBlocked('Redirect senza destinazione.')
                            await self.check_robots(urljoin(event['request']['url'],location))
                        await session.send('Fetch.continueResponse',{'requestId':event['requestId']})
                    except Exception as exc:
                        errors.append(str(exc) if isinstance(exc,SourceBlocked) else 'Risposta browser non verificabile.')
                        try:await session.send('Fetch.failRequest',{'requestId':event['requestId'],'errorReason':'BlockedByClient'})
                        except Exception:pass  # Context cancellation can close the target first.
                session.on('Fetch.requestPaused',inspect_response)
                await session.send('Fetch.enable',{'patterns':[{'urlPattern':'*','requestStage':'Response'}]})
            try:
                response=await page.goto(url,wait_until='domcontentloaded',timeout=45000)
            except Exception as exc:
                if errors:raise SourceBlocked(errors[0]) from exc
                raise SourceBlocked('Navigazione browser non riuscita; verifica accesso e risorse della fonte.') from exc
            if native and response and response.status!=200:
                raise SourceBlocked(f'La fonte risponde HTTP {response.status}.')
            await page.wait_for_timeout(1500)
            text=await page.content()
            self.validate_url(page.url)
            if errors:
                raise SourceBlocked(errors[0])
            if len(text.encode())>self.settings.max_html_bytes:
                raise SourceBlocked('Pagina renderizzata troppo grande.')
            if any(x in text.lower() for x in CHALLENGE_INDICATORS):
                raise SourceBlocked('Challenge anti-bot rilevata.')
            return text,page.url



def retry_seconds(value):
    from datetime import datetime, timezone
    from email.utils import parsedate_to_datetime
    try:
        delay=float(value)
        if not math.isfinite(delay): return 0
    except (ValueError,TypeError):
        try: delay=(parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds()
        except (ValueError,TypeError,OverflowError): return 0
    return min(86400,max(0,int(delay)))
