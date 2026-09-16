import {icon} from './icons.js';
import {e, num, euro, amount, relative, stamp, label, reviewLabel, score, discount, strategyTags, selectOptions, activeRun} from './utils.js';
import {action, badge, empty, notice, pageHeading} from './ui.js';
import {mapPanel} from './map.js';

export const stages = ['new','reviewing','shortlisted','due_diligence','negotiation','acquired','discarded'];
const checks = [
  ['source_checked','Annuncio e fonte verificati'],
  ['area_checked','Superficie e stato confrontabili'],
  ['occupancy_checked','Occupazione e disponibilità verificate'],
  ['planning_checked','Verifica urbanistica professionale'],
  ['costs_checked','Costi e ipotesi economiche verificati'],
];
const workFor = (s,id) => s.ops?.work?.find(w=>w.property_id===id);
const teamName = (s,id) => s.ops?.team?.find(u=>u.id===id)?.name || 'Non assegnato';
const isLate = w => w?.due_date && w.due_date < new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10);
const compactProperty = p => `<button class="rank-property" data-action="property" data-id="${e(p.id)}"><span class="rank-icon">${icon('building')}</span><span class="rank-text"><strong>${e(p.city || 'Comune n.d.')} · ${e(p.zone || label(p.property_type))}</strong><span>${num(p.surface)} m² · ${amount(p.price_sqm,p.currency)}/m²</span></span><span class="rank-result">${score(p)}${discount(p)}</span></button>`;

function metric(title,value,detail,glyph) {
  return `<article class="metric-card"><div class="metric-label"><span>${title}</span><span class="metric-icon">${icon(glyph)}</span></div><div class="metric-value">${value}</div><div class="metric-detail">${detail}</div></article>`;
}

export function pipelineView(s) {
  const query=(s.pipelineQuery||'').toLocaleLowerCase();
  const items=s.data.properties.filter(p=>`${p.title} ${p.city} ${teamName(s,workFor(s,p.id)?.owner_id)}`.toLocaleLowerCase().includes(query));
  return `${pageHeading('DEAL MANAGEMENT','Pipeline','Assegna le verifiche, registra le decisioni e conserva le evidenze.','<a href="#properties" class="btn">Tutte le opportunità</a>')}
    <div class="pipeline-toolbar"><div class="search-input">${icon('search')}<input id="pipeline-search" type="search" value="${e(s.pipelineQuery||'')}" placeholder="Cerca per immobile, comune o responsabile" aria-label="Cerca nella pipeline"></div><span class="muted small">${num(items.length)} immobili · Le modifiche sono condivise con il team</span></div><div class="pipeline-board">${stages.map(stage=>{
      const rows=items.filter(p=>p.review_status===stage);
      return `<section class="pipeline-column stage-${stage}"><header><span>${reviewLabel(stage)}</span><strong>${rows.length}</strong></header><div>${rows.map(p=>{
        const work=workFor(s,p.id), done=Object.values(work?.checklist||{}).filter(Boolean).length;
        return `<article class="deal-card"><div class="deal-card-heading"><span>${e(p.city||'Comune n.d.')}</span>${score(p)}</div><button class="deal-card-title" data-action="property" data-id="${e(p.id)}">${e(p.title)}</button><strong class="deal-card-price">${amount(p.price,p.currency)} <small>· ${num(p.surface)} m²</small></strong><div class="strategy-group">${strategyTags(p,1)}</div><div class="deal-card-work"><span>${icon('user')}${e(teamName(s,work?.owner_id))}</span>${work?.due_date?`<span class="${isLate(work)&&!['acquired','discarded'].includes(stage)?'danger-text':''}">${icon('calendar')}${e(work.due_date)}</span>`:''}<span>${icon('check')}${done} / ${checks.length} verifiche</span></div>${action('deal-work',s.user.role==='viewer'?'Dettagli revisione':'Gestisci revisione','edit','btn small-btn full',`data-id="${e(p.id)}"`)}</article>`;
      }).join('')||'<div class="column-empty">Nessun immobile</div>'}</div></section>`;
    }).join('')}</div>`;
}

