import {icon} from './icons.js';
import {e, num, relative} from './utils.js';
import {action, badge} from './ui.js';
import {grouped} from './table-ui.js';

export {stages,pipelineView,workForm} from './pipeline-ui.js';

export {inboxView} from './inbox-ui.js';

export {benchmarkView as marketView} from './benchmark-ui.js';

export function savedViewBar(s) {
  const rows=s.ops?.saved_views||[];
  // Lives at the end of the quick-views row: personal views are just more quick views.
  return `<div class="saved-views">${rows.length?'<span class="sr-only">Viste personali</span>':''}${rows.map(v=>`<div class="saved-view"><button data-action="apply-view" data-id="${e(v.id)}">${e(v.name)}</button><button data-action="delete-view" data-id="${e(v.id)}" aria-label="Elimina vista ${e(v.name)}">${icon('close')}</button></div>`).join('')}${action('save-view','Salva vista','plus','text-button','title="Salva filtri e ordinamento correnti"')}</div>`;
}

export {scenarioForm,scenarioResult} from './scenario-ui.js';

export {comparablesContent} from './comparables-ui.js';

// Analysis tools of the sheet, all secondary and text-only (icons stay on the export group): the one primary action is Registra contatto.
export function propertyTools(s,p) {
  return `<div class="property-tools" role="group" aria-label="Analisi">${action('comparables','<span>Comparabili</span>','','btn',`data-id="${e(p.id)}"`)}${action('scenarios','<span>Scenario<span class="tool-long"> economico</span></span>','','btn',`data-id="${e(p.id)}" aria-label="Scenario economico" ${p.currency==='EUR'?'':'disabled title="Richiede valuta EUR verificata"'}`)}${action('deal-work','<span>Revisione</span>','','btn',`data-id="${e(p.id)}"`)}</div>`;
}

export function duplicateControls(s,pair) {
  const [a,b]=[pair.a,pair.b].sort();
  const reviewed=s.ops?.duplicate_reviews?.find(r=>r.a===a&&r.b===b);
  if(s.user.role==='viewer') return reviewed?badge(reviewed.decision==='same_asset'?'Stesso asset':'Distinti'):'';
  return `<div class="duplicate-controls">${reviewed?`<span class="quiet-pill">${reviewed.decision==='same_asset'?'Stesso asset confermato':'Annunci distinti'}</span>`:''}${action('duplicate-review','Stesso asset','','btn small-btn',`data-a="${e(a)}" data-b="${e(b)}" data-decision="same_asset" ${s.duplicateBusy?'disabled':''}`)}${action('duplicate-review','Distinti','','btn small-btn',`data-a="${e(a)}" data-b="${e(b)}" data-decision="distinct" ${s.duplicateBusy?'disabled':''}`)}</div>`;
}

// Technical status for whoever installs Vedra: worker, limits, email and what the AI has cost so far.
export function operationsSettings(s) {
  const ops=s.ops||{}, worker=ops.worker||{}, usage=ops.ai_usage||{}, admin=s.user.role==='admin';
  const accepted=usage.accepted_analyses||0;
  const cost=usage.estimated_eur==null?'costo non stimabile senza tariffe configurate':`costo stimato € ${num(usage.estimated_eur,2)}`;
  const rows=[['Worker',worker.last_tick?`Ultimo segnale ${relative(worker.last_tick)}`:'Nessun segnale rilevato'],['Durata massima per esecuzione',`${num((ops.limits?.run_timeout_seconds||0)/60)} minuti`],['Analisi AI per esecuzione',`Fino a ${num(ops.limits?.max_ai_listings)}`],['Email',ops.mail?.enabled?`Attive · ${num(ops.mail?.pending||0)} in attesa · ${num(ops.mail?.failed||0)} non inviate`:'Non configurate'],
    ['Consumi AI',`${grouped(accepted)} ${accepted===1?'analisi accettata':'analisi accettate'} · ${cost}<small>Stima sulle risposte accettate, non una fattura del provider.</small>`]];
  return `<section class="pg-surface settings-panel set-section ops-settings"><div class="pg-head"><div><h2>Stato operativo</h2><p>${e(ops.workspace?.name||'Workspace')} · istanza dedicata e privata</p></div></div>
    <dl class="set-rows">${rows.map(([k,v])=>`<div><dt>${e(k)}</dt><dd>${v}</dd></div>`).join('')}</dl>
    <div id="readiness-result"></div>
    <div class="set-foot">${admin?action('readiness','Verifica sistema','pulse','btn'):''}${admin?action('audit','Registro modifiche','document','btn'):''}<a href="/api/docs" class="btn" target="_blank" rel="noopener">Documentazione API ${icon('upRight')}</a></div></section>`;
}
