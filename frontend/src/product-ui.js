import {icon} from './icons.js';
import {e, num, euro, amount, relative, stamp, label, reviewLabel, score, discount, strategyTags, selectOptions, activeRun, availabilityTag} from './utils.js';
import {action, badge, empty, notice, pageHeading} from './ui.js';
import {mapPanel} from './map.js';

export {stages,pipelineView,workForm} from './pipeline-ui.js';
const compactProperty = p => `<button class="rank-property" data-action="property" data-id="${e(p.id)}"><span class="rank-icon">${icon('building')}</span><span class="rank-text"><strong>${e(p.city || 'Comune n.d.')} · ${e(p.zone || label(p.property_type))}</strong><span>${num(p.surface)} m² · ${amount(p.price_sqm,p.currency)}/m²</span></span><span class="rank-result">${score(p)}${discount(p)}</span></button>`;

function metric(title,value,detail,glyph) {
  return `<article class="metric-card"><div class="metric-label"><span>${title}</span><span class="metric-icon">${icon(glyph)}</span></div><div class="metric-value">${value}</div><div class="metric-detail">${detail}</div></article>`;
}

export {inboxView} from './inbox-ui.js';

export {benchmarkView as marketView} from './benchmark-ui.js';

export function savedViewBar(s) {
  const rows=s.ops?.saved_views||[];
  // Lives at the end of the quick-views row: personal views are just more quick views.
  return `<div class="saved-views">${rows.length?'<span class="sr-only">Viste personali</span>':''}${rows.map(v=>`<div class="saved-view"><button data-action="apply-view" data-id="${e(v.id)}">${e(v.name)}</button><button data-action="delete-view" data-id="${e(v.id)}" aria-label="Elimina vista ${e(v.name)}">${icon('close')}</button></div>`).join('')}${action('save-view','Salva vista','plus','text-button','title="Salva filtri e ordinamento correnti"')}</div>`;
}

export {scenarioForm,scenarioResult} from './scenario-ui.js';

export {comparablesContent} from './comparables-ui.js';

export function propertyTools(s,p) {
  return `<div class="property-tools">${action('deal-work','Revisione','board','btn',`data-id="${e(p.id)}"`)}${action('comparables','Comparabili','compare','btn',`data-id="${e(p.id)}"`)}${action('scenarios','Scenario economico','calculator','btn',`data-id="${e(p.id)}" ${p.currency==='EUR'?'':'disabled title="Richiede valuta EUR verificata"'}`)}</div>`;
}

export function duplicateControls(s,pair) {
  const [a,b]=[pair.a,pair.b].sort();
  const reviewed=s.ops?.duplicate_reviews?.find(r=>r.a===a&&r.b===b);
  if(s.user.role==='viewer') return reviewed?badge(reviewed.decision==='same_asset'?'Stesso asset':'Distinti'):'';
  return `<div class="duplicate-controls">${reviewed?`<span class="quiet-pill">${reviewed.decision==='same_asset'?'Stesso asset confermato':'Annunci distinti'}</span>`:''}${action('duplicate-review','Stesso asset','','btn small-btn',`data-a="${e(a)}" data-b="${e(b)}" data-decision="same_asset" ${s.duplicateBusy?'disabled':''}`)}${action('duplicate-review','Distinti','','btn small-btn',`data-a="${e(a)}" data-b="${e(b)}" data-decision="distinct" ${s.duplicateBusy?'disabled':''}`)}</div>`;
}

export function operationsSettings(s) {
  const ops=s.ops||{}, worker=ops.worker||{};
  return `<section class="panel settings-panel full-settings"><div class="section-heading"><div><h2>Stato operativo</h2><p>${e(ops.workspace?.name||'Workspace')} · istanza dedicata</p></div>${s.user.role==='admin'?action('readiness','Verifica sistema','pulse','btn'):''}</div><dl class="settings-facts"><div><dt>Ultimo heartbeat del worker</dt><dd>${worker.last_tick?relative(worker.last_tick):'Non rilevato'}</dd></div><div><dt>Budget per esecuzione</dt><dd>${num((ops.limits?.run_timeout_seconds||0)/60)} minuti</dd></div><div><dt>Analisi AI per run</dt><dd>Massimo ${num(ops.limits?.max_ai_listings)}</dd></div><div><dt>Email</dt><dd>${ops.mail?.enabled?'Attive':'Non configurate'} · ${ops.mail?.pending||0} in attesa · ${ops.mail?.failed||0} fallite</dd></div></dl><div class="usage-summary"><h3>Consumi AI registrati</h3><p>${num(ops.ai_usage?.accepted_analyses||0)} analisi accettate · ${num(ops.ai_usage?.input_tokens)} token input · ${num(ops.ai_usage?.output_tokens)} token output</p><p>${ops.ai_usage?.estimated_eur==null?"Costo non calcolabile senza usage e tariffe configurate":"Stima delle risposte accettate: € "+num(ops.ai_usage.estimated_eur,4)}</p><small>Non è una fattura: tentativi falliti o output rifiutati possono essere addebitati dal provider e non sono inclusi.</small></div><div id="readiness-result"></div><div class="settings-security-actions">${action('password','Cambia password','lock','btn')}${s.user.role==='admin'?action('audit','Registro modifiche','document','btn'):''}<a href="/api/docs" class="btn" target="_blank" rel="noopener">API reference ${icon('upRight')}</a></div><p class="small muted">Workspace privato. L’amministratore gestisce gli accessi del team.</p></section>`;
}