export function inboxView(s) {
  const items=(s.notifications||[]).filter(n=>!s.inboxUnread||!n.read_at);
  return `${pageHeading('NOTIFICHE','Inbox','Eventi persistenti del workspace. Letto e non letto sono personali.',action('read-all','Segna tutte come lette','check','btn'))}
    <div class="inbox-toolbar"><div class="segmented"><button data-action="inbox-filter" data-unread="false" class="${!s.inboxUnread?'active':''}">Tutte</button><button data-action="inbox-filter" data-unread="true" class="${s.inboxUnread?'active':''}">Non lette · ${num(s.ops?.unread||0)}</button></div><span class="small muted">${s.ops?.mail?.enabled?'Invio email attivo sui dati reali':'Email non attive · gli eventi restano in questa inbox'}</span></div><section class="panel inbox-list">${items.map(n=>`<article class="inbox-item ${n.read_at?'read':''}"><span class="inbox-dot"></span><span class="inbox-icon">${icon(n.kind==='price_change'?'chart':n.kind==='source_blocked'?'warning':'bell')}</span><button data-action="notification-open" data-id="${e(n.id)}"><strong>${e(n.title)} </strong><p>${e(n.body)}</p><small>${stamp(n.created_at,true)}</small></button>${n.read_at?'<span class="read-check" title="Letta">'+icon('check')+'</span>':action('notification-read','','check','icon-button',`data-id="${e(n.id)}" aria-label="Segna come letta"`)}</article>`).join('')||empty('Tutto in ordine','Nessuna notifica in questa vista. Non vengono creati eventi fittizi.')}</section><p class="small muted page-note">Ultimi 200 eventi. Le notifiche email, quando configurate, vengono inviate solo per eventi reali; i tentativi sono persistenti e limitati.</p>`;
}

export function marketView(s) {
  const rows=s.benchmarks||[];
  const available=s.data.stats.benchmarked;
  return `${pageHeading('RIFERIMENTI','Mercato e benchmark','Riferimenti importati e confronti omogenei, separati dai prezzi richiesti degli annunci.',s.user.role==='admin'?action('import','Importa benchmark','upload','btn primary'):'')}
    <div class="market-summary"><section class="panel"><span>Benchmark nel dataset</span><strong>${num(rows.length)}</strong></section><section class="panel"><span>Immobili confrontabili</span><strong>${num(available)} <small>/ ${num(s.data.stats.properties)}</small></strong></section><section class="panel"><span>Confronto utilizzato</span><strong class="text-stat">Zona · tipo · stato</strong><p>Stessa base di superficie, valuta e operazione</p></section></div>
    ${notice('OMI non viene scaricato automaticamente. Importa dati utilizzabili dal cliente e cita fonte e periodo. I prezzi richiesti degli annunci non sono prezzi di transazione.')}
    <section class="panel">${rows.length?`<div class="table-scroll"><table class="benchmark-table"><thead><tr><th>COMUNE / ZONA</th><th>TIPO / STATO</th><th>BASE</th><th>RANGE €/M²</th><th>PERIODO</th><th>FONTE</th></tr></thead><tbody>${rows.map(b=>`<tr><td><strong>${e(b.city)}</strong><small>${e(b.zone)}</small></td><td>${e(label(b.property_type))}<small>${e(label(b.condition))}</small></td><td>${e(b.area_basis==='commercial'?'Commerciale':label(b.area_basis))}<small>${e(label(b.transaction_type))}</small></td><td class="numeric">${euro(b.min_sqm)} – ${euro(b.max_sqm)}</td><td>${e(b.period)}</td><td>${e(b.source_label)}</td></tr>`).join('')}</tbody></table></div>`:empty('Nessun benchmark importato','L’assenza di un riferimento non impedisce la raccolta. Score e scostamento restano non disponibili.')}</section>
    <div class="market-method panel"><h2>Comparabili dal tuo archivio</h2><p>Apri un immobile e scegli <strong>Comparabili</strong>: il confronto usa gli annunci osservati negli ultimi 90 giorni con stessi metadati e superficie ±30%. La mediana compare solo con almeno tre comparabili. Gli asset confermati come duplicati non vengono contati due volte.</p><span class="quiet-pill">Prezzi richiesti · non una valutazione</span></div>`;
}

export function savedViewBar(s) {
  const rows=s.ops?.saved_views||[];
  return `<div class="saved-views"><span>${icon('filter')} Viste personali</span>${rows.map(v=>`<div class="saved-view"><button data-action="apply-view" data-id="${e(v.id)}">${e(v.name)}</button><button data-action="delete-view" data-id="${e(v.id)}" aria-label="Elimina vista ${e(v.name)}">${icon('close')}</button></div>`).join('')}${action('save-view','Salva filtri','plus','text-button')}</div>`;
}

