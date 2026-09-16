#!/usr/bin/env python3
"""Produce Vercel Build Output v3: static UI and same-origin reverse proxy only."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path, origin: str) -> Path:
    origin = origin.rstrip('/')
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or parsed.port not in (None, 443)
            or any(c in origin for c in '\\$\r\n')):
        raise ValueError('VEDRA_API_ORIGIN deve essere l’origine HTTPS della tua API, senza percorso o credenziali.')
    output = root / '.vercel/output'
    if output.exists():
        shutil.rmtree(output)
    static = output / 'static'
    static.mkdir(parents=True)
    shutil.copy2(root / 'frontend/index.html', static / 'index.html')
    shutil.copytree(root / 'frontend/src', static / 'assets')
    shutil.copytree(root / 'frontend/public', static / 'public')
    csp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data:; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    config = {'version': 3, 'routes': [
        {'src':'/(.*)', 'headers':{'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY',
             'Referrer-Policy':'no-referrer', 'Content-Security-Policy':csp,
             'Permissions-Policy':'camera=(), microphone=(), geolocation=()'}, 'continue':True},
        {'src':'/bridge(?:/.*)?', 'status':404},
        {'src':'/api/(.*)', 'dest':origin+'/api/$1', 'headers':{'Cache-Control':'no-store'}},
        {'src':'/(.*)', 'headers':{'Cache-Control':'no-cache'}, 'continue':True},
        {'handle':'filesystem'},
        {'src':'/(.*)', 'dest':'/index.html'},
    ]}
    (output / 'config.json').write_text(json.dumps(config, indent=2)+'\n')
    return output


if __name__ == '__main__':
    try:
        destination = build(ROOT, os.environ.get('VEDRA_API_ORIGIN', ''))
        print(f'Output statico e proxy creati: {destination}')
    except ValueError as exc:
        raise SystemExit(str(exc))
