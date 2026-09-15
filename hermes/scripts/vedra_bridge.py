#!/usr/bin/env python3
"""Narrow, dependency-free Vedra bridge for an isolated Hermes profile.

Credentials are read only from environment variables and are never printed.
No arbitrary shell commands, source URLs, SQL or admin writes are exposed here.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Bridge redirect refused; correct VEDRA_BASE_URL instead.')


def identifier(value: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
        raise argparse.ArgumentTypeError('Invalid application identifier.')
    return value


def call(method: str, path: str, payload: dict | None = None) -> dict:
    base = os.environ.get('VEDRA_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    token = os.environ.get('VEDRA_BRIDGE_TOKEN', '')
    parts = urlsplit(base)
    if parts.scheme not in ('http', 'https') or parts.username or parts.password or parts.query or parts.fragment:
        raise RuntimeError('VEDRA_BASE_URL must be an HTTP(S) origin without embedded credentials.')
    if not token:
        raise RuntimeError('VEDRA_BRIDGE_TOKEN is not configured in this Hermes profile.')
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode() if payload is not None else None
    request = Request(base + path, data=body, method=method, headers={
        'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
        'Accept': 'application/json', 'User-Agent': 'VedraHermesBridge/0.1',
    })
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=int(os.environ.get('VEDRA_REQUEST_TIMEOUT', '180'))) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise RuntimeError('Bridge response exceeds 2 MB.')
            return json.loads(raw)
    except HTTPError as error:
        # Structured application errors can explain validation failures without echoing headers.
        raw = error.read(4096).decode(errors='replace')
        try:
            detail = json.loads(raw).get('detail', f'HTTP {error.code}')
        except (ValueError, AttributeError):
            detail = f'HTTP {error.code}'
        raise RuntimeError(f'Vedra rejected the request ({error.code}): {detail}') from None
    except URLError as error:
        raise RuntimeError('Vedra bridge is unreachable. Check the service and VEDRA_BASE_URL.') from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('collect', 'status', 'finish'):
        commands.add_parser(name).add_argument('run_id', type=identifier)
    submit = commands.add_parser('submit')
    submit.add_argument('run_id', type=identifier)
    submit.add_argument('property_id', type=identifier)
    submit.add_argument('json_file', help='UTF-8 JSON file, or - to read stdin')
    commands.add_parser('enqueue').add_argument('agent_id', type=identifier)
    args = parser.parse_args(argv)
    try:
        if args.command == 'enqueue':
            result = call('POST', f'/bridge/agents/{args.agent_id}/enqueue')
        elif args.command == 'status':
            result = call('GET', f'/bridge/runs/{args.run_id}')
        elif args.command == 'submit':
            if args.json_file == '-':
                text = sys.stdin.read(64_001)
            else:
                path = Path(args.json_file)
                if path.stat().st_size > 64_000:
                    raise RuntimeError('Classification JSON exceeds 64 KB.')
                text = path.read_text(encoding='utf-8')
            if len(text) > 64_000:
                raise RuntimeError('Classification JSON exceeds 64 KB.')
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError('Classification must be a JSON object.')
            result = call('POST', f'/bridge/runs/{args.run_id}/analysis/{args.property_id}', payload)
        else:
            result = call('POST', f'/bridge/runs/{args.run_id}/{args.command}')
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (RuntimeError, ValueError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
