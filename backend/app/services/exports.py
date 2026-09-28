from __future__ import annotations

import csv
import io
from datetime import datetime,timezone

from ..security import csv_safe

HEADERS=['ID','Titolo','Comune','Micro-zona','Tipologia','Prezzo','Superficie mq','Prezzo/mq',
         'Benchmark min','Benchmark max','Sconto %','Score economico','Completezza %','Motore','Fonte','URL','Rilevato il','Valuta','Disponibilità','Priorità verifica']


def export_csv(rows):
    output=io.StringIO(newline='')
    writer=csv.writer(output,delimiter=';')
    writer.writerow(HEADERS)
    for p in rows:
        b=p.get('benchmark') or {}
        writer.writerow([csv_safe(v) for v in [p['id'],p['title'],p['city'],p['zone'],p['property_type'],p['price'],p['surface'],
            p['price_sqm'],b.get('min_sqm'),b.get('max_sqm'),p['discount'],p['score'],p['completeness'],p['analysis'].get('engine'),
            p.get('source_name',''),p['url'],p['last_seen'],p['currency'],p.get('availability','unknown'),p.get('priority',{}).get('score')]])
    return ('\ufeff'+output.getvalue()).encode('utf-8')


MONEY='#,##0';PCT='0.0';DATE='dd/mm/yyyy'
SELECTION_HEADERS=['ID','Immobile','Comune','Zona','Prezzo richiesto','Valuta','m²','Prezzo/m²',
    'Da ristrutturare /m²','Δ vs Da ristrutturare %','Ristrutturato /m²','Δ vs Ristrutturato %','Nuovo /m²','Δ vs Nuovo %','Campioni (R/Ri/N)',
    'OMI min €/m²','OMI max €/m²','Δ vs OMI medio %','Sconto benchmark %','Giorni sul mercato','Base anzianità','Ribassi osservati','Ribasso totale %',
    'Catasto dichiarato','Cambio d’uso dichiarato','Inserzionista','Telefono','Email','Filiera dichiarata','Evidenza filiera','Mandato (team)','Prossimo contatto',
    'Disponibilità','Fase team','Ricerche nei criteri','Motivi / verifiche','Da chiarire','Campi mancanti',
    'Fonte','URL','Pubblicazione dichiarata','Prima osservazione','Ultima rilevazione','Aggiornamento','Ultima acquisizione dettaglio']
AVAILABILITY={'listed':'Pubblicato','sold':'Venduto','rented':'Affittato','withdrawn':'Ritirato','review':'Da verificare','unknown':'Da verificare'}
STAGES={'new':'Da valutare','reviewing':'In valutazione','shortlisted':'In shortlist','due_diligence':'Due diligence','negotiation':'Negoziazione','acquired':'Acquisito','discarded':'Scartato'}


def day(value):
    """ISO timestamps become Excel dates (UTC day); invalid values stay empty rather than guessed."""
    if not value:return None
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    except ValueError:return None
    if parsed.tzinfo:parsed=parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(hour=0,minute=0,second=0,microsecond=0)


