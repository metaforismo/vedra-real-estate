from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from .db import Database, now, uid


PBKDF2_ITERATIONS = 600_000


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    return f'pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, digest = encoded.split('$')
        if algorithm != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def bootstrap_user(db: Database, settings) -> None:
    if db.one('SELECT id FROM users LIMIT 1'):
        return
    password = settings.admin_password
    if password and (len(password)<12 or password.lower().startswith(('change','replace'))):
        raise RuntimeError('ADMIN_PASSWORD deve contenere almeno 12 caratteri e non essere un placeholder.')
    if not password:
        password = secrets.token_urlsafe(18)
        target = settings.data_dir / 'bootstrap-password.txt'
        target.write_text(f'{settings.admin_email}\n{password}\n')
        target.chmod(0o600)
        print(f'Vedra: credenziali iniziali in {target}. Rimuovi il file dopo averle conservate.')
    db.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',
               (uid(), settings.admin_email.lower(), password_hash(password), 'Workspace Admin', 'admin', now()))


class LoginLimiter:
    def __init__(self):
        self.attempts: dict[str, deque] = defaultdict(deque)

    def check(self, key: str):
        instant = time.monotonic()
        q = self.attempts[key]
        while q and q[0] < instant-600:
            q.popleft()
        if len(q)>=10:
            raise HTTPException(429, 'Troppi tentativi. Riprova tra dieci minuti.', headers={'Retry-After':'600'})
        q.append(instant)
        if len(self.attempts)>10000:
            self.attempts = defaultdict(deque, {k:v for k,v in self.attempts.items() if v and v[-1]>instant-600})


def create_session(db: Database, user: dict, hours: int) -> tuple[str,str]:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    expires = (datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat(timespec='seconds')
    db.execute('DELETE FROM sessions WHERE expires_at < ?', (now(),))
    db.execute('INSERT INTO sessions VALUES(?,?,?,?)', (token_hash(token),user['id'],csrf,expires))
    return token,csrf


def current_user(request: Request) -> dict:
    token = request.cookies.get('vedra_session','')
    row = request.app.state.db.one('''SELECT u.id,u.email,u.name,u.role,s.csrf FROM sessions s
             JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?''', (token_hash(token),now()))
    if not row:
        raise HTTPException(401, 'Accedi per continuare.')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not hmac.compare_digest(request.headers.get('x-csrf-token',''), row['csrf']):
            raise HTTPException(403,'Token CSRF assente o non valido. Ricarica la pagina.')
    return row


def require_editor(request: Request) -> dict:
    user=current_user(request)
    if user['role'] not in ('admin','analyst'):
        raise HTTPException(403, 'L’account può soltanto consultare i dati.')
    return user


def require_admin(request: Request) -> dict:
    user=current_user(request)
    if user['role']!='admin':
        raise HTTPException(403, 'Operazione riservata agli amministratori.')
    return user


def require_bridge(request: Request) -> None:
    received=request.headers.get('authorization','').removeprefix('Bearer ')
    if received.startswith('run:'):
        import re
        ident=request.path_params.get('ident','')
        pattern=r'/bridge/runs/[A-Za-z0-9_-]+(?:/analysis/[A-Za-z0-9_-]+|/finish)?'
        if not re.fullmatch(pattern,request.url.path):
            raise HTTPException(403,'Capability non abilitata a questa operazione.')
        row=request.app.state.db.one('SELECT * FROM run_capabilities WHERE run_id=?',(ident,))
        run=request.app.state.db.one('SELECT runtime,status FROM runs WHERE id=?',(ident,))
        if (not row or row['expires_at']<=now() or not run or run['runtime']!='hermes'
            or run['status']!='running' or not hmac.compare_digest(row['token_hash'],token_hash(received[4:]))):
            raise HTTPException(401,'Capability scaduta o non valida per questa run.')
        return
    expected=request.app.state.settings.bridge_token
    received=request.headers.get('authorization','').removeprefix('Bearer ')
    if not expected or not hmac.compare_digest(expected,received):
        raise HTTPException(401, 'Bridge non autorizzato.')


def csv_safe(value) -> str:
    if isinstance(value,(int,float)):
        return str(value)
    value='' if value is None else str(value)
    # Prevent formula injection in Excel/LibreOffice, including leading whitespace.
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value


class BodyLimitMiddleware:
    """Bound chunked request bodies too, before JSON parsing or authentication work."""
    def __init__(self, app, limit=5_000_000):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] in ('GET', 'HEAD', 'OPTIONS'):
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            size += len(chunk)
            if size > self.limit:
                from starlette.responses import JSONResponse
                return await JSONResponse({'detail': 'Richiesta troppo grande (massimo 5 MB).'}, status_code=413)(scope, receive, send)
            chunks.append(chunk)
            if not message.get('more_body', False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)
