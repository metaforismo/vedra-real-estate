import {icon} from './icons.js';
import {e, num, euro, amount, relative, stamp, label, reviewLabel, score, discount, strategyTags, selectOptions, activeRun, availabilityTag} from './utils.js';
import {action, badge, empty, notice, pageHeading} from './ui.js';
import {mapPanel} from './map.js';
import {grouped} from './table-ui.js';

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
  const ops=s.ops||{}, worker=ops.worker||{}, usage=ops.ai_usage||{}, admin=s.user.role==='admin';
  const rows=[['Worker',worker.last_tick?`Ultimo segnale ${relative(worker.last_tick)}`:'Nessun segnale rilevato'],['Durata massima per esecuzione',`${num((ops.limits?.run_timeout_seconds||0)/60)} minuti`],['Analisi AI per esecuzione',`Fino a ${num(ops.limits?.max_ai_listings)}`],['Email',ops.mail?.enabled?`Attive · ${num(ops.mail?.pending||0)} in attesa · ${num(ops.mail?.failed||0)} non inviate`:'Non configurate'],
    ['Consumi AI registrati',`${grouped(usage.accepted_analyses||0)} analisi accettate · ${grouped(usage.input_tokens)} token in ingresso · ${grouped(usage.output_tokens)} in uscita<small>${usage.estimated_eur==null?'Costo non calcolabile senza tariffe configurate.':'Stima sulle risposte accettate: € '+num(usage.estimated_eur,4)+'.'} Non è una fattura: il provider può addebitare anche tentativi falliti o risposte scartate.</small>`]];
  return `<section class="pg-surface settings-panel set-section">${`<div class="pg-head"><div><h2>Account e stato operativo</h2><p>${e(ops.workspace?.name||'Workspace')} · istanza dedicata e privata</p></div><div class="set-actions">${action('password','Cambia password','lock','btn')}</div></div>`}
    <dl class="set-rows">${rows.map(([k,v])=>`<div><dt>${e(k)}</dt><dd>${v}</dd></div>`).join('')}</dl>
    <div id="readiness-result"></div>
    <div class="set-foot">${admin?action('readiness','Verifica sistema','pulse','btn'):''}${admin?action('audit','Registro modifiche','document','btn'):''}<a href="/api/docs" class="btn" target="_blank" rel="noopener">Documentazione API ${icon('upRight')}</a></div></section>`;
}
