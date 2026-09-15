#!/usr/bin/env python3
"""Exercise the real app in Chromium against an isolated, temporary backend.

Normal mode uses localhost directly. --relay is ONLY for locked-down QA machines
whose enterprise browser policy forbids top-level URL navigation. It relays actual
HTTP responses, not fixtures or mock API responses; see TEST_REPORT.md.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', help='Optional path to a system Chromium')
    parser.add_argument('--relay', action='store_true', help='Restricted-environment QA transport only')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/ui')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    password = secrets.token_urlsafe(24)
    checks: list[str] = []
    errors: list[str] = []
    report = {'checks': checks, 'page_errors': errors, 'transport': 'real-http-relay' if args.relay else 'direct-http'}
    with tempfile.TemporaryDirectory(prefix='vedra-ui-') as temp:
        env = dict(os.environ, DATA_DIR=temp, ADMIN_EMAIL='ui-test@vedra.local', ADMIN_PASSWORD=password,
                   PUBLIC_ORIGIN=origin, ALLOWED_HOSTS='127.0.0.1,localhost', COOKIE_SECURE='false',
                   SCHEDULER_ENABLED='false', SEED_DEMO='true', HERMES_API_KEY='', VEDRA_BRIDGE_TOKEN='',
                   LIVE_ALLOWED_DOMAINS='', BROWSER_ENABLED='false')
        with (output / 'server.log').open('w') as log:
            process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/run.py'), '--port', str(port)],
                                       cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 30
                with httpx.Client(trust_env=False) as health:
                    while True:
                        try:
                            if health.get(origin + '/api/health', timeout=1).status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        if process.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError('Backend did not start. See server.log.')
                        time.sleep(.2)
                with sync_playwright() as pw:
                    launch = {'headless': True}
                    if args.chromium:
                        launch['executable_path'] = args.chromium
                    browser = pw.chromium.launch(**launch)
                    context = browser.new_context(viewport={'width': 1440, 'height': 1080}, device_scale_factor=1)
                    page = context.new_page()
                    page.set_default_timeout(15_000)
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    transport = httpx.Client(trust_env=False, timeout=30, follow_redirects=False)
                    if args.relay:
                        def relay(route):
                            req = route.request
                            headers = {k: v for k, v in req.headers.items() if k.lower() not in
                                       ('host', 'origin', 'cookie', 'content-length', 'accept-encoding')}
                            response = transport.request(req.method, req.url, headers=headers, content=req.post_data_buffer)
                            headers = {k: v for k, v in response.headers.items() if k.lower() not in
                                       ('content-length', 'content-encoding', 'transfer-encoding', 'content-security-policy')}
                            headers['access-control-allow-origin'] = 'null'
                            headers['access-control-allow-credentials'] = 'true'
                            route.fulfill(status=response.status_code, headers=headers, body=response.content)
                        page.route(origin + '/**', relay)
                        html = (ROOT / 'frontend/index.html').read_text().replace('<head>', f'<head><base href="{origin}/">')
                        page.set_content(html)
                    else:
                        page.goto(origin, wait_until='networkidle')

                    def screenshot(name: str) -> None:
                        page.screenshot(path=str(output / f'{name}.png'), full_page=True, animations='disabled')
                        if page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'):
                            details=page.evaluate('Array.from(document.querySelectorAll("body *")).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).filter(e=>e.right>innerWidth+1).slice(0,20)')
                            raise AssertionError(f'Horizontal document overflow: {name}: {details}')

                    def nav(name: str) -> None:
                        routes = {'Panoramica':'overview','Opportunità':'properties','Agenti':'agents','Fonti e importazioni':'sources','Qualità dei dati':'quality','Attività':'activity','Impostazioni':'settings'}
                        page.locator(f'a.nav-link[href="#{routes[name]}"]').click()

                    def close() -> None:
                        page.get_by_role('button', name='Chiudi finestra', exact=True).click()
                        expect(page.get_by_role('dialog')).to_have_count(0)

                    expect(page.get_by_role('heading', name='Bentornato.')).to_be_visible()
                    screenshot('login')
                    page.get_by_label('Email', exact=True).fill('ui-test@vedra.local')
                    page.get_by_label('Password', exact=True).fill(password)
                    page.get_by_role('button', name='Accedi al workspace').click()
                    expect(page.get_by_role('heading', name='Le opportunità prendono forma.')).to_be_visible()
                    screenshot('dashboard')
                    checks.append('Login, real session and overview')

                    page.locator('.property-link').first.click()
                    expect(page.locator('.property-drawer')).to_be_visible()
                    screenshot('property-detail')
                    page.get_by_label('Aggiungi una nota').fill('Verificare superficie commerciale e documentazione della proprietà.')
                    page.get_by_role('button', name='Aggiungi nota', exact=True).click()
                    expect(page.locator('.notes-list')).to_contain_text('Verificare superficie commerciale')
                    close()
                    checks.append('Property detail and persisted team note')

                    nav('Opportunità')
                    page.locator('[data-select-property]').nth(0).check()
                    page.locator('[data-select-property]').nth(1).check()
                    page.get_by_role('button', name='Confronta', exact=True).click()
                    expect(page.get_by_role('heading', name='Metti a confronto.')).to_be_visible()
                    expect(page.locator('.compare-table thead th')).to_have_count(3)
                    screenshot('comparison')
                    close()
                    page.get_by_role('button', name='Annulla selezione').click()
                    page.get_by_label('Comune', exact=True).select_option('Monza')
                    expect(page.locator('#results-body')).not_to_contain_text('Como ·')
                    expect(page.locator('#results-body')).to_contain_text('Monza')
                    page.get_by_role('button', name='Azzera', exact=True).click()
                    page.get_by_role('button', name='Vista schede').click()
                    expect(page.locator('.property-card')).to_have_count(36)
                    screenshot('opportunities')
                    checks.append('Selection, comparison, municipal filter and card view')

                    nav('Agenti')
                    screenshot('agents')
                    page.get_by_role('button', name='Crea agente', exact=True).click()
                    page.get_by_label('Nome della ricerca').fill('Milano · Verifica UI')
                    page.locator('#agent-form input[name="source_ids"]').first.check()
                    page.locator('#agent-form input[name="max_listings"]').fill('8')
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    card = page.locator('.agent-card').filter(has=page.get_by_role('heading', name='Milano · Verifica UI'))
                    expect(card).to_be_visible()
                    card.get_by_role('button', name='Esegui ora', exact=True).click()
                    expect(page.locator('#run-content .run-meta')).to_contain_text('Completata', timeout=30_000)
                    expect(page.locator('#run-content')).to_contain_text('Regole locali')
                    screenshot('run')
                    close()
                    card.get_by_role('button', name='Pausa', exact=True).click()
                    expect(card.get_by_role('button', name='Riprendi')).to_be_visible()
                    card.get_by_role('button', name='Riprendi').click()
                    expect(card.get_by_role('button', name='Pausa', exact=True)).to_be_visible()
                    checks.append('Create, execute, inspect logs, pause and resume a real queued job')

                    nav('Fonti e importazioni')
                    page.get_by_role('button', name='Importa dati', exact=True).click()
                    page.get_by_label('File da importare').set_input_files(str(ROOT / 'fixtures/imports/properties-demo.csv'))
                    page.locator('#import-form input[name="permission_confirmed"]').check()
                    page.locator('#import-form button[type="submit"]').click()
                    expect(page.get_by_role('heading', name='Importazione completata.')).to_be_visible()
                    close()
                    screenshot('sources')
                    checks.append('CSV file import through the actual browser form')

                    nav('Qualità dei dati')
                    expect(page.get_by_role('heading', name='Quanto sappiamo, davvero?')).to_be_visible()
                    screenshot('data-quality')
                    nav('Impostazioni')
                    page.locator('[data-action="runtime-test"]').click()
                    expect(page.locator('#runtime-result')).to_contain_text('Hermes non configurato')
                    checks.append('Data quality and honest missing Hermes status')

                    nav('Panoramica')
                    page.get_by_role('button', name='Cambia tema').click()
                    expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
                    screenshot('dashboard-dark')
                    page.get_by_role('button', name='Cambia tema').click()
                    page.set_viewport_size({'width': 393, 'height': 852})
                    page.wait_for_timeout(300)  # Let the responsive sidebar transition finish.
                    screenshot('mobile-dashboard')
                    page.get_by_role('button', name='Apri navigazione').click()
                    nav('Agenti')
                    expect(page.get_by_role('heading', name='Ricerche che non ripartono da zero.')).to_be_visible()
                    screenshot('mobile-agents')
                    checks.append('Dark theme and 393px mobile navigation without document overflow')
                    if errors:
                        raise AssertionError('JavaScript errors: ' + repr(errors))
                    transport.close()
                    browser.close()
                report['status'] = 'passed'
            except Exception as exc:
                report['status'] = 'failed'
                report['failure'] = str(exc)
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
                (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
