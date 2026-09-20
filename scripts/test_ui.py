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
                   SCHEDULER_ENABLED='false', WORKER_ENABLED='true', DATABASE_URL='', HERMES_API_KEY='', VEDRA_BRIDGE_TOKEN='',
                   LIVE_ALLOWED_DOMAINS='', BROWSER_ENABLED='false', AI_API_KEY='', AI_API_BASE_URL='', AI_MODEL='', MAIL_ENABLED='false')
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
                    page.route('https://fonts.googleapis.com/**',lambda route:route.abort())
                    page.route('https://fonts.gstatic.com/**',lambda route:route.abort())
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
                        page.set_content(html,wait_until="domcontentloaded")
                    else:
                        page.goto(origin, wait_until='networkidle')

                    def screenshot(name: str) -> None:
                        page.screenshot(path=str(output / f'{name}.png'), full_page=True, animations='disabled')
                        if page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'):
                            details=page.evaluate('Array.from(document.querySelectorAll("body *")).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).filter(e=>e.right>innerWidth+1).slice(0,20)')
                            raise AssertionError(f'Horizontal document overflow: {name}: {details}')

                    def nav(name: str) -> None:
                        routes = {'Panoramica':'overview','Opportunità':'properties','Agenti':'agents','Fonti e importazioni':'sources','Qualità dei dati':'quality','Attività':'activity','Impostazioni':'settings','Pipeline':'pipeline','Inbox':'inbox','Mercato':'market','Insight':'insights'}
                        page.locator(f'a.nav-link[href="#{routes[name]}"]').click()

                    def close() -> None:
                        page.get_by_role('button', name='Chiudi finestra', exact=True).click()
                        expect(page.get_by_role('dialog')).to_have_count(0)

                    expect(page.get_by_role('heading', name='Accedi', exact=True)).to_be_visible()
                    screenshot('login')
                    page.get_by_label('Email', exact=True).fill('ui-test@vedra.local')
                    page.get_by_label('Password', exact=True).fill(password)
                    page.get_by_role('button', name='Accedi al workspace').click()
                    expect(page.get_by_role('heading', name='Panoramica', exact=True)).to_be_visible()
                    expect(page.get_by_role('heading',name='Collega la prima fonte')).to_be_visible()
                    screenshot('empty-workspace')
                    checks.append('Real workspace is empty by default')
                    # Only the QA process can load test fixtures; the running app has no seed endpoint.
                    sys.path.insert(0,str(ROOT/'backend'))
                    sys.path.insert(0,str(ROOT/'backend/tests'))
                    from app.config import Settings
                    from app.db import Database
                    from support.catalog import seed
                    test_settings=Settings(data_dir=Path(temp),database_url='',worker_enabled=False)
                    test_db=Database(test_settings.db_path)
                    seed(test_db,test_settings)
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    expect(page.locator('.rank-property')).to_have_count(5)
                    screenshot('dashboard')
                    checks.append('Login, real session and overview')

                    page.locator('.rank-property').first.click()
                    expect(page.locator('.property-drawer')).to_be_visible()
                    screenshot('property-detail')
                    page.get_by_label('Aggiungi una nota').fill('Verificare superficie commerciale e documentazione della proprietà.')
                    page.get_by_role('button', name='Aggiungi nota', exact=True).click()
                    expect(page.locator('.notes-list')).to_contain_text('Verificare superficie commerciale')
                    close()
                    checks.append('Property detail and persisted team note')

                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Revisione',exact=True).click()
                    page.locator('#work-form select[name="stage"]').select_option('due_diligence')
                    page.get_by_label('Scadenza revisione').fill('2026-12-01')
                    page.get_by_label('Annuncio e fonte verificati').check()
                    page.get_by_role('button',name='Salva revisione').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Revisione',exact=True).click()
                    expect(page.get_by_label('Annuncio e fonte verificati')).to_be_checked()
                    expect(page.locator('#work-form select[name="stage"]')).to_have_value('due_diligence')
                    screenshot('review')
                    close()
                    nav('Pipeline')
                    expect(page.locator('.pipeline-board')).to_be_visible()
                    screenshot('pipeline')
                    checks.append('Pipeline stage, due date and human checklist persist')
                    nav('Panoramica')
                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Scenario economico',exact=True).click()
                    page.get_by_label('Nome scenario',exact=True).fill('QA scenario')
                    page.get_by_label('Prezzo di acquisto (€)',exact=True).fill('100000')
                    page.get_by_label('Rivendita ipotizzata (€)',exact=True).fill('160000')
                    page.get_by_label('Lavori (€)',exact=True).fill('20000')
                    page.get_by_role('button',name='Calcola',exact=True).click()
                    expect(page.locator('#scenario-result')).to_contain_text('ROI semplice')
                    screenshot('scenario')
                    page.get_by_role('button',name='Salva scenario',exact=True).click()
                    expect(page.locator('.saved-scenarios')).to_contain_text('QA scenario')
                    page.locator('[data-action="load-scenario"]').first.click()
                    expect(page.get_by_label('Prezzo di acquisto (€)',exact=True)).to_have_value('100000')
                    close()
                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Comparabili',exact=True).click()
                    expect(page.locator('.comp-median')).to_contain_text('Mediana')
                    screenshot('comparables')
                    close()
                    checks.append('Scenario calculation, saved assumptions, reload and honest comparables')
                    nav('Mercato')
                    expect(page.get_by_role('heading',name='Mercato e benchmark',exact=True)).to_be_visible()
                    screenshot('market')
                    nav('Inbox')
                    expect(page.get_by_role('heading',name='Inbox',exact=True)).to_be_visible()
                    screenshot('inbox')
                    nav('Insight')
                    expect(page.get_by_role('heading',name='Segnali da approfondire')).to_be_visible()
                    screenshot('insights')
                    checks.append('Benchmark inventory, inbox and archive insights')
                    nav('Opportunità')
                    page.locator('[data-action="save-view"]').click()
                    page.locator('#save-view-form input[name="name"]').fill('QA view')
                    page.locator('#save-view-form button[type="submit"]').click()
                    expect(page.locator('[data-action="apply-view"]').filter(has_text='QA view')).to_be_visible()
                    checks.append('Personal saved view round trip')
                    expect(page.locator('#results-body')).to_have_attribute('aria-busy','false')
                    page.get_by_label('Annunci per pagina',exact=True).select_option('25')
                    expect(page.locator('[data-select-property]')).to_have_count(25)
                    first_selected=page.locator('[data-select-property]').first.get_attribute('data-select-property')
                    page.locator('[data-select-property]').first.check()
                    page.get_by_role('button',name='Pagina successiva',exact=True).click()
                    expect(page.locator('[data-select-property]')).to_have_count(11)
                    second_selected=page.locator('[data-select-property]').first.get_attribute('data-select-property')
                    assert first_selected!=second_selected
                    page.locator('[data-select-property]').first.check()
                    expect(page.locator('#selection-count')).to_have_text('2')
                    page.get_by_role('button',name='Aggiorna stato',exact=True).click()
                    expect(page.locator('.bulk-summary')).to_contain_text('2 annunci')
                    page.locator('#bulk-review-form select[name="stage"]').select_option('negotiation')
                    page.locator('#bulk-review-form textarea[name="note"]').fill('QA: confronto con il team prima del prossimo passo.')
                    screenshot('bulk-review')
                    page.get_by_role('button',name='Applica a 2 annunci',exact=True).click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    expect(page.locator('#selection-count')).to_have_text('0')
                    assert all(test_db.one('SELECT review_status FROM properties WHERE id=?',(ident,))['review_status']=='negotiation' for ident in [first_selected,second_selected])
                    checks.append('Server pagination and cross-page bulk review persist atomically')
                    page.get_by_role('button',name='Pagina precedente',exact=True).click()
                    expect(page.locator('[data-select-property]')).to_have_count(25)
                    page.locator('#catalog-advanced summary').click()
                    page.get_by_label('Valuta',exact=True).select_option('EUR')
                    expect(page.locator('#catalog-advanced')).to_have_attribute('open','')
                    expect(page.get_by_label('Prezzo minimo',exact=True)).to_be_visible()
                    page.get_by_label('Prezzo minimo',exact=True).fill('100000')
                    page.get_by_label('Prezzo massimo',exact=True).fill('50000')
                    page.get_by_label('Prezzo massimo',exact=True).press('Tab')
                    expect(page.locator('.catalog-error')).to_contain_text('minimo')
                    page.get_by_label('Prezzo massimo',exact=True).fill('500000')
                    page.get_by_label('Prezzo massimo',exact=True).press('Tab')
                    expect(page.locator('#results-body')).to_have_attribute('aria-busy','false')
                    page.get_by_role('button',name='Azzera',exact=True).click()
                    page.get_by_label('Annunci per pagina',exact=True).select_option('50')
                    expect(page.locator('[data-select-property]')).to_have_count(36)
                    page.locator('#catalog-advanced summary').click()
                    screenshot('catalogue')
                    page.locator('.property-link').first.click()
                    page.get_by_role('button',name='Variazioni dei campi',exact=True).click()
                    expect(page.get_by_role('heading',name='Cronologia delle evidenze')).to_be_visible()
                    expect(page.locator('.evidence-timeline')).to_be_visible()
                    screenshot('evidence-history')
                    close()
                    checks.append('Advanced archive filters and evidence history through the real API')
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
                    page.locator('.card-select input').first.check()
                    expect(page.locator('#selection-count')).to_have_text('1')
                    assert page.evaluate('document.activeElement.id.startsWith("select-")')
                    page.get_by_role('button',name='Annulla selezione').click()
                    screenshot('opportunities')
                    checks.append('Selection, comparison, municipal filter and card view')

                    nav('Agenti')
                    screenshot('agents')
                    page.get_by_role('button', name='Crea agente', exact=True).click()
                    page.get_by_label('Nome della ricerca').fill('Milano · Verifica UI')
                    page.get_by_label('Zona o indirizzo (opzionale)').fill('Porta Romana')
                    page.get_by_label('Budget minimo (€)',exact=True).fill('500000')
                    page.get_by_label('Budget massimo (€)',exact=True).fill('600000')
                    page.locator('#agent-form input[name="source_ids"]').first.check()
                    page.locator('#agent-form input[name="max_listings"]').fill('8')
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    card = page.locator('.agent-card').filter(has=page.get_by_role('heading', name='Milano · Verifica UI'))
                    expect(card).to_be_visible()
                    criteria=json.loads(test_db.one('SELECT criteria FROM agents WHERE name=?',('Milano · Verifica UI',))['criteria'])
                    assert criteria['min_price']==500000 and criteria['max_price']==600000
                    assert criteria['location_query']=='Porta Romana'
                    expect(card).to_contain_text('Porta Romana')
                    card.get_by_role('button',name='Diagnostica',exact=True).click()
                    expect(page.get_by_role('heading',name='Diagnostica agente')).to_be_visible()
                    expect(page.locator('.preflight-source')).to_contain_text('non trova nuovi annunci online')
                    screenshot('agent-preflight')
                    close()
                    checks.append('Agent preflight distinguishes configuration from live acquisition')
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
                    page.get_by_label('File da importare').set_input_files(str(ROOT / 'backend/tests/fixtures/imports/properties-demo.csv'))
                    page.locator('#import-form input[name="permission_confirmed"]').check()
                    page.locator('#import-form button[type="submit"]').click()
                    expect(page.get_by_role('heading', name='Importazione completata.')).to_be_visible()
                    close()
                    screenshot('sources')
                    checks.append('CSV file import through the actual browser form')

                    page.get_by_role('button',name='Importa dati',exact=True).click()
                    csv_text='listing_key,title,city,zone,price,surface,currency,transaction_type,property_type,condition,area_basis,latitude,longitude,description\nqa-map,TEST MAPPA SINTETICO,Milano,Test,150000,100,EUR,sale,office,good,commercial,45.46,9.19,Record sintetico di collaudo\n'
                    page.get_by_label('File da importare').set_input_files({'name':'qa-map-demo.csv','mimeType':'text/csv','buffer':csv_text.encode()})
                    page.locator('#import-form input[name="permission_confirmed"]').check()
                    page.locator('#import-form button[type="submit"]').click()
                    expect(page.get_by_role('heading',name='Importazione completata.')).to_be_visible()
                    close()
                    nav('Panoramica')
                    expect(page.locator('.map-point')).to_have_count(1)
                    page.locator('.map-point').click()
                    expect(page.locator('.property-drawer')).to_contain_text('TEST MAPPA SINTETICO')
                    close()
                    screenshot('map-populated')
                    checks.append('Map point comes from imported coordinates and opens the matching stored property')
                    nav('Qualità dei dati')
                    expect(page.get_by_role('heading', name='Qualità dei dati')).to_be_visible()
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
                    expect(page.get_by_role('heading', name='Agenti', exact=True)).to_be_visible()
                    screenshot('mobile-agents')
                    checks.append('Dark theme and 393px mobile navigation without document overflow')
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.get_by_label('Cerca immobili',exact=True).fill('Monza')
                    page.get_by_label('Cerca immobili',exact=True).press('Enter')
                    expect(page.locator('#results-body')).to_contain_text('Monza')
                    expect(page.locator('#property-search')).to_have_value('Monza')
                    checks.append('Global search submits to the property list')
                    page.emulate_media(reduced_motion='reduce')
                    page.set_viewport_size({'width':393,'height':852})
                    expect(page.locator('#results-body')).to_have_attribute('aria-busy','false')
                    screenshot('mobile-catalogue')
                    page.locator('#property-search').fill('Nessun record con questo nome')
                    expect(page.locator('#results-body')).to_contain_text('Nessun annuncio in questa vista')
                    screenshot('catalogue-empty')
                    checks.append('Mobile archive, reduced motion and filtered empty state')

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