def export_xlsx(rows, db=None):
    """Portable application exporter; no proprietary runtime required on the user's VPS."""
    rows=list(rows)
    if db is not None:
        from .market_references import MarketReferences
        references=MarketReferences(db)
        observations={};calls={};scenarios={}
        for offset in range(0,len(rows),400):
            ids=tuple(p['id'] for p in rows[offset:offset+400])
            marks=','.join('?' for _ in ids)
            for item in db.all('SELECT o.property_id,o.observed_at,o.price,o.content_hash,c.currency,c.transaction_type,v.values_json FROM observations o LEFT JOIN observation_context c ON c.observation_id=o.id LEFT JOIN observation_values v ON v.observation_id=o.id WHERE o.property_id IN ('+marks+') ORDER BY o.observed_at,o.id',ids):
                observations.setdefault(item['property_id'],[]).append(item)
            for item in db.all('SELECT s.*,u.name author FROM scenarios s JOIN users u ON u.id=s.author_id WHERE s.property_id IN ('+marks+') ORDER BY s.created_at,s.id',ids):
                scenarios.setdefault(item['property_id'],[]).append(item)
            for item in db.all('SELECT c.*,u.name author FROM contact_actions c JOIN users u ON u.id=c.user_id WHERE c.property_id IN ('+marks+') ORDER BY c.created_at DESC,c.id DESC',ids):
                calls.setdefault(item['property_id'],[]).append(item)
        from .decision_facts import dossier
        rows=[{**p,'market_references':references.for_property(p),'same_condition_comparables':references.for_property(p,same_condition=True),'cross_sources':references.assets.for_property(p),'observations':observations.get(p['id'],[]),'scenarios':scenarios.get(p['id'],[]),'decision':dossier(p,observations.get(p['id'],[]),calls.get(p['id'],[]))} for p in rows]
        from .signals import attach_signals
        attach_signals(db,rows,references=references,observations=observations)
    if db is not None:
        from .decision_support import DecisionSupport
        support=DecisionSupport(db,[p['id'] for p in rows],references.assets)
        rows=[{**p,'decision_support':support.summarize(p)} for p in rows]
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill,Alignment
    from openpyxl.comments import Comment
    from openpyxl.worksheet.table import Table,TableStyleInfo
    wb=Workbook()
    ws=wb.active;ws.title='Opportunità'
    ws.append(['VEDRA | Annunci e riferimenti di mercato'])
    ws.merge_cells('A1:T1');ws.row_dimensions[1].height=32
    ws['A1'].font=Font(size=14,bold=True,color='173C35')
    ws.append(HEADERS)
    for i,p in enumerate(rows,3):
        b=p.get('benchmark') or {}
        cells=[p['id'],p['title'],p['city'],p['zone'],p['property_type'],p['price'],p['surface'],
              f'=IF(OR(F{i}="",G{i}="",G{i}=0),"",F{i}/G{i})',b.get('min_sqm'),b.get('max_sqm'),
              f'=IF(OR(H{i}="",I{i}="",J{i}=""),"",1-H{i}/AVERAGE(I{i}:J{i}))',p['score'],p['completeness'],
              p['analysis'].get('engine'),p.get('source_name',''),p['url'],p['last_seen'],p['currency'],p.get('availability','unknown'),p.get('priority',{}).get('score')]
        for j,val in enumerate(cells,1):
            if isinstance(val,str) and j not in (8,11):val=csv_safe(val)
            ws.cell(i,j,val)
        for j in (6,8,9,10):ws.cell(i,j).number_format=f'#,##0.00 "{p["currency"] if p["currency"]!="XXX" else "valuta n.d."}"'
        ws.cell(i,7).number_format='#,##0.0'
        ws.cell(i,11).number_format='0.0%'
        ws.cell(i,12).number_format='0" / 100"'
        ws.cell(i,13).number_format='0"%"'
        ws.cell(i,9).comment=Comment(f"Fonte: {b.get('source_label','Nessun benchmark')}\n{b.get('source_url','')}\nPeriodo: {b.get('period','')}\nConfronto sul punto medio, non su un prezzo transato.",'Vedra')
        ws.row_dimensions[i].height=30
    for c in ws[2]:
        c.fill=PatternFill('solid',fgColor='173C35');c.font=Font(color='FFFFFF',bold=True);c.alignment=Alignment(wrap_text=True,vertical='center')
    ws.row_dimensions[2].height=30
    from openpyxl.utils import get_column_letter
    for j in range(1,21):ws.column_dimensions[get_column_letter(j)].width=18
    for col,width in [('A',38),('B',40),('D',23),('O',30),('P',44),('Q',27)]:ws.column_dimensions[col].width=width
    for row in ws.iter_rows(min_row=3):
        for cell in row:cell.alignment=Alignment(vertical='center',wrap_text=True)
    ws.freeze_panes='F3'
    if rows:
        table=Table(displayName='Opportunita',ref=f'A2:T{len(rows)+2}')
        table.tableStyleInfo=TableStyleInfo(name='TableStyleMedium2',showRowStripes=True)
        ws.add_table(table)
    note=wb.create_sheet('Metodo e limiti')
    notes=[['VEDRA | Metodo'],['Scope','Origination e screening preliminare. Nessun rendimento o cambio d’uso certificato.'],
           ['Fonte','Quotazioni OMI acquisite dalla fonte ufficiale; benchmark omogenei importabili.'],
           ['Confronto','Richiede comune, micro-zona, tipo, stato, valuta, contratto e base superficie compatibili.'],
           ['Completezza','Campi presenti / 10 campi attesi. Non è accuratezza, copertura del mercato o probabilità.'],
           ['Score economico','clamp(35 + sconto % × 1,4; 0; 70) + min(30; 15 × strategie con evidenza).'],
           ['Priorità verifica','Dati 30; disponibilità 20 (10 se solo pubblicato); confronto 40 (10 se condizionato); strategie 10. Non è un rendimento.'],
           ['Assenza benchmark','Score economico e delta restano vuoti.'],
           ['Formule','Prezzo/mq e delta si ricalcolano in Excel. Nessun prezzo di uscita o margine inventato.'],
           ['Esportazione',datetime.now(timezone.utc).isoformat(timespec='seconds')]]
    for r in notes:note.append(r)
    note.column_dimensions['A'].width=25;note.column_dimensions['B'].width=95
    for row in note:
        for cell in row:cell.alignment=Alignment(wrap_text=True,vertical='top')
        note.row_dimensions[row[0].row].height=35
    mandate_labels={'not_checked':'Da verificare','declared':'Dichiarato','confirmed_by_team':'Verificato dal team'}
    outcome_labels={'no_answer':'Nessuna risposta','reached':'Interlocutore raggiunto','documents_requested':'Documenti richiesti','not_relevant':'Non pertinente'}
    selection=wb.create_sheet('Selezione',0)
    selection.append(SELECTION_HEADERS)
    references=wb.create_sheet('Riferimenti')
    references.append(['ID immobile','Categoria','Mediana /m²','Min /m²','Max /m²','Campione','Stato / metodo','Valuta','Fonte','URL','Periodo','Fonti','25° percentile /m²','75° percentile /m²','Prima rilevazione nel campione','Ultima rilevazione nel campione','Verifiche','Richiesta / mediana %'])
    evidence=wb.create_sheet('Comparabili')
    evidence.append(['ID immobile','Categoria','ID comparabile','Titolo','Prezzo/m²','m²','Fonte','URL','Osservato il'])
    criteria=wb.create_sheet('Criteri AI')
    criteria.append(['ID immobile','Ricerca','Istruzioni','Esito','Motivazione','Citazioni','Verifica per criterio'])
    contacts=wb.create_sheet('Contatti')
    contacts.append(['ID immobile','Data','Interlocutore','Esito','Mandato (team)','Note','Prossimo contatto','Registrato da','Annuncio contattato'])
    cross_sheet=wb.create_sheet('Fonti dello stesso asset')
    cross_sheet.append(['ID selezionato','ID annuncio','Fonte','URL','Prezzo richiesto','Valuta','m²','Base superficie','Operazione','Disponibilità','Osservato il','Inserzionista','Telefono','Email','Mandato dichiarato','Divergenze da verificare'])
    scenario_sheet=wb.create_sheet('Scenari')
    scenario_sheet.append(['ID immobile','Scenario','Autore','Salvato il','Acquisto EUR','Rivendita EUR','Lavori EUR','Costi acquisto EUR','Imprevisti %','Vendita %','Gestione mensile EUR','Mesi','ROI obiettivo %','Stress ribasso %','Stress lavori %','Stress ritardo mesi','Capitale EUR','Risultato EUR','ROI %','Pareggio EUR','Acquisto massimo EUR','Obiettivo base','Stress risultato EUR','Stress ROI %','Stress acquisto massimo EUR','Obiettivo stress','Modello'])
    history=wb.create_sheet('Storico')
    history.append(['ID immobile','Osservato il','Prezzo richiesto','Valuta','Variazione prezzo','Versione contenuto','Operazione','Variazione % omogenea'])
    for p in rows:
        from ..db import load
        from ..product_schemas import ScenarioInputs
        from .scenarios import calculate
        for scenario in p.get('scenarios',[]):
            inputs=ScenarioInputs.model_validate(load(scenario['inputs']))
            r=calculate(inputs);d=inputs.model_dump()
            vals=[p['id'],scenario['name'],scenario['author'],scenario['created_at'],*[d[key] for key in ('purchase','sale','works','acquisition_costs','contingency_pct','selling_pct','holding_monthly','months','target_roi_pct','stress_sale_pct','stress_works_pct','stress_delay_months')],r['invested'],r['profit'],r['roi_pct'],r['breakeven_sale'],r['max_purchase'],'Sì' if r['target_met'] else 'No',r['stress']['profit'],r['stress']['roi_pct'],r['stress']['max_purchase'],'Sì' if r['stress']['target_met'] else 'No',r['version']]
            scenario_sheet.append([csv_safe(v) if isinstance(v,str) else v for v in vals])
        from .history import observed_price_change
        from ..db import load
        previous=None;previous_fields=None
        for observation in p.get('observations',[]):
            price=observation['price'];currency=observation.get('currency');transaction=observation.get('transaction_type')
            context=(currency,transaction)
            comparable=currency not in (None,'XXX') and transaction in ('sale','rent')
            delta=price-previous[0] if previous and comparable and previous[1]==context and price is not None and previous[0] is not None else None
            fields=load(observation.get('values_json'))
            pct=observed_price_change(previous_fields,fields)
            previous_fields=fields
            history.append([csv_safe(v) if isinstance(v,str) else v for v in [p['id'],observation['observed_at'],price,currency,delta,observation['content_hash'],transaction,pct]])
            previous=(price,context)
        cross=p.get('cross_sources',{})
        if cross.get('count',0)>1:
            for entry in cross['entries']:
                contact=entry['contact']
                cross_sheet.append([csv_safe(v) if isinstance(v,str) else v for v in [p['id'],entry['id'],entry['source'],entry['url'],entry['price'],entry['currency'],entry['surface'],entry['area_basis'],entry['transaction_type'],entry['availability'],entry['last_seen'],contact.get('name') or contact.get('organization'),contact.get('telephone'),contact.get('email'),entry['mandate'],'; '.join(cross['conflicts'])]])
        matches=p.get('search_matches') or p.get('screenings') or []
        reasons=[r for m in matches for r in m.get('reasons',m.get('fit_reasons',[]))]+cross.get('conflicts',[])
        if not p.get('benchmark'):reasons.append('Benchmark compatibile assente')
        refs=p.get('market_references',{})
        groups={r['key']:r for r in refs.get('groups',[])}
        signals=p.get('signals',{});signal_market=signals.get('market',{});signal_refs={r['key']:r for r in signal_market.get('refs',[])};omi=signal_market.get('omi') or {};reductions=signals.get('reductions',{})
        basis={'published':'Pubblicazione dichiarata','first_seen':'Prima rilevazione'}.get(signals.get('listed_basis'))
        samples='/'.join(str(signal_refs.get(k,{}).get('count',0)) for k in ('to_renovate','renovated','new'))
        decision=p.get('decision',{});contact=decision.get('contact') or {};last=decision.get('calls',[None])[0] if decision.get('calls') else {}
        support=p.get('decision_support',{});age=support.get('freshness',{});route=decision.get('contact_route',{})
        delta=lambda key:signal_refs.get(key,{}).get('delta_pct')
        # Decision columns first, in the order the analyst reads them: price, the four references, age, declarations, contact.
        columns=[('ID',p['id'],None),('Immobile',p['title'],None),('Comune',p['city'],None),('Zona',p['zone'],None),
            ('Prezzo richiesto',p['price'],MONEY),('Valuta',p['currency'],None),('m²',p['surface'],MONEY),('Prezzo/m²',p['price_sqm'],MONEY),
            ('Da ristrutturare /m²',groups.get('to_renovate',{}).get('median_sqm'),MONEY),('Δ vs Da ristrutturare %',delta('to_renovate'),PCT),
            ('Ristrutturato /m²',groups.get('renovated',{}).get('median_sqm'),MONEY),('Δ vs Ristrutturato %',delta('renovated'),PCT),
            ('Nuovo /m²',groups.get('new',{}).get('median_sqm'),MONEY),('Δ vs Nuovo %',delta('new'),PCT),('Campioni (R/Ri/N)',samples,None),
            ('OMI min €/m²',omi.get('min_sqm'),MONEY),('OMI max €/m²',omi.get('max_sqm'),MONEY),('Δ vs OMI medio %',omi.get('delta_pct'),PCT),
            ('Sconto benchmark %',p.get('discount'),PCT),
            ('Giorni sul mercato',signals.get('days_listed'),None),('Base anzianità',basis,None),('Ribassi osservati',reductions.get('count'),None),('Ribasso totale %',reductions.get('total_pct'),PCT),
            ('Catasto dichiarato',decision.get('cadastral',{}).get('quote'),None),('Cambio d’uso dichiarato',decision.get('change_of_use',{}).get('quote'),None),
            ('Inserzionista',contact.get('name') or contact.get('organization'),None),('Telefono',contact.get('telephone'),None),('Email',contact.get('email'),None),
            ('Filiera dichiarata',route.get('label'),None),('Evidenza filiera',route.get('quote'),None),('Mandato (team)',mandate_labels.get(last.get('mandate_status')),None),('Prossimo contatto',day(last.get('next_contact')),DATE),
            ('Disponibilità',AVAILABILITY.get(p.get('availability'),'Da verificare'),None),('Fase team',STAGES.get(p.get('review_status'),p.get('review_status')),None),
            ('Ricerche nei criteri','; '.join(m['name'] for m in matches if m['fit']),None),('Motivi / verifiche','; '.join(dict.fromkeys(reasons)),None),
            ('Da chiarire','\n'.join(support.get('questions',[])),None),('Campi mancanti',', '.join(p.get('missing_fields',[])),None),
            ('Fonte',p.get('source_name',''),None),('URL',p['url'],None),('Pubblicazione dichiarata',day(decision.get('published_at')),DATE),
            ('Prima osservazione',day(p.get('first_seen')),DATE),('Ultima rilevazione',day(p['last_seen']),DATE),
            ('Aggiornamento',age.get('label'),None),('Ultima acquisizione dettaglio',day(age.get('checked_at')),DATE)]
        assert [header for header,_,_ in columns]==SELECTION_HEADERS
        values=[value for _,value,_ in columns]
        shared=[support['related_contact']] if support.get('related_contact') else []
        for item in [*decision.get('calls',[]),*shared]:
            contacts.append([csv_safe(v) if isinstance(v,str) else v for v in [p['id'],item['created_at'],item['contact_name'],outcome_labels[item['outcome']],mandate_labels[item['mandate_status']],item['note'],item['next_contact'],item['author'],item.get('property_id',p['id'])]])
        selection.append([csv_safe(v) if isinstance(v,str) else v for v in values])
        for index,(_,_,fmt) in enumerate(columns,1):
            if fmt:selection.cell(row=selection.max_row,column=index).number_format=fmt
        for group in [*refs.get('groups',[]),*p.get('same_condition_comparables',{}).get('groups',[])]:
            references.append([p['id'],group['label'],group['median_sqm'],group['min_sqm'],group['max_sqm'],group['count'],csv_safe(group['reason']),p['currency'],'Annunci in archivio',None,'Ultimi 90 giorni',group.get('source_count'),group.get('q1_sqm'),group.get('q3_sqm'),group.get('oldest_observed'),group.get('newest_observed'),'; '.join(group.get('warnings',[])),group.get('asking_delta_pct')])
            for item in group['items']:
                evidence.append([csv_safe(v) if isinstance(v,str) else v for v in [p['id'],group['label'],item['id'],item['title'],item['price_sqm'],item['surface'],item['source'],item['url'],item['observed_at']]])
        omi=refs.get('omi') or p.get('market_context') or {}
        if omi.get('status')=='available' and not omi.get('stale'):
            for item in omi.get('rows',[]):
                references.append([p['id'],'OMI · '+str(item.get('type',''))+' · '+str(item.get('condition','')),None,item.get('min_sqm'),item.get('max_sqm'),None,csv_safe('Periodo '+str(omi.get('period',''))+' · riferimento condizionato, base '+str(item.get('area_basis',''))),'EUR',csv_safe(omi.get('source_label','')),csv_safe(omi.get('source_url','')),csv_safe(omi.get('period',''))])
        else:references.append([p['id'],'OMI',None,None,None,None,csv_safe(omi.get('reason') or 'Riferimento assente o non aggiornato'),'EUR',csv_safe(omi.get('source_label','')),csv_safe(omi.get('source_url','')),csv_safe(omi.get('period',''))])
        from .analysis import custom_assessment
        for match in matches:
            prompt=match.get('custom_prompt','')
            if not prompt:continue
            assessment=custom_assessment(p,prompt)
            status={'matched':'Coerente','not_matched':'Non coerente','uncertain':'Da verificare'}.get(assessment['status'],'Da verificare') if assessment else 'Da analizzare'
            criteria.append([csv_safe(v) for v in [p['id'],match['name'],prompt,status,assessment['reason'] if assessment else 'Esegui la ricerca con i criteri aggiornati',' | '.join(assessment['evidence']) if assessment else '', '\n'.join(c['criterion']+': '+{'matched':'Coerente','not_matched':'Non coerente','uncertain':'Da verificare'}[c['status']]+' · '+c['reason']+' · '+ ' | '.join(c['evidence']) for c in assessment.get('checks',[])) if assessment else '']])
    for sheet in (selection,references,evidence,criteria,history,contacts,cross_sheet,scenario_sheet):
        sheet.freeze_panes='C2';sheet.auto_filter.ref=sheet.dimensions
        sheet.row_dimensions[1].height=34
        for cell in sheet[1]:
            cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='173C35');cell.alignment=Alignment(wrap_text=True)
        for column in range(1,sheet.max_column+1):sheet.column_dimensions[get_column_letter(column)].width=24
        for row in sheet.iter_rows(min_row=2):
            for cell in row:cell.alignment=Alignment(wrap_text=True,vertical='top')
        sheet.sheet_view.showGridLines=False
    selection.column_dimensions['B'].width=45
    for index,cell in enumerate(selection[1],1):
        if cell.value in ('Motivi / verifiche','Da chiarire','Cambio d’uso dichiarato','Evidenza filiera','URL'):selection.column_dimensions[get_column_letter(index)].width=45
    note.append(['Stesso stato','Confronto omogeneo della finestra Comparabili, riportato in Riferimenti e Comparabili. Stessi metadati e servizio della piattaforma; il campione può coincidere con una delle tre categorie di mercato.'])
    note.append(['Quattro riferimenti','Prezzi richiesti da ristrutturare/ristrutturati/nuovi separati. Mediana da 3 asset compatibili; OMI distinto e condizionato. Buono non equivale a ristrutturato.'])
    note.append(['Anzianità','Data di pubblicazione dichiarata e valida quando disponibile, altrimenti prima osservazione di Vedra. Storico limitato alle osservazioni raccolte. Prezzi mancanti, cambio di valuta o di operazione interrompono il confronto.'])
    note.append(['Variazione storica %','Stesso calcolo della cronologia: prezzi positivi, valuta, operazione, superficie e base superficie invariate e conservate. Non misura lo sconto di mercato.'])
    note.append(['Unità','I valori per m² degli annunci usano la valuta dell’immobile, riportata in Selezione. OMI è sempre in EUR. I campioni visibili mostrano al massimo 12 asset per categoria; statistiche fino a 1.000 annunci per zona.'])
    note.append(['Fonti dello stesso asset','Solo collegamenti confermati dal team. Le divergenze richiedono verifica; nessun prezzo viene scelto come vero.'])
    note.append(['Scenari','Istantanea degli scenari salvati: stessi input e calcolatore della piattaforma. Nessuna simulazione probabilistica. Costi di acquisto fissi, debito e imposte non inserite esclusi. Un acquisto massimo negativo indica che nessun prezzo positivo soddisfa il ROI.'])
    note.append(['Campione','Quartili interpolati dei prezzi richiesti. Numero fonti e dispersione descrivono i dati, non accuratezza o indipendenza.'])
    legacy_sheet='xl/worksheets/sheet'+str(wb.worksheets.index(ws)+1)+'.xml'
    # Excel recalculates on opening. Also populate the two deterministic caches so
    # read-only viewers do not display empty values before their first recalculation.
    wb.calculation.fullCalcOnLoad=True
    wb.calculation.calcMode='auto'
    out=io.BytesIO();wb.save(out)
    import zipfile
    from xml.etree import ElementTree as ET
    namespace={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    patched=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(out.getvalue())) as source,zipfile.ZipFile(patched,'w',zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            content=source.read(item.filename)
            if item.filename==legacy_sheet:
                tree=ET.fromstring(content)
                cells={cell.get('r'):cell for cell in tree.findall('.//s:c',namespace)}
                for i,p in enumerate(rows,3):
                    amount=p['price']/p['surface'] if p['price'] and p['surface'] else None
                    b=p.get('benchmark')
                    delta=1-amount/((b['min_sqm']+b['max_sqm'])/2) if b and amount is not None else None
                    for address,value in ((f'H{i}',amount),(f'K{i}',delta)):
                        cell=cells[address]
                        cached=cell.find('s:v',namespace)
                        if cached is None:cached=ET.SubElement(cell,'{'+namespace['s']+'}v')
                        cached.text=str(value) if value is not None else ''
                        cell.set('t','n' if value is not None else 'str')
                content=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
            target.writestr(item,content)
    return patched.getvalue()


def export_docx(p):
    from docx import Document
    from docx.shared import Inches,Pt,RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=Inches(.7);sec.bottom_margin=Inches(.65);sec.left_margin=Inches(.8);sec.right_margin=Inches(.8)
    normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10)
    normal.paragraph_format.space_after=Pt(6)
    doc.core_properties.title=f"Vedra · {p['title']}";doc.core_properties.author='Vedra'
    sec.header.paragraphs[0].text='VEDRA  /  REAL ESTATE INTELLIGENCE'
    doc.add_heading('Scheda di screening',0)
    doc.add_paragraph('DOCUMENTO PRELIMINARE · VERIFICA UMANA RICHIESTA','Subtitle')
    doc.add_heading(p['title'],1)
    doc.add_paragraph(f"{p['city']} · {p['zone'] or 'Micro-zona non disponibile'}\nID: {p['id']}")
    def euro(v):return (f'{v:,.0f}'.replace(',','.')+' '+('€' if p['currency']=='EUR' else p['currency'] if p['currency']!='XXX' else '(valuta n.d.)')) if v is not None else 'Non disponibile'
    table=doc.add_table(rows=0,cols=2);table.style='Light Shading Accent 1'
    for k,v in [('Prezzo richiesto',euro(p['price'])),('Superficie',f"{p['surface']} mq" if p['surface'] else 'Non disponibile'),
                ('Prezzo / mq',euro(p['price_sqm'])),('Priorità di verifica',str(p.get('priority',{}).get('score',0))+'/100'),('Disponibilità',p.get('availability','unknown')),
                ('Completezza campi',f"{p['completeness']}% (non misura l’accuratezza)"),('Tipologia / stato',f"{p['property_type']} / {p['condition']}")]:
        row=table.add_row();row.cells[0].text=k;row.cells[1].text=v
    doc.add_heading('Strategie ed evidenze',2)
    strategies=p['analysis'].get('strategies',[])
    if not strategies:doc.add_paragraph('Nessuna strategia supportata dal testo acquisito.')
    for s in strategies:
        doc.add_paragraph(s['strategy'].replace('_',' ').title(),'Heading 3')
        doc.add_paragraph('Evidenza dal testo: “'+s['evidence']+'”')
    b=p.get('benchmark')
    doc.add_heading('Confronto di prezzo',2)
    if b and p.get('discount') is not None:
        doc.add_paragraph(f"Range: {euro(b['min_sqm'])} – {euro(b['max_sqm'])} / mq. Periodo {b['period']}.\nScostamento del prezzo dal punto medio: {-p['discount']}% (negativo = sotto il riferimento). Non è una stima del prezzo transato.")
        doc.add_paragraph(f"Fonte benchmark: {b['source_label']}\n{b['source_url']}")
    else:doc.add_paragraph(p['analysis'].get('benchmark_note','Nessun benchmark compatibile.'))
    doc.add_heading('Fonti e limiti',2)
    doc.add_paragraph(f"Annuncio: {p['url']}\nAcquisito: {p['last_seen']}\nMotore classificazione: {p['analysis'].get('engine','non disponibile')}")
    doc.add_paragraph('Campi assenti: '+(', '.join(p['missing_fields']) or 'nessuno tra quelli misurati'))
    for text in p['analysis'].get('caveats',[]):doc.add_paragraph(text)
    doc.add_paragraph('Questo documento non costituisce una perizia o una raccomandazione d’investimento. Destinazione d’uso, urbanistica, stato locativo, costi e diritti sui dati devono essere verificati prima di ogni decisione.')
    footer=sec.footer.paragraphs[0];footer.text='VEDRA  |  '
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
    out=io.BytesIO();doc.save(out);return out.getvalue()