export function workForm(s,p,w) {
  const readonly=s.user.role==='viewer';
  return `<form id="work-form" class="modal-form" data-id="${e(p.id)}" data-version="${w.version}"><fieldset ${readonly?'disabled':''}><div class="form-grid"><label>Fase<select name="stage">${selectOptions(stages.map(x=>[x,reviewLabel(x)]),p.review_status)}</select></label><label>Responsabile<select name="owner_id">${selectOptions([['','Non assegnato'],...(s.ops?.team||[]).filter(u=>u.role!=='viewer').map(u=>[u.id,u.name])],w.owner_id||'')}</select></label><label>Scadenza revisione<input type="date" name="due_date" value="${e(w.due_date||'')}"></label><div class="field-note">Questa data riguarda il team, non la disponibilità o la scadenza legale dell’immobile.</div></div><div class="review-checklist"><h3>Controlli umani</h3>${checks.map(([key,text])=>`<label><input type="checkbox" name="${key}" ${w.checklist?.[key]?'checked':''}>${text}</label>`).join('')}</div><p class="small muted">Le verifiche non vengono spuntate dall’AI. In caso di modifiche simultanee il salvataggio viene fermato per evitare sovrascritture.</p><div class="form-error" id="modal-error" role="alert"></div>${readonly?'':`<div class="modal-form-footer"><button class="btn" type="button" data-action="property" data-id="${e(p.id)}">Scheda immobile</button><button type="submit" class="btn primary">Salva revisione ${icon('check')}</button></div>`}</fieldset></form>`;
}

export function scenarioForm(s,p,scenarios) {
  const editable=s.user.role!=='viewer';
  return `<div class="modal-body"><div class="scenario-context"><span>${e(p.city)} · ${num(p.surface)} m²</span><strong>Prezzo richiesto ${amount(p.price,p.currency)}</strong></div>${notice('Inserisci le tue ipotesi. Questo modello non stima il prezzo di rivendita e non verifica la fattibilità. Calcoli senza debito, prima delle imposte non incluse nei costi.')}<form id="scenario-form" data-id="${e(p.id)}"><div class="form-grid"><label class="span-2">Nome scenario<input name="name" value="Scenario base" maxlength="80" required></label>${[
    ['purchase','Prezzo di acquisto (€)',p.price||'',1,1e9],['sale','Rivendita ipotizzata (€)','',1,1e10],['works','Lavori (€)',0,0,1e9],['acquisition_costs','Costi di acquisto e imposte (€)',0,0,1e9],['contingency_pct','Imprevisti sui lavori (%)',10,0,100],['selling_pct','Costi di vendita (%)',3,0,99.99],['holding_monthly','Gestione mensile (€)',0,0,1e7],['months','Durata (mesi)',12,1,120],
  ].map(([key,text,val,min,max])=>`<label>${text}<input name="${key}" type="number" min="${min}" max="${max}" step="${key==='months'?'1':'0.01'}" value="${val}" required></label>`).join('')}</div><div class="form-error" id="modal-error" role="alert"></div><div class="modal-form-footer"><button type="submit" class="btn">${icon('calculator')} Calcola</button>${editable?'<button type="submit" name="save" value="true" class="btn primary">Salva scenario</button>':''}</div></form><div id="scenario-result" aria-live="polite"></div><section class="saved-scenarios"><h3>Scenari salvati</h3>${scenarios.length?scenarios.map(row=>`<div><span><strong>${e(row.name)}</strong><small>${e(row.author)} · ${stamp(row.created_at)}</small></span><span class="${row.result.profit<0?'danger-text':''}">${euro(row.result.profit)}<small>Risultato ante imposte escluse</small></span>${action('load-scenario','Apri','','btn small-btn',`data-id="${e(row.id)}"`)}${editable&&(s.user.role==='admin'||s.user.id===row.author_id)?action('delete-scenario','','close','icon-button',`data-id="${e(row.id)}" aria-label="Elimina scenario ${e(row.name)}"`):''}</div>`).join(''):'<p class="muted small">Nessuno scenario salvato per questo immobile.</p>'}</section></div>`;
}

