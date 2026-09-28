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
import re
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
        env = dict(os.environ, VEDRA_IGNORE_DOTENV='1', DATA_DIR=temp, ADMIN_EMAIL='ui-test@vedra.local', ADMIN_PASSWORD=password,
                   PUBLIC_ORIGIN=origin, ALLOWED_HOSTS='127.0.0.1,localhost', COOKIE_SECURE='false',
                   SCHEDULER_ENABLED='false', WORKER_ENABLED='true', DATABASE_URL='', HERMES_API_KEY='', VEDRA_BRIDGE_TOKEN='',
                   LIVE_ALLOWED_DOMAINS='', BROWSER_ENABLED='false', OMI_ENABLED='true', AI_API_KEY='', AI_API_BASE_URL='', AI_MODEL='', MAIL_ENABLED='false')
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
                        page.screenshot(path=str(output / f'{name}.png'), full_page=page.get_by_role('dialog').count()==0, animations='disabled')
                        if page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'):
                            details=page.evaluate('Array.from(document.querySelectorAll("body *")).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).filter(e=>e.right>innerWidth+1).slice(0,20)')
                            raise AssertionError(f'Horizontal document overflow: {name}: {details}')

                    def nav(name: str) -> None:
                        routes = {'Panoramica':'overview','Opportunità':'properties','Agenti':'agents','Fonti e importazioni':'sources','Qualità dei dati':'quality','Attività':'activity','Impostazioni':'settings','Pipeline':'pipeline','Broker':'brokers','Inbox':'inbox','Mercato':'market','Insight':'insights'}
                        link=page.locator(f'a.nav-link[href="#{routes[name]}"]')
                        if not link.is_visible():page.locator('.nav-management > summary').click()
                        link.click()
                        if routes[name]=='overview':
                            expect(page.locator('.pulse')).to_be_visible()

                    def close() -> None:
                        page.get_by_role('button', name='Chiudi finestra', exact=True).click()
                        expect(page.get_by_role('dialog')).to_have_count(0)

                    expect(page.get_by_role('heading', name='Accedi', exact=True)).to_be_visible()
                    screenshot('login')
                    page.get_by_label('Email', exact=True).fill('ui-test@vedra.local')
                    page.get_by_label('Password', exact=True).fill(password)
                    page.get_by_role('button', name='Accedi al workspace').click()
                    expect(page.get_by_role('heading', name='Oggi', exact=True)).to_be_visible()
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
                    from app.db import dump,load,now
                    contact_row=test_db.one('SELECT id,evidence FROM properties ORDER BY priority_score DESC LIMIT 1')
                    evidence=load(contact_row['evidence']);evidence['decision_facts']={'contact':{'name':'Broker di collaudo','telephone':'+39020000000','email':'qa@example.test','role':'Inserzionista dichiarato','method':'QA fixture'}}
                    test_db.execute("UPDATE properties SET availability='listed',review_status='shortlisted',evidence=? WHERE id=?",(dump(evidence),contact_row['id']))
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    expect(page.locator('.rank-property')).to_have_count(5)
                    screenshot('today')
                    expect(page.locator('.pulse-tile')).to_have_count(4)
                    screenshot('dashboard')
                    checks.append('Login, real session and overview')

                    page.locator('.rank-property').first.click()
                    expect(page.locator('.property-drawer')).to_be_visible()
                    expect(page.locator('.reference-card')).to_have_count(4)
                    with page.expect_download() as excel_download:
                        page.get_by_role('link',name='Excel',exact=True).click()
                    downloaded=excel_download.value
                    downloaded.save_as(output / 'property.xlsx')
                    from openpyxl import load_workbook
                    assert load_workbook(output / 'property.xlsx').active.title=='Selezione'
                    checks.append('Single-property Excel download and four separate market references')
                    with page.expect_download() as word_download:
                        page.get_by_role('link',name='Word',exact=True).click()
                    word_download.value.save_as(output / 'property.docx')
                    from zipfile import ZipFile
                    with ZipFile(output / 'property.docx') as document:
                        assert 'word/document.xml' in document.namelist()
                    for width in (320,393,768,1440):
                        page.set_viewport_size({'width':width,'height':1080 if width>600 else 852})
                        geometry=page.locator('.property-drawer').evaluate('''el=>{
                          const box=q=>el.querySelector(q).getBoundingClientRect().toJSON();
                          return {drawer:el.getBoundingClientRect().toJSON(),scroll:el.scrollWidth,client:el.clientWidth,
                            excel:box('.export-actions a:first-child'),word:box('.export-actions a:last-child'),
                            price:box('.deal-hero'),actions:box('.deal-actions'),contact:box('.decision-section')};
                        }''')
                        assert abs(geometry['excel']['y']-geometry['word']['y'])<=1
                        assert 0<=geometry['word']['x']-geometry['excel']['right']<=10
                        assert geometry['scroll']<=geometry['client']+1
                        assert geometry['price']['bottom']<=geometry['actions']['top']
                        assert geometry['actions']['bottom']<=geometry['contact']['top']
                        if width<=600:
                            assert abs(geometry['drawer']['width']-width)<=1
                            assert geometry['excel']['height']>=44 and geometry['word']['height']>=44
                    screenshot('property-actions-desktop')
                    page.set_viewport_size({'width':393,'height':852})
                    screenshot('property-actions-mobile')
                    page.set_viewport_size({'width':1440,'height':1080})
                    checks.append('Excel and Word stay grouped at 320/393/768/1440px; full-width mobile drawer, touch targets and both exports work')
                    page.get_by_role('heading',name='Riferimenti di mercato',exact=True).scroll_into_view_if_needed()
                    screenshot('market-references')
                    page.set_viewport_size({'width':393,'height':852})
                    page.get_by_role('heading',name='Riferimenti di mercato',exact=True).scroll_into_view_if_needed()
                    screenshot('mobile-market-references')
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.locator('.drawer-content h1').scroll_into_view_if_needed()
                    screenshot('property-detail')
                    page.get_by_label('Aggiungi una nota').fill('Verificare superficie commerciale e documentazione della proprietà.')
                    page.get_by_role('button', name='Aggiungi nota', exact=True).click()
                    expect(page.locator('.notes-list')).to_contain_text('Verificare superficie commerciale')
                    close()
                    checks.append('Property detail and persisted team note')

                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Registra contatto',exact=True).click()
                    page.get_by_label('Interlocutore',exact=True).fill('Broker QA')
                    page.get_by_role('button',name='Salva esito',exact=True).click()
                    expect(page.get_by_label('Esito',exact=True)).to_be_focused()
                    expect(page.get_by_label('Esito',exact=True)).to_have_value('')
                    page.get_by_label('Esito',exact=True).select_option('no_answer')
                    page.get_by_label('Mandato',exact=True).select_option('confirmed_by_team')
                    expect(page.locator('#contact-note-help')).to_be_visible()
                    page.get_by_role('button',name='Salva esito',exact=True).click()
                    expect(page.locator('#modal-error')).not_to_be_empty()
                    page.get_by_label('Note del contatto',exact=True).fill('Verifica del mandato effettuata: documento di test.')
                    expect(page.locator('#modal-error')).to_be_empty()
                    page.get_by_label('Esito',exact=True).select_option('documents_requested')
                    page.get_by_label('Prossimo contatto',exact=True).fill('2099-01-01')
                    page.get_by_label('Esito',exact=True).select_option('not_relevant')
                    expect(page.get_by_label('Prossimo contatto',exact=True)).to_be_disabled()
                    expect(page.locator('#contact-next-help')).to_be_visible()
                    assert page.locator('#contact-form').evaluate('(el)=>new FormData(el).get("next_contact")') is None
                    page.get_by_label('Esito',exact=True).select_option('documents_requested')
                    expect(page.get_by_label('Prossimo contatto',exact=True)).to_have_value('2099-01-01')
                    expect(page.get_by_label('Prossimo contatto',exact=True)).to_be_enabled()
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.get_by_label('Note del contatto',exact=True).scroll_into_view_if_needed()
                        close_box=page.get_by_role('button',name='Chiudi finestra',exact=True).bounding_box()
                        assert close_box and close_box['y']>=0 and close_box['height']>=44
                        screenshot(f'contact-form-{width}')
                    pending_contacts=[]
                    def hold_contact(route):pending_contacts.append(route)
                    page.route('**/api/properties/*/contacts',hold_contact)
                    contact_request=page.locator('#contact-form').get_attribute('data-request')
                    page.get_by_role('button',name='Salva esito',exact=True).click()
                    expect(page.locator('#contact-form')).to_have_attribute('aria-busy','true')
                    for name in ['Interlocutore','Esito','Mandato','Note del contatto','Prossimo contatto']:
                        expect(page.get_by_label(name,exact=True)).to_be_disabled()
                    expect(page.get_by_role('button',name='Annulla',exact=True)).to_be_disabled()
                    # Commit through the real API, then lose the HTTP acknowledgement.
                    pending_contact=pending_contacts.pop()
                    assert pending_contact.fetch().status==201
                    pending_contact.abort('failed')
                    expect(page.locator('#modal-error')).to_have_text('Connessione non disponibile.')
                    expect(page.get_by_label('Interlocutore',exact=True)).to_be_enabled()
                    expect(page.get_by_label('Prossimo contatto',exact=True)).to_have_value('2099-01-01')
                    page.unroute('**/api/properties/*/contacts',hold_contact)
                    page.get_by_role('button',name='Salva esito',exact=True).click()
                    expect(page.locator('.contact-last')).to_contain_text('Documenti richiesti')
                    assert test_db.one('SELECT COUNT(*) n FROM contact_actions WHERE id=?',(contact_request,))['n']==1
                    checks.append('Contact outcome is explicit; incompatible follow-up is disabled without losing its draft; pending writes lock fields and a lost acknowledgement retries without duplication')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.locator('.decision-section').scroll_into_view_if_needed()
                        screenshot(f'contact-decision-{width}')
                    checks.append('Contact form and decision recap fit 320/393/768/1440px; header and touch close remain reachable')
                    page.get_by_text('Storico contatti (1)',exact=True).click()
                    expect(page.locator('.contact-history')).to_contain_text('Broker QA')
                    screenshot('contact-history')
                    close()
                    page.locator('.rank-property').first.click()
                    expect(page.locator('.contact-last')).to_contain_text('Mandato verificato dal team')
                    close()
                    checks.append('Contact outcome persists, mandate verification requires evidence, follow-up and audit are visible')

                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Revisione',exact=True).click()
                    page.locator('#work-form select[name="stage"]').select_option('due_diligence')
                    page.get_by_label('Scadenza revisione').fill('2026-12-01')
                    page.get_by_label('Annuncio e fonte verificati').check()
                    pending_work=[]
                    def hold_work(route):
                        if route.request.method=='PUT':pending_work.append(route)
                        else:route.continue_()
                    page.route('**/api/properties/*/work',hold_work)
                    page.get_by_role('button',name='Salva revisione').click()
                    expect(page.locator('#work-form')).to_have_attribute('aria-busy','true')
                    expect(page.get_by_label('Fase',exact=True)).to_be_disabled()
                    expect(page.get_by_label('Annuncio e fonte verificati')).to_be_disabled()
                    assert len(pending_work)==1
                    pending_work[0].continue_()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    page.unroute('**/api/properties/*/work',hold_work)
                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Revisione',exact=True).click()
                    expect(page.get_by_label('Annuncio e fonte verificati')).to_be_checked()
                    expect(page.locator('#work-form select[name="stage"]')).to_have_value('due_diligence')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'review-{width}')
                    screenshot('review')
                    review_id=page.locator('#work-form').get_attribute('data-id')
                    version=int(page.locator('#work-form').get_attribute('data-version'))
                    # A separate writer changes the record while this form is still open.
                    test_db.execute('UPDATE deal_work SET version=version+1,due_date=? WHERE property_id=?',('2000-01-01',review_id))
                    test_db.execute('UPDATE properties SET review_status=? WHERE id=?',('negotiation',review_id))
                    page.get_by_label('Fase',exact=True).select_option('shortlisted')
                    page.get_by_role('button',name='Salva revisione').click()
                    expect(page.locator('#work-conflict')).to_be_visible()
                    expect(page.get_by_label('Fase',exact=True)).to_have_value('shortlisted')
                    expect(page.get_by_label('Fase',exact=True)).to_be_enabled()
                    assert test_db.one('SELECT review_status FROM properties WHERE id=?',(review_id,))['review_status']=='negotiation'
                    page.once('dialog',lambda dialog:dialog.dismiss())
                    page.get_by_role('button',name='Carica versione del team',exact=True).click()
                    expect(page.get_by_label('Fase',exact=True)).to_have_value('shortlisted')
                    screenshot('review-conflict')
                    page.once('dialog',lambda dialog:dialog.accept())
                    page.get_by_role('button',name='Carica versione del team',exact=True).click()
                    expect(page.get_by_label('Fase',exact=True)).to_have_value('negotiation')
                    expect(page.locator('#work-form')).to_have_attribute('data-version',str(version+1))
                    close()
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    checks.append('Review fields lock during pending HTTP writes; a real version conflict preserves edits and offers explicit reload/cancel')
                    nav('Pipeline')
                    expect(page.locator('.work-list')).to_be_visible()
                    page.get_by_label('Disponibilità',exact=True).select_option('closed')
                    page.get_by_label('Cerca nella pipeline').fill('nessuna-corrispondenza-qa')
                    expect(page.get_by_text('Nessun immobile corrisponde',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Azzera filtri',exact=True).click()
                    expect(page.get_by_label('Disponibilità',exact=True)).to_have_value('all')
                    expect(page.locator('.work-list')).to_be_visible()
                    page.get_by_role('button',name='Scaduti',exact=True).click()
                    expect(page.locator(f'.work-row[data-work-id="{review_id}"]')).to_be_visible()
                    expect(page.locator('.work-row').first.locator('.work-due')).to_contain_text('Scaduta')
                    page.get_by_label('Fase',exact=True).select_option('acquired')
                    expect(page.get_by_text('Nessun immobile corrisponde',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Mostra tutti',exact=True).click()
                    expect(page.get_by_label('Fase',exact=True)).to_have_value('')
                    expect(page.get_by_role('button',name='Tutti',exact=True)).to_have_attribute('aria-pressed','true')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.evaluate('window.scrollTo(0,0)')
                        screenshot(f'pipeline-list-{width}')
                        page.screenshot(path=str(output/f'pipeline-viewport-{width}.png'),full_page=False,animations='disabled')
                        if width<=600:
                            assert page.locator('.work-actions .btn').first.bounding_box()['height']>=44
                        page.get_by_role('button',name='Bacheca',exact=True).click()
                        expect(page.locator('.pipeline-board')).to_be_visible()
                        assert page.locator('.pipeline-board').bounding_box()['height']<800
                        screenshot(f'pipeline-board-{width}')
                        page.locator('.pipeline-board').focus()
                        page.keyboard.press('ArrowRight')
                        deadline=time.monotonic()+2
                        while page.locator('.pipeline-board').evaluate('(el)=>el.scrollLeft')<=0 and time.monotonic()<deadline:
                            page.wait_for_timeout(50)
                        assert page.locator('.pipeline-board').evaluate('(el)=>el.scrollLeft')>0
                        page.get_by_role('button',name='Elenco',exact=True).click()
                        expect(page.get_by_role('button',name='Elenco',exact=True)).to_be_focused()
                    screenshot('pipeline')
                    checks.append('Pipeline list/board, deadline filter, recovery and responsive geometry at 320–1440px')
                    checks.append('Pipeline stage, due date and human checklist persist')
                    nav('Panoramica')
                    page.locator('.rank-property').first.click()
                    page.get_by_role('button',name='Scenario economico',exact=True).click()
                    page.get_by_label('Nome scenario',exact=True).fill('QA scenario')
                    page.get_by_label('Prezzo di acquisto (€)',exact=True).fill('100000')
                    page.get_by_label('Rivendita ipotizzata (€)',exact=True).fill('160000')
                    page.get_by_label('Lavori (€)',exact=True).fill('20000')
                    page.get_by_label('ROI obiettivo (%)',exact=True).fill('20')
                    page.locator('.scenario-stress > summary').click()
                    page.get_by_label('Stress: ritardo (mesi)',exact=True).fill('9')
                    page.get_by_role('button',name='Calcola',exact=True).click()
                    expect(page.locator('#scenario-result')).to_contain_text('ROI semplice')
                    expect(page.locator('#scenario-result')).to_contain_text('Acquisto massimo sotto stress')
                    expect(page.locator('#scenario-result')).to_contain_text('ritardo 9 mesi')
                    page.locator('#scenario-result').scroll_into_view_if_needed()
                    screenshot('scenario')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.locator('#scenario-result h3').evaluate('(el)=>el.scrollIntoView({block:"start"})')
                        close_box=page.get_by_role('button',name='Chiudi finestra',exact=True).bounding_box()
                        assert close_box and close_box['y']>=0 and close_box['y']+close_box['height']<=page.viewport_size['height']
                        assert close_box['width']>=44 and close_box['height']>=44
                        screenshot(f'scenario-results-{width}')
                        page.locator('#scenario-form').scroll_into_view_if_needed()
                        screenshot(f'scenario-inputs-{width}')
                    checks.append('Scenario inputs/results fit 320/393/768/1440px with close control always in view')
                    page.locator('.scenario-stress > summary').click()
                    page.locator('.scenario-body').evaluate('(el)=>el.scrollTop=0')
                    screenshot('scenario-overview')
                    page.get_by_label('Nome scenario',exact=True).fill('QA scenario rinominato')
                    expect(page.locator('#scenario-result')).to_contain_text('ROI semplice')
                    page.get_by_label('Nome scenario',exact=True).fill('QA scenario')
                    page.get_by_label('ROI obiettivo (%)',exact=True).fill('21')
                    expect(page.locator('#scenario-result')).to_contain_text('Ipotesi modificate: ricalcola.')
                    page.get_by_label('ROI obiettivo (%)',exact=True).fill('20')
                    pending_scenarios=[]
                    def hold_scenario(route):pending_scenarios.append(route)
                    page.route('**/api/scenarios/calculate',hold_scenario)
                    page.get_by_role('button',name='Calcola',exact=True).click()
                    expect(page.locator('#scenario-form')).to_have_attribute('aria-busy','true')
                    expect(page.get_by_role('button',name='Calcola',exact=True)).to_be_disabled()
                    expect(page.get_by_role('button',name='Salva scenario',exact=True)).to_be_disabled()
                    page.get_by_label('Lavori (€)',exact=True).fill('21000')
                    pending_scenarios.pop().continue_()
                    expect(page.locator('#scenario-form')).to_have_attribute('aria-busy','false')
                    expect(page.locator('#scenario-result')).to_contain_text('Ipotesi modificate: ricalcola.')
                    page.get_by_label('Lavori (€)',exact=True).fill('20000')
                    page.get_by_role('button',name='Calcola',exact=True).click()
                    expect(page.locator('#scenario-form')).to_have_attribute('aria-busy','true')
                    page.get_by_label('Nome scenario',exact=True).fill('QA scenario rinominato')
                    pending_scenarios.pop().continue_()
                    expect(page.locator('#scenario-result')).to_contain_text('ROI semplice')
                    expect(page.get_by_label('Nome scenario',exact=True)).to_have_value('QA scenario rinominato')
                    page.get_by_label('Nome scenario',exact=True).fill('QA scenario')
                    page.get_by_role('button',name='Calcola',exact=True).click()
                    expect(page.locator('#scenario-form')).to_have_attribute('aria-busy','true')
                    pending_scenarios.pop().abort('failed')
                    expect(page.locator('#modal-error')).to_have_text('Connessione non disponibile.')
                    expect(page.get_by_role('button',name='Calcola',exact=True)).to_be_enabled()
                    expect(page.get_by_role('button',name='Salva scenario',exact=True)).to_be_enabled()
                    expect(page.get_by_label('Lavori (€)',exact=True)).to_have_value('20000')
                    page.unroute('**/api/scenarios/calculate',hold_scenario)
                    checks.append('Pending calculations lock both actions, discard stale numeric results, retain name edits and recover from network errors')
                    page.get_by_role('button',name='Salva scenario',exact=True).click()
                    expect(page.locator('.saved-scenarios')).to_contain_text('QA scenario')
                    expect(page.locator('#scenario-state')).to_have_text('Salvato')
                    expect(page.get_by_label('Prezzo di acquisto (€)',exact=True)).to_have_value('100000')
                    expect(page.locator('#scenario-result')).to_contain_text('ROI semplice')
                    expect(page.get_by_role('button',name='Salva copia',exact=True)).to_be_visible()
                    page.get_by_label('Lavori (€)',exact=True).fill('21000')
                    page.once('dialog',lambda dialog:dialog.dismiss())
                    page.locator('[data-action="load-scenario"]').first.click()
                    expect(page.get_by_label('Lavori (€)',exact=True)).to_have_value('21000')
                    page.once('dialog',lambda dialog:dialog.accept())
                    page.locator('[data-action="load-scenario"]').first.click()
                    expect(page.get_by_label('Lavori (€)',exact=True)).to_have_value('20000')
                    expect(page.get_by_label('Prezzo di acquisto (€)',exact=True)).to_have_value('100000')
                    expect(page.get_by_label('ROI obiettivo (%)',exact=True)).to_have_value('20')
                    expect(page.get_by_label('Stress: ritardo (mesi)',exact=True)).to_have_value('9')
                    page.get_by_label('Nome scenario',exact=True).fill('QA copia')
                    page.get_by_role('button',name='Salva copia',exact=True).click()
                    expect(page.locator('[data-action="load-scenario"]')).to_have_count(2)
                    page.get_by_label('Lavori (€)',exact=True).fill('22000')
                    page.once('dialog',lambda dialog:dialog.accept())
                    page.get_by_role('button',name='Elimina scenario QA copia',exact=True).click()
                    expect(page.locator('[data-action="load-scenario"]')).to_have_count(1)
                    expect(page.get_by_label('Lavori (€)',exact=True)).to_have_value('22000')
                    expect(page.get_by_label('Nome scenario',exact=True)).to_have_value('QA copia')
                    expect(page.locator('#scenario-state')).to_have_text('Bozza')
                    expect(page.get_by_role('button',name='Salva scenario',exact=True)).to_be_visible()
                    checks.append('Scenario save preserves inputs/results; replacing dirty edits requires confirmation; save-copy and deletion preserve the current draft')
                    checks.append('Target ROI, purchase ceiling and combined stress persist in the platform')
                    close()
                    page.locator('.rank-property').first.click()
                    with page.expect_download() as scenario_download:
                        page.get_by_role('link',name='Excel',exact=True).click()
                    scenario_download.value.save_as(output/'scenario.xlsx')
                    scenario_book=load_workbook(output/'scenario.xlsx',data_only=True)
                    scenario_row=next(r for r in scenario_book['Scenari'].iter_rows(min_row=2,values_only=True) if r[1]=='QA scenario')
                    assert scenario_row[12]==20 and scenario_row[15]==9
                    checks.append('Saved platform scenarios exported with identical assumptions and results')
                    page.get_by_role('button',name='Comparabili',exact=True).click()
                    expect(page.locator('.comp-median')).to_contain_text('Mediana')
                    screenshot('comparables')
                    close()
                    checks.append('Scenario calculation, saved assumptions, reload and honest comparables')
                    from support.market import seed_market
                    market_fixture=seed_market(test_db,test_settings)
                    nav('Mercato')
                    expect(page.get_by_role('heading',name='Prezzi di zona',exact=True)).to_be_visible()
                    page.get_by_role('button',name='Importa prezzi di zona',exact=True).click()
                    expect(page.locator('#import-kind')).to_have_value('benchmarks')
                    close()
                    screenshot('market')
                    expect(page.locator('.benchmark-item')).to_have_count(20)
                    first_benchmark=page.locator('.benchmark-item').first.inner_text()
                    held_bench=[]
                    def fail_benchmark(route):route.abort('failed')
                    page.route('**/api/benchmarks/catalog?*',fail_benchmark)
                    page.get_by_role('button',name='Avanti',exact=True).click()
                    expect(page.locator('#benchmark-results')).to_contain_text('Riferimenti non disponibili')
                    expect(page.locator('.benchmark-item')).to_have_count(0)
                    page.unroute('**/api/benchmarks/catalog?*',fail_benchmark)
                    page.get_by_role('button',name='Riprova',exact=True).click()
                    expect(page.locator('.benchmark-item')).to_have_count(20)
                    expect(page.locator('.benchmark-pagination')).to_contain_text('Pagina 2')
                    assert page.locator('.benchmark-item').first.inner_text()!=first_benchmark
                    page.locator('#benchmark-query').fill('QA città benchmark')
                    with page.expect_response('**/api/benchmarks/catalog?*'):
                        page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    expect(page.locator('#benchmark-query')).to_have_value('QA città benchmark')
                    page.locator('#benchmark-filters').get_by_role('button',name='Cerca',exact=True).click()
                    expect(page.locator('.benchmark-item')).to_have_count(1)
                    expect(page.locator('.benchmark-range')).to_contain_text('USD / m²')
                    expect(page.locator('#toasts .toast')).to_have_count(0,timeout=12000)
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'benchmark-filter-{width}')
                    page.get_by_role('button',name='Azzera',exact=True).click()
                    expect(page.locator('.benchmark-item')).to_have_count(20)
                    checks.append('Benchmark inventory: server pagination, retry without stale rows, original currency and responsive filtered results')
                    page.get_by_role('button',name='Consulta OMI',exact=True).click()
                    expect(page.locator('#omi-form')).to_be_visible()
                    page.get_by_label('Provincia',exact=True).select_option('MI')
                    expect(page.get_by_label('Comune OMI',exact=True)).to_be_enabled()
                    page.get_by_label('Comune OMI',exact=True).select_option('F205')
                    expect(page.get_by_label('Zona OMI',exact=True)).to_be_enabled()
                    expect(page.get_by_role('button',name='Consulta quotazioni',exact=True)).to_be_disabled()
                    page.get_by_label('Zona OMI',exact=True).select_option('B1')
                    held_quotes=[]
                    def hold_quote(route):held_quotes.append(route)
                    page.route('**/api/omi/quotes?*',hold_quote)
                    with page.expect_request('**/api/omi/quotes?*'):
                        page.get_by_role('button',name='Consulta quotazioni',exact=True).click()
                    expect(page.locator('#omi-form')).to_have_attribute('aria-busy','true')
                    page.get_by_label('Zona OMI',exact=True).select_option('D1')
                    expect(page.locator('#omi-result')).to_be_empty()
                    held_quotes[0].continue_()
                    page.unroute('**/api/omi/quotes?*',hold_quote)
                    page.get_by_label('Destinazione OMI',exact=True).select_option('C')
                    page.get_by_role('button',name='Consulta quotazioni',exact=True).click()
                    expect(page.locator('#omi-result')).to_contain_text('QA C D1')
                    expect(page.locator('#omi-result')).not_to_contain_text('QA R B1')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'omi-result-{width}')
                        assert page.locator('.omi-modal').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                    page.get_by_label('Destinazione OMI',exact=True).select_option('T')
                    expect(page.locator('#omi-result')).to_be_empty()
                    def fail_quote(route):route.abort('failed')
                    page.route('**/api/omi/quotes?*',fail_quote)
                    page.get_by_role('button',name='Consulta quotazioni',exact=True).click()
                    expect(page.locator('#modal-error')).to_contain_text('Connessione non disponibile')
                    page.unroute('**/api/omi/quotes?*',fail_quote)
                    page.get_by_role('button',name='Riprova',exact=True).click()
                    expect(page.locator('#omi-result')).to_contain_text('QA T D1')
                    close()
                    checks.append('OMI through synthetic cached documents: explicit zone, late quote discarded after selection changes, usage invalidation and network retry')
                    test_db.execute('DELETE FROM benchmarks WHERE id=?',(market_fixture,))
                    nav('Inbox')
                    expect(page.get_by_role('heading',name='Inbox',exact=True)).to_be_visible()
                    expect(page.locator('#inbox-results')).to_have_attribute('aria-busy','false')
                    from app.services.operations import notify
                    qa_user=test_db.one('SELECT id FROM users WHERE email=?',('ui-test@vedra.local',))['id']
                    test_db.execute('INSERT INTO notification_reads(notification_id,user_id,read_at) SELECT id,?,? FROM notifications WHERE is_demo=0 ON CONFLICT DO NOTHING',(qa_user,now()))
                    for kind,title,body,target in [
                        ('price_change','Prezzo modificato','Milano · Ufficio da ristrutturare',contact_row['id']),
                        ('availability_change','Disponibilità aggiornata','Annuncio non più disponibile',contact_row['id']),
                        ('source_blocked','Fonte da verificare','Acquisizione interrotta. La fonte non ha risposto.',None),
                    ]:
                        notify(test_db,test_settings,kind=kind,title=title,body=body,property_id=target,dedupe_key='inbox-qa-'+kind)
                    page.get_by_role('button',name='Aggiorna',exact=True).click()
                    # Wait for the refresh render: a click during it can land on the replaced button.
                    expect(page.locator('#inbox-results')).to_have_attribute('aria-busy','false')
                    expect(page.locator('#inbox-unread .notification-count')).to_have_text('3')
                    page.locator('#inbox-unread').click()
                    expect(page.locator('.notification-row')).to_have_count(3)
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        buttons=page.locator('.notification-toolbar .segmented button')
                        for button in buttons.all():
                            assert button.evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
                            assert button.bounding_box()['height']>=44
                        first_box,second_box=[button.bounding_box() for button in buttons.all()]
                        assert first_box['x']+first_box['width']<=second_box['x']
                        # Measure a settled list: a background refresh can re-render rows mid-loop.
                        expect(page.locator('#inbox-results')).to_have_attribute('aria-busy','false')
                        heights=page.locator('.notification-actions button').evaluate_all('els=>els.map(el=>el.getBoundingClientRect().height)')
                        assert heights and min(heights)>=44
                        screenshot(f'inbox-{width}')
                    page.get_by_label('Tipo di evento',exact=True).select_option('source_blocked')
                    expect(page.locator('.notification-row')).to_have_count(1)
                    expect(page.locator('#inbox-kind')).to_be_focused()
                    expect(page.locator('.notification-row [data-action="notification-open"]')).to_have_count(0)
                    page.get_by_role('button',name='Segna come letta',exact=True).click()
                    expect(page.get_by_role('heading',name='Nessuna notifica da leggere')).to_be_visible()
                    page.get_by_label('Tipo di evento',exact=True).select_option('price_change')
                    expect(page.locator('.notification-row')).to_have_count(1)
                    page.get_by_role('button',name='Apri immobile',exact=True).click()
                    expect(page.locator('.property-drawer')).to_be_visible()
                    assert test_db.one('SELECT r.read_at FROM notification_reads r JOIN notifications n ON n.id=r.notification_id WHERE n.dedupe_key=? AND r.user_id=?',('inbox-qa-price_change',qa_user))
                    close()
                    page.get_by_label('Tipo di evento',exact=True).select_option('all')
                    page.get_by_role('button',name='Segna l’intera Inbox come letta',exact=True).click()
                    expect(page.get_by_role('heading',name='Nessuna notifica da leggere')).to_be_visible()
                    checks.append('Inbox: type filters, personal reads, explicit property opening and responsive layouts')
                    # Older unread events must remain reachable beyond the legacy 200-row window.
                    for n in range(205):
                        test_db.execute('INSERT INTO notifications VALUES(?,?,?,?,?,?,?,?,?)',
                            (f'qa-inbox-{n:03d}','source_blocked',f'Evento storico {n}','Fonte di collaudo',None,None,0,'2000-01-01T00:00:00+00:00',f'qa-inbox-{n:03d}'))
                    test_db.execute('INSERT INTO notification_reads(notification_id,user_id,read_at) SELECT id,?,? FROM notifications WHERE id LIKE ? AND id<>? ON CONFLICT DO NOTHING',
                        (qa_user,now(),'qa-inbox-%','qa-inbox-000'))
                    page.get_by_role('button',name='Aggiorna',exact=True).click()
                    expect(page.locator('.notification-row')).to_have_count(1)
                    expect(page.locator('.notification-row')).to_contain_text('Evento storico 0')
                    page.locator('#inbox-all').click()
                    expect(page.locator('.notification-row')).to_have_count(40)
                    def fail_more(route):
                        if 'before_id=' in route.request.url:route.abort('failed')
                        else:route.continue_()
                    page.route('**/api/notifications/feed?*',fail_more)
                    page.get_by_role('button',name='Mostra altre',exact=True).click()
                    expect(page.locator('.notification-error')).to_contain_text('Connessione non disponibile')
                    expect(page.locator('.notification-row')).to_have_count(40)
                    page.unroute('**/api/notifications/feed?*',fail_more)
                    page.get_by_role('button',name='Riprova a caricare',exact=True).click()
                    expect(page.locator('.notification-row')).to_have_count(80)
                    expect(page.locator('#inbox-more')).to_be_focused()
                    while page.get_by_role('button',name='Mostra altre',exact=True).count():
                        page.get_by_role('button',name='Mostra altre',exact=True).click()
                        expect(page.locator('#inbox-results')).to_have_attribute('aria-busy','false')
                    expect(page.get_by_role('button',name='Tutto caricato',exact=True)).to_be_disabled()
                    expect(page.locator('#inbox-results')).to_be_focused()
                    actual_ids=page.locator('.notification-row [data-action="notification-read"]').count()
                    assert actual_ids==1
                    checks.append('Inbox: old unread beyond 200 events, pagination, network retry and keyboard focus')
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
                    from support.history import seed_history,remove_history
                    history_property=page.locator('.property-link').first.get_attribute('data-id')
                    history_ids=seed_history(test_db,history_property)
                    page.locator('.property-link').first.click()
                    expect(page.locator('.history-preview li')).to_have_count(3)
                    expect(page.locator('.history-preview')).to_contain_text('36 rilevazioni')
                    page.get_by_role('button',name='Apri cronologia',exact=True).click()
                    expect(page.get_by_role('heading',name='Cronologia', exact=True)).to_be_visible()
                    expect(page.locator('.history-event')).to_have_count(30)
                    expect(page.locator('.history-movement').filter(has_text='Ribasso').first).to_contain_text('Ribasso')
                    expect(page.locator('.history-modal .modal-header')).to_contain_text(test_db.one('SELECT title FROM properties WHERE id=?',(history_property,))['title'])
                    first_observation=page.locator('.history-event').first.get_attribute('data-observation-id')
                    text_detail=page.locator('.history-text').first
                    text_detail.locator('summary').click()
                    expect(text_detail).to_contain_text('QA fine del testo storico 34')
                    expect(page.locator('.history-changes').first).to_contain_text('Disponibilità')
                    expect(page.locator('.history-changes').first).not_to_contain_text('availability')
                    text_detail.locator('summary').click()
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.locator('.history-modal').evaluate('(el)=>el.scrollTop=0')
                        screenshot(f'history-{width}')
                        assert page.get_by_role('button',name='Chiudi finestra',exact=True).bounding_box()['height']>=44
                    text_detail.locator('summary').click()
                    page.locator('.history-extra summary').first.focus()
                    page.keyboard.press('Enter')
                    expect(page.locator('.history-extra').first).to_have_attribute('open','')
                    expect(page.locator('.history-extra').first).to_contain_text('Titolo')
                    page.locator('.history-method summary').focus()
                    page.keyboard.press('Enter')
                    expect(page.locator('.history-method')).to_have_attribute('open','')
                    def fail_history_page(route):route.abort('failed')
                    page.route('**/api/properties/*/history?before=*',fail_history_page)
                    page.get_by_role('button',name='Mostra precedenti',exact=True).click()
                    expect(page.locator('.history-error')).to_contain_text('Connessione non disponibile')
                    expect(page.locator('.history-event')).to_have_count(30)
                    expect(page.locator('.history-text').first).to_have_attribute('open','')
                    page.unroute('**/api/properties/*/history?before=*',fail_history_page)
                    page.get_by_role('button',name='Riprova',exact=True).click()
                    expect(page.locator('.history-event')).to_have_count(36)
                    assert page.locator('.history-event').first.get_attribute('data-observation-id')==first_observation
                    expect(page.locator('.history-text').first).to_have_attribute('open','')
                    expect(page.locator('#history-count')).to_be_focused()
                    page.get_by_role('button',name='Torna all’immobile',exact=True).click()
                    expect(page.locator('.property-drawer')).to_be_visible()
                    with page.expect_download() as history_export:
                        page.get_by_role('link',name='Excel',exact=True).click()
                    history_export.value.save_as(output/'history.xlsx')
                    history_book=load_workbook(output/'history.xlsx',data_only=True)
                    history_rows=list(history_book['Storico'].iter_rows(min_row=2,values_only=True))
                    assert len(history_rows)==36
                    assert next(row[7] for row in history_rows if row[2]==66000)==-1.5
                    page.get_by_role('button',name='Apri cronologia',exact=True).click()
                    expect(page.locator('.history-event')).to_have_count(30)
                    pending_history=[]
                    def hold_history_page(route):pending_history.append(route)
                    page.route('**/api/properties/*/history?before=*',hold_history_page)
                    page.get_by_role('button',name='Mostra precedenti',exact=True).click()
                    expect(page.locator('#history-content')).to_have_attribute('aria-busy','true')
                    expect(page.get_by_role('button',name='Caricamento…',exact=True)).to_be_disabled()
                    close()
                    assert len(pending_history)==1
                    with page.expect_response('**/api/properties/*/history?before=*'):
                        pending_history[0].continue_()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    page.unroute('**/api/properties/*/history?before=*',hold_history_page)
                    remove_history(test_db,history_ids)
                    checks.append('Historical evidence: complete text, immutable currency, before/after layout and touch controls at 320–1440px')
                    checks.append('History pagination appends without losing open details, retries failed HTTP requests and ignores responses after closing')
                    checks.append('Advanced archive filters and evidence history through the real API')
                    page.locator('[data-select-property]').nth(0).check()
                    expect(page.get_by_role('button',name='Confronta',exact=True)).to_be_disabled()
                    expect(page.locator('#comparison-hint')).to_be_visible()
                    page.locator('[data-select-property]').nth(1).check()
                    expect(page.get_by_role('button',name='Confronta',exact=True)).to_be_enabled()
                    page.locator('[data-select-property]').nth(2).check()
                    page.locator('[data-select-property]').nth(3).check()
                    expect(page.get_by_role('button',name='Confronta',exact=True)).to_be_disabled()
                    page.locator('[data-select-property]').nth(3).uncheck()
                    page.locator('[data-select-property]').nth(2).uncheck()
                    page.get_by_role('button', name='Confronta', exact=True).click()
                    expect(page.get_by_role('heading', name='Confronto', exact=True)).to_be_visible()
                    expect(page.locator('.compare-table:visible thead th')).to_have_count(3)
                    expect(page.get_by_role('tab',name='Decisione',exact=True)).to_have_attribute('aria-selected','true')
                    expect(page.locator('#compare-panel-decision')).to_contain_text('Contatto')
                    expect(page.locator('#compare-panel-decision')).to_contain_text('Aggiornamento dati')
                    screenshot('comparison')
                    compared_ids=json.loads(page.locator('[data-action="comparison-export"]').get_attribute('data-ids'))
                    assert len(compared_ids)==2
                    for section in ['Decisione','Mercato','Dati']:
                        page.get_by_role('tab',name=section,exact=True).click()
                        expect(page.get_by_role('tabpanel')).to_have_count(1)
                        for width in [320,393,768,1440]:
                            page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                            page.locator('.comparison-body').evaluate('(el)=>el.scrollTop=0')
                            screenshot(f'comparison-{section.lower()}-{width}')
                            assert page.locator('.comparison-body').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
                            assert page.get_by_role('button',name='Chiudi finestra',exact=True).bounding_box()['height']>=44
                    page.get_by_role('tab',name='Dati',exact=True).focus()
                    page.keyboard.press('Home')
                    expect(page.get_by_role('tab',name='Decisione',exact=True)).to_be_focused()
                    page.keyboard.press('ArrowRight')
                    expect(page.get_by_role('tab',name='Mercato',exact=True)).to_be_focused()
                    expect(page.locator('#compare-panel-market')).to_be_visible()
                    for label in ['Da ristrutturare','Ristrutturato','Nuovo','OMI','Scostamento dal benchmark']:
                        expect(page.locator('#compare-panel-market')).to_contain_text(label)
                    with page.expect_download() as comparison_export:
                        page.get_by_role('button',name='Excel selezione',exact=True).click()
                    comparison_export.value.save_as(output/'comparison.xlsx')
                    comparison_book=load_workbook(output/'comparison.xlsx',data_only=True)
                    assert set(compared_ids)=={str(row[0]) for row in list(comparison_book['Selezione'].values)[1:]}
                    close()
                    checks.append('Comparison uses full property dossiers, four references, contacts and exact-selection Excel; three keyboard tabs at 320–1440px')
                    page.locator('[data-select-property]').nth(2).check()
                    page.get_by_role('button',name='Confronta',exact=True).click()
                    expect(page.locator('.compare-table:visible thead th')).to_have_count(4)
                    page.set_viewport_size({'width':320,'height':852})
                    screenshot('comparison-three-mobile')
                    assert page.locator('.comparison-body').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
                    close()
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.locator('[data-select-property]').nth(2).uncheck()
                    # A failed detail must never produce a partially populated comparison.
                    page.route('**/api/properties/'+compared_ids[0],lambda route:route.abort('failed'))
                    page.get_by_role('button',name='Confronta',exact=True).click()
                    expect(page.get_by_role('alert')).to_contain_text('Connessione non disponibile')
                    expect(page.locator('.comparison-modal')).to_have_count(0)
                    close()
                    page.unroute('**/api/properties/'+compared_ids[0])
                    pending_comparison=[]
                    def hold_comparison(route):pending_comparison.append(route)
                    page.route('**/api/properties/'+compared_ids[0],hold_comparison)
                    page.get_by_role('button',name='Confronta',exact=True).click()
                    expect(page.get_by_role('status').filter(has_text='Caricamento')).to_be_visible()
                    close()
                    assert len(pending_comparison)==1
                    with page.expect_response('**/api/properties/'+compared_ids[0]):
                        pending_comparison[0].continue_()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    page.unroute('**/api/properties/'+compared_ids[0],hold_comparison)
                    page.get_by_role('button',name='Confronta',exact=True).click()
                    expect(page.locator('.comparison-modal')).to_be_visible()
                    close()
                    checks.append('Comparison handles three assets on mobile, failed detail recovery and closing before late responses without losing selection')
                    chosen=[element.get_attribute('data-select-property') for element in page.locator('[data-select-property]:checked').all()]
                    page.get_by_label('Comune',exact=True).select_option('Monza')
                    expect(page.locator('#results-body')).to_have_attribute('aria-busy','false')
                    expect(page.locator('#selection-count')).to_have_text('2')
                    with page.expect_download() as selected_export:
                        page.get_by_role('button',name='Esporta selezione',exact=True).click()
                    selected_export.value.save_as(output/'selected.xlsx')
                    selected_book=load_workbook(output/'selected.xlsx',data_only=True)
                    selected_rows=list(selected_book['Selezione'].values)
                    assert len(selected_rows)==3, selected_rows
                    assert set(chosen)=={str(row[0]) for row in selected_rows[1:]}
                    with page.expect_download() as catalog_export:
                        page.locator('[data-export-scope="catalog"][data-format="xlsx"]').click()
                    catalog_export.value.save_as(output/'filtered.xlsx')
                    filtered_book=load_workbook(output/'filtered.xlsx',data_only=True)
                    filtered_rows=list(filtered_book['Selezione'].values)
                    assert len(filtered_rows)-1==page.locator('[data-select-property]').count()
                    assert all('Monza' in row for row in filtered_rows[1:])
                    assert len(filtered_rows)>1
                    checks.append('Excel result export follows filters while selection export preserves the chosen IDs; comparison requires 2–3')
                    page.get_by_role('button', name='Annulla selezione').click()
                    expect(page.locator('#selection-bar')).to_have_attribute('inert','')
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
                    page.evaluate('window.scrollTo(0,0)')
                    page.screenshot(path=str(output/'catalog-overview.png'),full_page=False)
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':1080 if width>700 else 852})
                        assert page.locator('.property-art').first.bounding_box()['height']<=64
                        page.locator('.card-select input').first.check()
                        for control in page.locator('#selection-bar button:not([disabled])').all():
                            box=control.bounding_box()
                            assert box['x']>=0 and box['x']+box['width']<=width+1, (width,box)
                            if width<=700:assert box['height']>=44
                        bar=page.locator('#selection-bar').bounding_box()
                        assert bar['y']>=0 and bar['y']+bar['height']<=page.viewport_size['height']+1
                        for toast in page.locator('.toast').all():
                            toast_box=toast.bounding_box()
                            assert toast_box['y']+toast_box['height']<=bar['y'], (width,toast_box,bar)
                        if width==393:page.screenshot(path=str(output/'mobile-selection.png'),full_page=False,animations='disabled')
                        page.get_by_role('button',name='Annulla selezione').click()
                        screenshot(f'catalog-layout-{width}')
                    # A failed photo must recover to the same compact, labelled header.
                    page.locator('.property-art .card-thumb').first.evaluate("e=>{const img=document.createElement('img');img.className='listing-photo';e.append(img);img.src='/api/properties/qa-missing-photo/image';}")
                    expect(page.locator('.property-art .card-thumb').first.locator('img')).to_have_count(0)
                    assert page.locator('.property-art').first.bounding_box()['height']<=64
                    checks.append('Archive geometry at 320/393/768/1440px, compact absent/failed photos, touch targets and hidden selection focus')
                    checks.append('Selection, comparison, municipal filter and card view')

                    nav('Agenti')
                    screenshot('agents')
                    page.get_by_role('button', name='Nuova ricerca', exact=True).click()
                    page.get_by_label('Nome',exact=True).fill('Milano · Verifica UI')
                    page.get_by_label('Zona o indirizzo').fill('Porta Romana')
                    page.get_by_label('Budget minimo (€)',exact=True).fill('500000')
                    page.get_by_label('Budget massimo (€)',exact=True).fill('600000')
                    page.locator('#agent-form input[name="source_ids"]').first.check()
                    page.locator('#agent-form input[name="max_listings"]').fill('8')
                    page.get_by_label('Contatto cercato',exact=True).select_option('require_direct')
                    page.locator('textarea[name="custom_prompt"]').fill('Solo cambio d’uso esplicito')
                    # Scout instructions are always visible; the disclosure only holds optional start pages.
                    page.get_by_label('Istruzioni di ricerca',exact=True).fill('Visita il catalogo del broker e verifica chi ha il mandato.')
                    expect(page.locator('[data-instruction-indicator]')).to_be_hidden()
                    # Closing is reversible within this page session; no research was submitted.
                    expect(page.locator('.research-draft-bar')).to_contain_text('Bozza non salvata')
                    page.keyboard.press('Escape')
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    assert not test_db.one('SELECT id FROM agents WHERE name=?',('Milano · Verifica UI',))
                    page.get_by_role('button',name='Nuova ricerca',exact=True).click()
                    expect(page.locator('.research-draft-bar')).to_contain_text('Bozza ripristinata')
                    expect(page.get_by_role('button',name='Riprendi bozza',exact=True)).to_have_count(0)
                    expect(page.get_by_label('Nome',exact=True)).to_have_value('Milano · Verifica UI')
                    expect(page.get_by_label('Criteri personalizzati',exact=True)).to_have_value('Solo cambio d’uso esplicito')
                    expect(page.get_by_label('Istruzioni di ricerca',exact=True)).to_have_value('Visita il catalogo del broker e verifica chi ha il mandato.')
                    assert page.evaluate('!window.dispatchEvent(new Event("beforeunload",{cancelable:true}))')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.locator('.research-draft-bar').scroll_into_view_if_needed()
                        screenshot(f'research-draft-{width}')
                        assert page.locator('.research-modal').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
                    checks.append('Unsaved research criteria and instructions survive Escape/reopen in this page session; draft status and refresh warning are explicit at 320–1440px')
                    page.locator('.research-advanced > summary').click()
                    page.get_by_label('Superficie massima (opzionale)',exact=True).fill('0')
                    page.locator('.research-advanced > summary').click()
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.locator('.research-advanced')).to_have_attribute('open','')
                    expect(page.get_by_label('Superficie massima (opzionale)',exact=True)).to_be_focused()
                    page.get_by_label('Superficie massima (opzionale)',exact=True).fill('2000')
                    page.locator('input[name="property_types"][value="office"]').check()
                    # Types and strategies are primary criteria now: only max surface and auctions count as advanced.
                    expect(page.locator('[data-filter-indicator]')).to_have_text('2 selezionati')
                    page.locator('.research-advanced > summary').click()
                    for width in (320,393,768,1440):
                        page.set_viewport_size({'width':width,'height':1080 if width>600 else 852})
                        assert page.locator('.research-modal').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                    page.locator('#asset-heading').scroll_into_view_if_needed()
                    screenshot('research-asset')
                    page.locator('#criteria-heading').scroll_into_view_if_needed()
                    screenshot('research-criteria')
                    page.set_viewport_size({'width':393,'height':852})
                    screenshot('research-mobile')
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.locator('#modal-error')).to_contain_text('richiedono Scout')
                    expect(page.locator('textarea[name="custom_prompt"]')).to_have_value('Solo cambio d’uso esplicito')
                    screenshot('agent-custom-criteria')
                    expect(page.get_by_label('Istruzioni di ricerca',exact=True)).to_have_value('Visita il catalogo del broker e verifica chi ha il mandato.')
                    page.get_by_label('Istruzioni di ricerca',exact=True).fill('')
                    expect(page.locator('[data-instruction-indicator]')).to_be_hidden()
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.locator('#modal-error')).to_contain_text('richiedono Scout')
                    page.locator('textarea[name="custom_prompt"]').fill('')
                    checks.append('Custom criteria preserve input and reject a rules-only engine')
                    pending_research=[]
                    def hold_research(route):pending_research.append(route)
                    page.route('**/api/agents',hold_research)
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.locator('#agent-form')).to_have_attribute('aria-busy','true')
                    expect(page.get_by_label('Nome',exact=True)).to_be_disabled()
                    expect(page.get_by_label('Criteri personalizzati',exact=True)).to_be_disabled()
                    page.keyboard.press('Escape')
                    expect(page.locator('#agent-form')).to_be_visible()
                    expect(page.get_by_role('button',name='Chiudi finestra',exact=True)).to_be_disabled()
                    expect(page.get_by_role('button',name='Salvataggio…',exact=True)).to_be_disabled()
                    expect(page.locator('#agent-form')).to_be_visible()
                    page.locator('.research-draft-bar').scroll_into_view_if_needed()
                    screenshot('research-saving')
                    assert len(pending_research)==1
                    pending_research.pop().abort('failed')
                    expect(page.locator('#modal-error')).to_contain_text('Connessione non disponibile')
                    expect(page.get_by_label('Nome',exact=True)).to_be_enabled()
                    expect(page.get_by_label('Nome',exact=True)).to_have_value('Milano · Verifica UI')
                    # The server commits, but the client never receives the success response.
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.locator('#agent-form')).to_have_attribute('aria-busy','true')
                    page.wait_for_timeout(100)
                    assert len(pending_research)==1
                    lost_response=pending_research.pop()
                    committed=lost_response.fetch()
                    assert committed.status==201
                    committed_id=committed.json()['id']
                    lost_response.abort('failed')
                    expect(page.locator('#modal-error')).to_contain_text('Connessione non disponibile')
                    page.unroute('**/api/agents',hold_research)
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    assert page.evaluate('window.dispatchEvent(new Event("beforeunload",{cancelable:true}))')
                    checks.append('Research save freezes fields and dismissal; a request aborted before submission preserves input and retry clears the draft only after success')
                    records=test_db.all('SELECT id FROM agents WHERE name=?',('Milano · Verifica UI',))
                    assert [row['id'] for row in records]==[committed_id]
                    checks.append('A POST committed on the server with a lost browser response retries to the same research, without duplication')
                    card = page.locator('.agent-card').filter(has=page.get_by_role('heading', name='Milano · Verifica UI'))
                    expect(card).to_be_visible()
                    criteria=json.loads(test_db.one('SELECT criteria FROM agents WHERE name=?',('Milano · Verifica UI',))['criteria'])
                    assert criteria['min_price']==500000 and criteria['max_price']==600000
                    assert criteria['location_query']=='Porta Romana'
                    assert criteria['opportunity_only'] and criteria['contact_policy']=='require_direct'
                    assert criteria['max_surface']==2000 and criteria['property_types']==['office']
                    card.get_by_role('button',name='Configura Milano · Verifica UI').click()
                    page.locator('.research-advanced > summary').click()
                    expect(page.get_by_label('Superficie massima (opzionale)',exact=True)).to_have_value('2000')
                    expect(page.locator('input[name="property_types"][value="office"]')).to_be_checked()
                    close()
                    # Drafts must not replace a newer configuration without an explicit choice.
                    edited_id=card.locator('[data-action="edit-agent"]').get_attribute('data-id')
                    card.get_by_role('button',name='Configura Milano · Verifica UI').click()
                    page.get_by_label('Budget massimo (€)',exact=True).fill('610000')
                    close()
                    cfg=load(test_db.one('SELECT criteria FROM agents WHERE id=?',(edited_id,))['criteria'])
                    cfg['max_price']=620000
                    test_db.execute('UPDATE agents SET criteria=? WHERE id=?',(dump(cfg),edited_id))
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    card.get_by_role('button',name='Configura Milano · Verifica UI').click()
                    expect(page.locator('.research-draft-bar')).to_contain_text('Configurazione aggiornata dal team')
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_have_value('620000')
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_be_disabled()
                    for width in [320,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'research-draft-conflict-{width}')
                    page.get_by_role('button',name='Riprendi bozza',exact=True).click()
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_have_value('610000')
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_be_enabled()
                    page.get_by_role('button',name='Scarta bozza',exact=True).click()
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_have_value('620000')
                    expect(page.locator('.research-draft-bar')).to_be_hidden()
                    close()
                    checks.append('Research draft recovery detects a changed team configuration; restore is explicit and discard returns to the current server values')
                    card.get_by_role('button',name='Configura Milano · Verifica UI').click()
                    page.get_by_label('Budget massimo (€)',exact=True).fill('630000')
                    cfg['max_price']=640000
                    test_db.execute('UPDATE agents SET criteria=? WHERE id=?',(dump(cfg),edited_id))
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.locator('#modal-error')).to_contain_text('altro operatore')
                    expect(page.get_by_role('button',name='Salva ricerca',exact=True)).to_be_disabled()
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_have_value('630000')
                    assert load(test_db.one('SELECT criteria FROM agents WHERE id=?',(edited_id,))['criteria'])['max_price']==640000
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        recovery=page.get_by_role('button',name='Rileggi ricerca',exact=True)
                        recovery.scroll_into_view_if_needed()
                        assert recovery.bounding_box()['height']>=44
                        assert page.locator('.research-modal').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                        screenshot(f'research-save-conflict-{width}')
                    page.get_by_role('button',name='Rileggi ricerca',exact=True).click()
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_have_value('640000')
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_be_disabled()
                    page.get_by_role('button',name='Riprendi bozza',exact=True).click()
                    expect(page.get_by_label('Budget massimo (€)',exact=True)).to_have_value('630000')
                    page.locator('#agent-form button[type="submit"]').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    assert load(test_db.one('SELECT criteria FROM agents WHERE id=?',(edited_id,))['criteria'])['max_price']==630000
                    checks.append('A server-side edit conflict preserves both versions; 320–1440px recovery rereads the team configuration and applies the draft only after explicit choice')
                    checks.append('Grouped research form preserves collapsed filters, reveals invalid fields, retains prompts on error and fits 320–1440px')
                    expect(card).to_contain_text('Porta Romana')
                    # Secondary actions live in the card menu; Esegui ora and Configura stay visible.
                    card.locator('.card-menu > summary').click()
                    card.get_by_role('button',name='Verifica accesso',exact=True).click()
                    expect(page.get_by_role('heading',name='Verifica accesso')).to_be_visible()
                    expect(page.locator('.preflight-source')).to_contain_text('non trova nuovi annunci online')
                    screenshot('agent-preflight')
                    close()
                    checks.append('Agent preflight distinguishes configuration from live acquisition')
                    card.get_by_role('button', name='Esegui ora', exact=True).click()
                    expect(page.locator('#run-content .run-meta')).to_contain_text('Completata', timeout=30_000)
                    expect(page.locator('#run-content')).to_contain_text('Regole locali')
                    screenshot('run')
                    close()
                    card.locator('.card-menu > summary').click()
                    card.get_by_role('button', name='Pausa', exact=True).click()
                    expect(card.locator('.badge')).to_contain_text('In pausa')
                    card.locator('.card-menu > summary').click()
                    expect(card.get_by_role('button', name='Riprendi')).to_be_visible()
                    card.get_by_role('button', name='Riprendi').click()
                    expect(card.locator('.badge')).not_to_contain_text('In pausa')
                    card.locator('.card-menu > summary').click()
                    expect(card.get_by_role('button', name='Pausa', exact=True)).to_be_visible()
                    page.keyboard.press('Escape')
                    checks.append('Create, execute, inspect logs, pause and resume a real queued job')

                    # Controlled database fixture, real HTTP/SSE updates; no remote model call.
                    from support.research import research_review
                    review_agent,review_run,review_property=research_review(test_db)
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    review_card=page.locator('.agent-card').filter(has=page.get_by_role('heading',name='Ricerca · collaudo criteri'))
                    review_card.get_by_role('button',name='Mostra esecuzione',exact=True).click()
                    expect(page.locator('.run-analysis')).to_contain_text('0 / 1 risposte accettate')
                    expect(page.locator('.run-analysis')).to_contain_text('1 annuncio da analizzare')
                    expect(page.locator('#run-log')).not_to_have_attribute('open','')
                    page.locator('#run-instructions-toggle').click()
                    expect(page.locator('#run-instructions')).to_contain_text('Brief consegnato a Hermes')
                    expect(page.locator('#run-instructions')).to_contain_text('Mandato esclusivo documentato')
                    page.locator('#run-log-toggle').click()
                    page.locator('#run-log-toggle').focus()
                    test_db.event(review_run,'classify','Aggiornamento QA durante la lettura.')
                    expect(page.locator('#run-log')).to_contain_text('Aggiornamento QA durante la lettura.')
                    expect(page.locator('#run-instructions')).to_have_attribute('open','')
                    expect(page.locator('#run-log')).to_have_attribute('open','')
                    expect(page.locator('#run-log-toggle')).to_be_focused()
                    test_db.execute("UPDATE runs SET status='partial',finished_at=? WHERE id=?",(now(),review_run))
                    test_db.event(review_run,'finish','Una fonte da ricontrollare.','warning')
                    expect(page.locator('.run-outcome')).to_contain_text('Ricerca parziale')
                    expect(page.locator('.run-analysis')).to_contain_text('Avvia una nuova ricerca')
                    page.locator('#run-instructions-toggle').click()
                    page.locator('#run-log-toggle').click()
                    screenshot('research-progress')
                    for width in (320,393,768,1440):
                        page.set_viewport_size({'width':width,'height':852 if width<600 else 1080})
                        assert page.locator('.run-modal').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                        if width==393:screenshot('research-progress-mobile')
                    page.get_by_role('button',name='Risultati attuali della ricerca',exact=True).click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    expect(page.locator('#results-body')).to_contain_text('Nessun annuncio in questa vista')
                    checks.append('Run evidence shows pending AI work; live updates preserve open panels and keyboard focus; partial runs stay explicit')
                    # Open the excluded asset from the archive to inspect each custom requirement.
                    nav('Opportunità')
                    page.get_by_role('button',name='Azzera',exact=True).click()
                    expect(page.locator(f'[data-action="property"][data-id="{review_property}"]').first).to_be_visible()
                    page.locator(f'[data-action="property"][data-id="{review_property}"]').first.click()
                    check=page.locator('.screening-item').filter(has_text='Ricerca · collaudo criteri')
                    check.locator('.qualitative-check > summary').click()
                    expect(check).to_contain_text('1 / 2 coerenti')
                    expect(check.locator('.criterion-result')).to_have_count(2)
                    expect(check.locator('.criterion-result').nth(1)).to_contain_text('Da verificare')
                    expect(check.locator('blockquote')).to_be_hidden()
                    check.locator('.criterion-evidence > summary').click()
                    expect(check.locator('blockquote')).to_be_visible()
                    check.locator('.qualitative-check').scroll_into_view_if_needed()
                    screenshot('criterion-evidence')
                    page.set_viewport_size({'width':393,'height':852})
                    check.locator('.qualitative-check').scroll_into_view_if_needed()
                    screenshot('criterion-evidence-mobile')
                    close();page.set_viewport_size({'width':1440,'height':1080})
                    checks.append('Per-criterion assessment keeps uncertain requirements visible and quotes available without duplication')

                    nav('Fonti e importazioni')
                    page.get_by_role('button', name='Importa dati', exact=True).click()
                    form=page.locator('#import-form')
                    # The input mode is explicit; a selected file never overrides pasted text.
                    page.get_by_label('Incolla testo',exact=True).check()
                    page.get_by_label('Contenuto da importare',exact=True).fill('title,price,price\nCasa,100000,200000')
                    form.locator('[name="permission_confirmed"]').check()
                    form.locator('[type="submit"]').click()
                    expect(form.locator('#modal-error')).to_contain_text('colonne con lo stesso nome')
                    expect(form.locator('[name="content"]')).to_have_value('title,price,price\nCasa,100000,200000')
                    expect(form.locator('#modal-error')).to_be_focused()
                    page.get_by_label('Tipo di importazione',exact=True).select_option('html')
                    expect(form.locator('[name="source_url"]')).to_be_visible()
                    expect(form.locator('[name="source_url"]')).to_have_attribute('required','')
                    page.get_by_label('Tipo di importazione',exact=True).select_option('csv')
                    expect(form.locator('[name="source_url"]')).to_be_hidden()
                    page.get_by_label('Carica file',exact=True).check()
                    page.get_by_label('File da importare').set_input_files(str(ROOT / 'backend/tests/fixtures/imports/properties-demo.csv'))
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'import-form-{width}')
                        assert page.locator('.import-modal').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                        assert page.get_by_role('button',name='Chiudi finestra',exact=True).bounding_box()['height']>=44
                    held_import=[]
                    def hold_import(route):held_import.append(route)
                    page.route('**/api/imports',hold_import)
                    with page.expect_request('**/api/imports'):
                        form.locator('[type="submit"]').click()
                    expect(form.locator('[name="kind"]')).to_be_disabled()
                    expect(page.get_by_role('button',name='Annulla',exact=True)).to_be_disabled()
                    page.keyboard.press('Escape')
                    expect(form).to_be_visible()
                    assert len(held_import)==1
                    assert held_import[0].fetch().status==200
                    held_import[0].abort('failed')
                    expect(form.locator('#modal-error')).to_have_text('Connessione non disponibile.')
                    expect(form.locator('[name="kind"]')).to_be_enabled()
                    expect(form.locator('#file-name')).to_contain_text('properties-demo.csv')
                    page.unroute('**/api/imports',hold_import)
                    form.locator('[type="submit"]').click()
                    expect(page.get_by_role('heading', name='Importazione completata')).to_be_visible()
                    assert test_db.one("SELECT COUNT(*) n FROM properties WHERE source_id='imports-real'")['n']==3
                    expect(page.locator('.import-result-stats>div').nth(0)).to_contain_text('0')
                    expect(page.locator('.import-result-stats>div').nth(2)).to_contain_text('3')
                    expect(page.locator('.import-result-stats')).to_contain_text('Nuovi')
                    expect(page.locator('.import-result-stats')).to_contain_text('Invariati')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'import-result-{width}')
                        assert page.locator('.import-modal').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                    page.get_by_role('button',name='Apri immobili importati',exact=True).click()
                    expect(page.locator('#catalog-source_id')).to_have_value('imports-real')
                    expect(page.locator('.catalog-source-filter')).to_contain_text('Import cliente')
                    expect(page.locator('#results-body')).to_have_attribute('aria-busy','false')
                    expect(page.locator('[data-select-property]')).to_have_count(3)
                    nav('Fonti e importazioni')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'sources-{width}')
                    expect(page.locator('.source-imports [data-action="probe-source"]')).to_have_count(0)
                    checks.append('Import mode is explicit, malformed CSV preserves input, HTML URL is conditional, pending writes lock controls/Escape and a lost acknowledgement retries without duplicates')
                    checks.append('Import result shows counts and opens the matching source; form/result/source directory fit 320–1440px')


                    page.get_by_role('button', name='Collega fonte', exact=True).click()
                    form=page.locator('#source-form')
                    for portal,domain in [('Immobiliare.it','www.immobiliare.it'),('idealista','www.idealista.it'),('Casa.it','www.casa.it')]:
                        form.get_by_role('radio', name=portal, exact=True).check()
                        expect(form.locator('[name="domain"]')).to_have_value(domain)
                        expect(form.locator('[name="browser_navigation"]')).to_be_checked()
                        expect(form.locator('[name="permission_confirmed"]')).not_to_be_checked()
                    close()
                    checks.append('Three portal presets configure browser acquisition without claiming permission or creating sources')
                    page.get_by_role('button', name='Collega fonte', exact=True).click()
                    form=page.locator('#source-form')
                    form.locator('[name="name"]').fill('Fixture browser source')
                    form.locator('[name="domain"]').fill('catalog.example')
                    form.locator('[name="search_url"]').fill('https://catalog.example/search')
                    form.locator('[name="browser_navigation"]').check()
                    form.locator('[name="permission_note"]').fill('Local fixture only; no external acquisition.')
                    form.locator('[name="permission_confirmed"]').check()
                    form.locator('button[type="submit"]').click()
                    source_card=page.locator('.source-card').filter(has_text='Fixture browser source')
                    expect(source_card).to_contain_text('Browser')
                    source_card.get_by_role('button', name='Configura', exact=True).click()
                    expect(page.locator('#source-form [name="browser_navigation"]')).to_be_checked()
                    close()
                    checks.append('Browser navigation setting persists through the source form')
                    source_id=test_db.one("SELECT id FROM sources WHERE name='Fixture browser source'")['id']
                    test_db.execute("UPDATE sources SET status='blocked',last_error=?,last_checked=? WHERE id=?",('HTTP 403: accesso non disponibile nella fixture QA.',now(),source_id))
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    expect(source_card).to_contain_text('Accesso non riuscito')
                    expect(source_card.locator('.source-metrics')).to_contain_text('—')
                    source_card.locator('.source-error summary').focus();page.keyboard.press('Enter')
                    expect(source_card.locator('.source-error')).to_contain_text('HTTP 403')
                    expect(page.locator('#toasts .toast')).to_have_count(0,timeout=12000)
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.evaluate('window.scrollTo(0,0)')
                        screenshot(f'source-blocked-{width}')
                        for button in source_card.locator('.btn').all():
                            assert button.bounding_box()['height']>=44
                    source_card.get_by_role('button',name='Sospendi Fixture browser source',exact=True).click()
                    expect(source_card.get_by_role('button',name='Verifica accesso',exact=True)).to_be_disabled()
                    source_card.get_by_role('button',name='Abilita Fixture browser source',exact=True).click()
                    expect(source_card.get_by_role('button',name='Verifica accesso',exact=True)).to_be_enabled()
                    checks.append('Blocked web source has no artificial completeness, readable diagnosis, 44px actions and reversible suspension')


                    page.get_by_role('button',name='Importa dati',exact=True).click()
                    csv_text='listing_key,title,city,zone,price,surface,currency,transaction_type,property_type,condition,area_basis,latitude,longitude,description\nqa-map,TEST MAPPA SINTETICO,Milano,Test,150000,100,EUR,sale,office,good,commercial,45.46,9.19,Record sintetico di collaudo\n'
                    page.get_by_label('File da importare').set_input_files({'name':'qa-map-demo.csv','mimeType':'text/csv','buffer':csv_text.encode()})
                    page.locator('#import-form input[name="permission_confirmed"]').check()
                    page.locator('#import-form button[type="submit"]').click()
                    expect(page.get_by_role('heading',name='Importazione completata')).to_be_visible()
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
                    from support.quality import seed_quality
                    quality_ids=seed_quality(test_db,test_settings)
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    expect(page.locator('.quality-pair')).to_have_count(1)
                    expect(page.locator('#toasts .toast')).to_have_count(0,timeout=12000)
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'quality-{width}')
                        for button in page.locator('.quality-field .btn,.quality-pair-actions .btn,.quality-tabs button').all():
                            assert button.bounding_box()['height']>=44
                        if width==1440:
                            facts=page.locator('.quality-candidate-facts').all()
                            assert abs(facts[0].bounding_box()['y']-facts[1].bounding_box()['y'])<2
                    page.evaluate('window.scrollTo(0,0)')
                    page.screenshot(path=str(output/'quality-desktop-summary.png'))
                    page.locator('.quality-pair').scroll_into_view_if_needed()
                    page.screenshot(path=str(output/'quality-desktop-duplicates.png'))
                    page.locator('.quality-method summary').focus();page.keyboard.press('Enter')
                    expect(page.locator('.quality-method')).to_have_attribute('open','')
                    missing_count=test_db.one('SELECT COUNT(*) n FROM properties WHERE is_demo=0 AND price IS NULL')['n']
                    page.get_by_role('button',name='Vedi annunci senza prezzo',exact=True).click()
                    expect(page.locator('.catalog-missing-filter')).to_contain_text('Dato mancante: Prezzo')
                    expect(page.locator('[data-select-property]')).to_have_count(missing_count)
                    expect(page.get_by_label('Disponibilità',exact=True)).to_have_value('all')
                    expect(page.locator(f'[data-select-property="{quality_ids[2]}"]')).to_have_count(1)
                    with page.expect_download() as missing_export:
                        page.get_by_role('button',name='Excel',exact=True).click()
                    missing_export.value.save_as(output/'missing-prices.xlsx')
                    assert load_workbook(output/'missing-prices.xlsx',data_only=True)['Selezione'].max_row==missing_count+1
                    page.get_by_role('button',name='Rimuovi filtro',exact=True).click()
                    expect(page.locator('.catalog-missing-filter')).to_have_count(0)
                    expect(page.locator('#results-body')).to_have_attribute('aria-busy','false')
                    nav('Qualità dei dati')
                    expect(page.locator('.quality-pair')).to_have_count(1)
                    page.get_by_role('button',name='QA · Ufficio centrale',exact=True).click()
                    expect(page.locator('.property-drawer')).to_contain_text('QA · Ufficio centrale')
                    close()
                    held_review=[]
                    def hold_duplicate_review(route):held_review.append(route)
                    page.route('**/api/duplicates/review',hold_duplicate_review)
                    page.get_by_role('button',name='Stesso asset',exact=True).click()
                    expect(page.get_by_role('button',name='Distinti',exact=True)).to_be_disabled()
                    assert len(held_review)==1
                    held_review[0].continue_()
                    expect(page.get_by_role('heading',name='Nessuna coppia da verificare')).to_be_visible()
                    page.unroute('**/api/duplicates/review',hold_duplicate_review)
                    page.locator('#quality-reviewed').click()
                    expect(page.locator('.quality-pair')).to_have_count(1)
                    expect(page.locator('.quality-pair')).to_contain_text('Stesso asset confermato')
                    expect(page.locator('#quality-reviewed')).to_be_focused()
                    page.get_by_role('button',name='Distinti',exact=True).click()
                    expect(page.locator('.quality-pair-actions .quiet-pill')).to_have_text('Annunci distinti')
                    a,b=sorted(quality_ids[:2])
                    assert test_db.one('SELECT decision FROM duplicate_reviews WHERE a=? AND b=?',(a,b))['decision']=='distinct'
                    checks.append('Data quality: missing-field drilldown includes archived listings and exports the identical filtered result')
                    checks.append('Duplicate review: source comparison, aligned facts, keyboard focus, pending-write lock and persistent reversible decisions at 320–1440px')
                    nav('Impostazioni')
                    # Without a model or Hermes there is nothing to verify: no dead buttons, an explicit state.
                    expect(page.locator('[data-action="runtime-test"], [data-action="ai-test"]')).to_have_count(0)
                    expect(page.locator('.settings-panel').first).to_contain_text('Nessun modello configurato')
                    checks.append('Data quality and honest missing model status')
                    nav('Broker')
                    expect(page.get_by_role('heading',name='Broker',exact=True)).to_be_visible()
                    expect(page.locator('.page-summary')).to_contain_text('inserzionist')
                    page.get_by_label('Prezzo minimo degli annunci',exact=True).select_option('4000000')
                    expect(page.locator('.broker-surface')).to_be_visible()
                    for width in (393,1440):
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        screenshot(f'brokers-{width}')
                    checks.append('Broker directory loads, filters by minimum price and fits 393–1440px')

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
                    expect(page.get_by_role('heading', name='Ricerche', exact=True)).to_be_visible()
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
                    page.get_by_role('button',name='Azzera filtri',exact=True).click()
                    expect(page.locator('#property-search')).to_have_value('')
                    expect(page.locator('.property-card')).to_have_count(42)  # Includes the two published quality fixtures.
                    checks.append('Mobile archive, reduced motion and filtered empty state')

                    from support.decision import decision_dataset
                    user_id=test_db.one("SELECT id FROM users WHERE email='ui-test@vedra.local'")['id']
                    subject_id,linked_id,_=decision_dataset(test_db,test_settings,user_id)
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    page.get_by_role('button',name='Azzera',exact=True).click()
                    page.locator('#property-search').fill('QA · Asset da approfondire')
                    expect(page.locator('#results-body')).to_contain_text('QA · Asset da approfondire')
                    page.locator(f'[data-action="property"][data-id="{subject_id}"]').first.click()
                    expect(page.locator('.cross-source-summary')).to_contain_text('Prezzi richiesti diversi')
                    page.locator('.cross-source-details > summary').click()
                    expect(page.locator('.cross-source-row')).to_have_count(2)
                    page.get_by_role('heading',name='Contatto e verifiche',exact=True).scroll_into_view_if_needed()
                    screenshot('cross-source-dossier')
                    expect(page.locator('.reference-card').first).to_contain_text('3 annunci · 3 fonti')
                    expect(page.locator('.reference-card').first).to_contain_text('Fascia centrale')
                    expect(page.locator('.omi-reference')).to_contain_text(re.compile(r'2[.\s]?800'))
                    page.get_by_role('heading',name='Riferimenti di mercato',exact=True).scroll_into_view_if_needed()
                    screenshot('decision-references')
                    page.set_viewport_size({'width':393,'height':852})
                    page.get_by_role('heading',name='Riferimenti di mercato',exact=True).scroll_into_view_if_needed()
                    screenshot('mobile-decision-references')
                    with page.expect_download() as cross_download:
                        page.get_by_role('link',name='Excel',exact=True).click()
                    cross_download.value.save_as(output / 'decision.xlsx')
                    cross_wb=load_workbook(output/'decision.xlsx',data_only=True)
                    assert cross_wb['Fonti dello stesso asset'].max_row==3
                    page.get_by_role('button',name='Comparabili',exact=True).click()
                    expect(page.locator('.comparable-row')).to_have_count(3)
                    expect(page.locator('.comp-median')).to_contain_text('3 annunci · 3 fonti')
                    expect(page.locator('.comp-median')).to_contain_text(re.compile(r'3[.\s]?400'))
                    expect(page.locator('.comp-comparison')).to_contain_text('14,7% sotto la mediana')
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        page.locator('.comparables-body').evaluate('(el)=>el.scrollTop=0')
                        screenshot(f'comparables-summary-{width}')
                        page.locator('.comp-sample-heading').scroll_into_view_if_needed()
                        screenshot(f'comparables-sample-{width}')
                        box=page.get_by_role('button',name='Chiudi finestra',exact=True).bounding_box()
                        assert box and box['y']>=0 and box['height']>=44
                    page.locator('.comp-method > summary').focus()
                    page.keyboard.press('Enter')
                    expect(page.locator('.comp-method')).to_have_attribute('open','')
                    expect(page.locator('.comp-method')).to_contain_text('Fascia centrale del campione')
                    with page.expect_download() as comparable_download:
                        page.get_by_role('link',name='Excel',exact=True).click()
                    comparable_download.value.save_as(output/'comparables.xlsx')
                    comparable_book=load_workbook(output/'comparables.xlsx',data_only=True)
                    reference=next(r for r in comparable_book['Riferimenti'].iter_rows(min_row=2,values_only=True) if r[1]=='Stesso stato')
                    assert reference[2]==3400 and reference[5]==3
                    sample=[r for r in comparable_book['Comparabili'].iter_rows(min_row=2,values_only=True) if r[1]=='Stesso stato']
                    assert len(sample)==3
                    page.get_by_role('button',name='Torna all’immobile',exact=True).click()
                    expect(page.locator('.drawer-content h1')).to_have_text('QA · Asset da approfondire')
                    page.get_by_role('button',name='Comparabili',exact=True).click()
                    comparable_title=page.locator('.comparable-row .plain-link').first.inner_text()
                    page.locator('.comparable-row .plain-link').first.click()
                    expect(page.locator('.drawer-content h1')).to_have_text(comparable_title)
                    checks.append('Populated comparables show source/date and price delta, match the Excel sample, and navigate to subject and comparable records')
                    checks.append('Comparable summary and sample fit 320/393/768/1440px; method disclosure works from keyboard and close remains visible')
                    close()
                    checks.append('Cross-source discrepancies, three-source reference samples, numeric OMI ranges and enriched Excel on desktop/mobile')
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.locator(f'[data-action="property"][data-id="{subject_id}"]').first.click()
                    page.locator('.cross-source-details > summary').click()
                    page.get_by_role('button',name='Scheda',exact=True).click()
                    page.get_by_role('button',name='Registra contatto',exact=True).click()
                    page.get_by_label('Interlocutore',exact=True).fill('QA · Broker collegato')
                    page.get_by_label('Esito',exact=True).select_option('no_answer')
                    page.get_by_label('Note del contatto',exact=True).fill('Richiesta documenti da preparare per il prossimo contatto.')
                    page.get_by_role('button',name='Salva esito',exact=True).click()
                    page.locator('.cross-source-details > summary').click()
                    page.get_by_role('button',name='Scheda',exact=True).click()
                    expect(page.locator('.related-contact')).to_contain_text('QA · Broker collegato')
                    page.locator('.call-questions > summary').click()
                    expect(page.locator('.call-questions')).to_contain_text('categoria catastale')
                    page.locator('.related-contact').scroll_into_view_if_needed()
                    screenshot('contact-preparation')
                    page.set_viewport_size({'width':393,'height':852})
                    page.locator('.related-contact').scroll_into_view_if_needed()
                    screenshot('mobile-contact-preparation')
                    close()
                    from datetime import datetime,timedelta,timezone
                    old=(datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
                    test_db.execute('UPDATE listing_checks SET last_detail_at=? WHERE property_id IN (?,?)',(old,subject_id,linked_id))
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.get_by_role('link',name='Oggi',exact=True).click()
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    expect(page.locator('.today-missing')).to_contain_text('Disponibilità da ricontrollare')
                    screenshot('stale-before-contact')
                    checks.append('Shared contact visible with source, preparation questions, stale acquisition routed to verification on desktop/mobile')

                    # Layout stress uses only the disposable QA record.
                    long_title='QA · Complesso immobiliare con laboratori e uffici, più corpi di fabbrica e superfici da verificare · '+('riferimento-senza-spazi-'*6)
                    test_db.execute('UPDATE properties SET title=?,price=? WHERE id=?',(long_title,999999999,subject_id))
                    page.locator(f'.today-title[data-id="{subject_id}"]').click()
                    expect(page.locator('#modal-title')).to_have_text(long_title)
                    for width in (320,393,768):
                        page.set_viewport_size({'width':width,'height':852})
                        assert page.locator('.property-drawer').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                    page.set_viewport_size({'width':320,'height':852})
                    screenshot('long-content-mobile')
                    page.locator('.priority-method > summary').press('Enter')
                    expect(page.locator('.priority-method')).to_have_attribute('open','')
                    assert page.locator('.property-drawer').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                    page.keyboard.press('Escape')
                    expect(page.locator('.property-drawer')).to_have_count(0)
                    checks.append('Long title, large price, score disclosure keyboard and Escape work at narrow widths without overflow')


                    # Compare enriched stored dossiers, including a confirmed duplicate.
                    page.set_viewport_size({'width':1440,'height':1080})
                    nav('Opportunità')
                    page.get_by_role('button',name='Azzera',exact=True).click()
                    if page.locator('[data-action="clear-selection"]').is_visible():
                        page.locator('[data-action="clear-selection"]').click()
                    page.locator('#property-search').fill('QA ·')
                    expect(page.locator(f'[data-select-property="{subject_id}"]')).to_be_visible()
                    page.locator(f'[data-select-property="{subject_id}"]').check()
                    page.locator(f'[data-select-property="{linked_id}"]').check()
                    page.get_by_role('button',name='Confronta',exact=True).click()
                    expect(page.locator('.comparison-body')).to_contain_text('Annunci dello stesso asset')
                    expect(page.locator('#compare-panel-decision')).to_contain_text('QA · Broker diretto')
                    expect(page.locator('#compare-panel-decision')).to_contain_text('Da ricontrollare')
                    for width in [320,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        assert page.locator('.comparison-body').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1')
                    page.get_by_role('tab',name='Mercato',exact=True).click()
                    expect(page.locator('#compare-panel-market')).to_contain_text('3 annunci · 3 fonti')
                    expect(page.locator('#compare-panel-market')).to_contain_text('OMI · dati QA')
                    expect(page.locator('#compare-panel-market')).to_contain_text('Superficie lorda')
                    expect(page.locator('#compare-panel-market')).to_contain_text('2800 EUR')
                    page.locator('#compare-panel-market .comparison-method summary').press('Enter')
                    expect(page.locator('#compare-panel-market .comparison-method')).to_have_attribute('open','')
                    screenshot('comparison-enriched-market')
                    page.get_by_role('tab',name='Decisione',exact=True).click()
                    page.locator('#compare-panel-decision .comparison-evidence summary').first.press('Enter')
                    expect(page.locator('#compare-panel-decision .comparison-evidence').first).to_have_attribute('open','')
                    page.locator('#compare-panel-decision thead button').first.click()
                    expect(page.locator('#modal-title')).to_have_text(long_title)
                    close()
                    checks.append('Comparison shows populated reference samples, OMI provenance, stale evidence and same-asset warning; long titles fit and source property opens')


                    # Final isolated fixture: exercise the complete daily queue beyond its old 8/4 cutoffs.
                    from support.today import today_dataset
                    test_db.execute("UPDATE properties SET review_status='discarded'")
                    today_dataset(test_db,test_settings)
                    def refresh_today():
                        previous=page.locator('.today-panel').element_handle()
                        page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                        previous.wait_for_element_state('hidden')
                        expect(page.locator('.today-panel')).to_be_visible()
                    page.set_viewport_size({'width':1440,'height':1080})
                    page.get_by_role('link',name='Oggi',exact=True).click()
                    refresh_today()
                    expect(page.locator('.today-panel>.section-title')).to_contain_text('12 contatti')
                    expect(page.locator('.today-missing>summary')).to_contain_text('6')
                    call_more=page.locator('[data-today-section="call"]')
                    verify_more=page.locator('[data-today-section="verifyMore"]')
                    expect(call_more.locator(':scope > summary')).to_have_text('Mostra altri 7 contatti')
                    expect(verify_more.locator(':scope > summary')).to_have_text('Mostra altri 2 da verificare')
                    # Five contacts at a glance, the rest one click away.
                    expect(page.locator('.today-item:visible')).to_have_count(9)
                    call_more.locator(':scope > summary').focus()
                    page.keyboard.press('Enter')
                    verify_more.locator(':scope > summary').click()
                    expect(page.locator('.today-item:visible')).to_have_count(18)
                    pending_today=[]
                    def hold_today(route):pending_today.append(route)
                    page.route('**/api/operations?*',hold_today)
                    previous=page.locator('.today-panel').element_handle()
                    page.get_by_role('button',name='Aggiorna dati',exact=True).click()
                    reason=call_more.locator('.today-provenance > summary').first
                    reason_id=reason.get_attribute('id')
                    reason.click()
                    expect(reason).to_be_focused()
                    assert len(pending_today)==1
                    pending_today.pop().continue_()
                    previous.wait_for_element_state('hidden')
                    page.unroute('**/api/operations?*',hold_today)
                    expect(page.locator('#'+reason_id)).to_be_focused()
                    expect(page.locator('#'+reason_id).locator('..')).to_have_attribute('open','')
                    refresh_today()
                    expect(call_more).to_have_attribute('open','')
                    expect(verify_more).to_have_attribute('open','')
                    expect(page.locator('.today-missing')).to_contain_text('Recapito da trovare')
                    expect(page.locator('.today-missing a[href^="tel:"]')).to_have_count(0)
                    for width in [320,393,768,1440]:
                        page.set_viewport_size({'width':width,'height':852 if width<700 else 1080})
                        call_more.locator(':scope > summary').scroll_into_view_if_needed()
                        assert call_more.locator(':scope > summary').bounding_box()['height']>=44
                        assert page.locator('.today-panel').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                        page.screenshot(path=str(output/f'today-complete-{width}.png'),full_page=False,animations='disabled')
                    last=call_more.locator('.today-title').last
                    last_title=last.inner_text()
                    last.click()
                    expect(page.locator('#modal-title')).to_have_text(last_title)
                    close()
                    expect(call_more).to_have_attribute('open','')
                    page.locator('.today-missing>summary').click()
                    refresh_today()
                    expect(page.locator('.today-missing')).not_to_have_attribute('open','')
                    checks.append('Daily queue exposes all 12 contacts and 6 verification candidates; keyboard expansion, refreshed disclosure state, linked detail and 320–1440px layouts work')

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