export function scenarioResult(r) {
  return `<div class="scenario-output"><div class="scenario-kpis"><div><span>Capitale impiegato</span><strong>${euro(r.invested)}</strong></div><div><span>Risultato operazione</span><strong class="${r.profit<0?'danger-text':''}">${euro(r.profit)}</strong></div><div><span>ROI semplice</span><strong>${num(r.roi_pct,2)}%</strong></div><div><span>Rivendita di pareggio</span><strong>${euro(r.breakeven_sale)}</strong></div></div><p class="small muted">Non è un rendimento annualizzato. Imposte aggiuntive, finanziamento e flussi intermedi sono esclusi.</p><h3>Sensibilità del risultato</h3><div class="table-scroll"><table><thead><tr><th>RIVENDITA</th><th>LAVORI BASE</th><th>LAVORI +20%</th></tr></thead><tbody>${[-10,0,10].map(shift=>`<tr><th>${shift>0?'+':''}${shift}%</th>${[0,20].map(w=>{const value=r.sensitivity.find(x=>x.sale_change_pct===shift&&x.works_change_pct===w)?.profit;return `<td class="${value<0?'danger-text':''}">${euro(value)}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div></div>`;
}

export function comparablesContent(p,result) {
  return `<div class="modal-body">${notice(e(result.reason))}<div class="comp-subject"><strong>${e(p.title)}</strong><span>${amount(p.price_sqm,p.currency)} / m² richiesti · ${num(p.surface)} m²</span></div><div class="comp-median"><span>Mediana dei comparabili</span><strong>${result.median_sqm==null?'Non disponibile':amount(result.median_sqm,p.currency)+' / m²'}</strong><small>${result.items.length} annunci confrontabili</small></div>${result.items.length?`<div class="comparable-list">${result.items.map(row=>`<button data-action="property" data-id="${e(row.id)}"><span><strong>${e(row.title)}</strong><small>${num(row.surface)} m² · ${relative(row.last_seen)}</small></span><strong>${amount(row.price_sqm,p.currency)} / m²</strong>${icon('arrow')}</button>`).join('')}</div>`:empty('Nessun comparabile omogeneo','Acquisisci altri annunci o verifica i metadati, senza allargare arbitrariamente il confronto.')}</div>`;
}

export function propertyTools(s,p) {
  return `<div class="property-tools">${action('deal-work','Revisione','board','btn',`data-id="${e(p.id)}"`)}${action('comparables','Comparabili','compare','btn',`data-id="${e(p.id)}"`)}${action('scenarios','Scenario economico','calculator','btn',`data-id="${e(p.id)}" ${p.currency==='EUR'?'':'disabled title="Richiede valuta EUR verificata"'}`)}</div>`;
}

export function duplicateControls(s,pair) {
  const [a,b]=[pair.a,pair.b].sort();
  const reviewed=s.ops?.duplicate_reviews?.find(r=>r.a===a&&r.b===b);
  if(s.user.role==='viewer') return reviewed?badge(reviewed.decision==='same_asset'?'Stesso asset':'Distinti'):'';
  return `<div class="duplicate-controls">${reviewed?`<span class="quiet-pill">${reviewed.decision==='same_asset'?'Stesso asset confermato':'Annunci distinti'}</span>`:''}${action('duplicate-review','Stesso asset','','btn small-btn',`data-a="${e(a)}" data-b="${e(b)}" data-decision="same_asset"`)}${action('duplicate-review','Distinti','','btn small-btn',`data-a="${e(a)}" data-b="${e(b)}" data-decision="distinct"`)}</div>`;
}

export function operationsSettings(s) {
  const ops=s.ops||{}, worker=ops.worker||{};
  return `<section class="panel settings-panel full-settings"><div class="section-heading"><div><h2>Stato operativo</h2><p>${e(ops.workspace?.name||'Workspace')} · istanza dedicata</p></div>${s.user.role==='admin'?action('readiness','Verifica sistema','pulse','btn'):''}</div><dl class="settings-facts"><div><dt>Ultimo heartbeat del worker</dt><dd>${worker.last_tick?relative(worker.last_tick):'Non rilevato'}</dd></div><div><dt>Budget per esecuzione</dt><dd>${num((ops.limits?.run_timeout_seconds||0)/60)} minuti</dd></div><div><dt>Analisi AI per run</dt><dd>Massimo ${num(ops.limits?.max_ai_listings)}</dd></div><div><dt>Email</dt><dd>${ops.mail?.enabled?'Attive':'Non configurate'} · ${ops.mail?.pending||0} in attesa · ${ops.mail?.failed||0} fallite</dd></div></dl><div class="usage-summary"><h3>Consumi AI registrati</h3><p>${num(ops.ai_usage?.accepted_analyses||0)} analisi accettate · ${num(ops.ai_usage?.input_tokens)} token input · ${num(ops.ai_usage?.output_tokens)} token output</p><p>${ops.ai_usage?.estimated_eur==null?"Costo non calcolabile senza usage e tariffe configurate":"Stima delle risposte accettate: € "+num(ops.ai_usage.estimated_eur,4)}</p><small>Non è una fattura: tentativi falliti o output rifiutati possono essere addebitati dal provider e non sono inclusi.</small></div><div id="readiness-result"></div><div class="settings-security-actions">${action('password','Cambia password','lock','btn')}${s.user.role==='admin'?action('audit','Registro modifiche','document','btn'):''}<a href="/api/docs" class="btn" target="_blank" rel="noopener">API reference ${icon('upRight')}</a></div><p class="small muted">Ogni cliente ha database, segreti e profilo Hermes separati. Questa release non offre registrazione pubblica, fatturazione o un database multi-tenant condiviso.</p></section>`;
}
