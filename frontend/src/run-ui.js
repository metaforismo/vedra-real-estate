import {icon} from './icons.js';
import {e,label,num,stamp,relative,safeUrl,activeRun,tone} from './utils.js';
import {notice,badge} from './ui.js';

// Scout's own narration: which page it read, what it saw, what it acquired. Evidence for trusting the run.
function scoutTrail(run){
  if(run.runtime!=='scout')return '';
  const events=(run.events||[]).filter(x=>x.step==='scout'||(x.step==='extract'&&x.data?.property_id)||(x.step==='source'&&x.level!=='info'));
  if(!events.length)return '';
  const row=x=>x.step==='scout'
    ?`<li class="trail-page"><span class="trail-kind">Pagina</span><div><p>${e(x.message.replace(/^Pagina (letta|non interpretata): /,''))}</p>${safeUrl(x.data?.url)?`<a href="${safeUrl(x.data.url)}" target="_blank" rel="noopener noreferrer">${e(((u=>u.pathname+u.search)(new URL(x.data.url))).slice(0,80)||'/')}</a>`:''}</div></li>`
    :x.step==='extract'?`<li class="trail-listing"><span class="trail-kind">${x.data?.new?'Nuovo':'Aggiornato'}</span><div><button class="plain-link" data-action="property" data-id="${e(x.data.property_id)}">${e(x.message.replace(/^Acquisito: /,''))}</button></div></li>`
    :`<li class="trail-block"><span class="trail-kind">Fonte</span><div><p>${e(x.message)}</p></div></li>`;
  return `<details class="run-disclosure scout-trail" open><summary>Cosa ha fatto Scout<span>${num(events.filter(x=>x.step==='extract').length)} annunci</span></summary><div class="run-disclosure-body"><ol class="trail">${events.slice(-40).map(row).join('')}</ol></div></details>`;
}

function researchTrace(run) {
  const c=run.config_snapshot?.criteria||{}, events=run.events||[];
  const delivered=events.find(x=>x.step==='research_brief');
  const pages=[...new Set(events.flatMap(x=>['browser','scout'].includes(x.step)?[x.data?.url]:x.step==='hermes_discovery'?(x.data?.pages||[]):[]))].filter(url=>safeUrl(url));
  const hasInstructions=c.research_instructions||c.custom_prompt||c.opportunity_only||Object.keys(c.source_urls||{}).length||c.contact_policy&&c.contact_policy!=='any';
  if(!hasInstructions&&!pages.length)return '';
  const targets=delivered?.data?.targets||Object.entries(c.source_urls||{}).map(([source_id,url])=>({source_id,url}));
  const lines=String(c.custom_prompt||'').split('\n').filter(x=>x.trim());
  return `<details class="run-disclosure research-trace" id="run-instructions"><summary id="run-instructions-toggle">Istruzioni e percorso<span>${num(pages.length)} ${pages.length===1?'pagina':'pagine'}</span></summary><div class="run-disclosure-body">
    ${c.opportunity_only?`<p>Solo sotto benchmark${c.min_discount?` · soglia ${num(c.min_discount)}%`:''}</p>`:''}
    ${c.contact_policy&&c.contact_policy!=='any'?`<p>${c.contact_policy==='require_direct'?'Contatto diretto dichiarato con recapito':'Priorità al contatto diretto'}</p>`:''}
    ${c.research_instructions?`<h3>Istruzioni di ricerca</h3><p class="preserve-lines">${e(c.research_instructions)}</p><small>${run.runtime==='scout'?'Seguite da Scout durante la navigazione':delivered?'Brief consegnato a Hermes':'Consegna non registrata'}</small>`:''}
    ${lines.length?`<h3>Criteri richiesti</h3><ol>${lines.map(line=>`<li>${e(line)}</li>`).join('')}</ol>`:''}
    ${targets.length?`<h3>Pagine di partenza</h3><ul class="run-pages">${targets.filter(x=>safeUrl(x.url)).map(x=>`<li><a href="${safeUrl(x.url)}" target="_blank" rel="noopener noreferrer">${e(x.name||x.url)}</a></li>`).join('')}</ul>`:''}
    <h3>Pagine consultate</h3>${pages.length?`<ul class="run-pages">${pages.map(url=>`<li><a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${e(url)}</a></li>`).join('')}</ul>`:'<p>Nessuna visita registrata.</p>'}
    <p class="small muted">Le visite documentano il percorso. Gli esiti dei criteri sono nelle schede immobili.</p>
  </div></details>`;
}

function analysisProgress(run) {
  if(!['hermes','llm'].includes(run.runtime))return '';
  const p=run.analysis_progress, c=run.config_snapshot?.criteria||{};
  if(!p)return '';
  const waiting=!run.collected&&!p.total;
  return `<section class="run-analysis" aria-label="Analisi AI"><div><strong>Analisi AI</strong><span>${waiting?(activeRun(run)?'In attesa della raccolta':'Raccolta non completata'):p.total?`${num(p.accepted)} / ${num(p.total)} risposte accettate`:'Nessuna nuova analisi richiesta'}</span></div>
    ${p.pending?`<p class="evidence-warning">${num(p.pending)} ${p.pending===1?'annuncio da analizzare':'annunci da analizzare'}${activeRun(run)?'':'. Avvia una nuova ricerca per riprovare.'}</p>`:''}
    <details id="run-validation"><summary id="run-validation-toggle">Cosa viene controllato</summary><p>${c.custom_prompt?'Il prompt salvato per questa esecuzione viene associato agli annunci. Le risposte devono coprire i requisiti e citare il testo acquisito. Un requisito omesso resta da verificare.':'Le strategie richiedono citazioni del testo acquisito.'} Una risposta accettata può escludere un annuncio o segnalarlo come incerto; non certifica la correttezza del modello.</p></details>
  </section>`;
}

export function runContent(run,canEdit=true) {
  const events=run.events||[], stats=run.stats||{}, last=events.at(-1), active=activeRun(run);
  const waiting=run.status==='running'&&run.runtime==='hermes'&&last?.step==='hermes';
  const headline={queued:'In attesa del servizio di ricerca.',running:waiting?'In attesa di Hermes.':'Raccolta e analisi in corso.',cancelling:'Interruzione richiesta.',completed:'Ricerca completata.',partial:'Ricerca parziale: controlla i passaggi mancanti.',failed:'Ricerca non riuscita.',cancelled:'Ricerca annullata.',interrupted:'Ricerca interrotta.'}[run.status]||'Stato non disponibile.';
  const steps={queue:'Avvio',source:'Fonte',discovery:'Raccolta',screening:'Selezione',hermes:'Hermes',scout:'Scout',research_brief:'Istruzioni',browser:'Browser',hermes_discovery:'Ricerca',hermes_discovery_failed:'Fonte non disponibile',hermes_acquire:'Acquisizione',availability:'Disponibilità',classify:'Analisi',error:'Errore',finish:'Esito'};
  return `<div class="run-meta">${badge(label(run.status),tone(run.status))}<span class="runtime-label">${icon(['hermes','scout'].includes(run.runtime)?'spark':'code')} ${{hermes:'Hermes',scout:'Scout',llm:'AI sull’archivio'}[run.runtime]||'Regole locali'}</span>${active&&canEdit?`<button id="run-cancel" class="btn small-btn danger-outline" data-action="cancel-run" data-id="${e(run.id)}" ${run.status==='cancelling'?'disabled':''}>${icon('stop')} Interrompi</button>`:''}</div>
    <p class="run-outcome" role="status">${active?'<span class="spinner"></span>':''}${headline}</p>
    ${waiting&&last?`<p class="small muted">Ultimo aggiornamento ${relative(last.time)}</p>`:''}
    <div class="run-stat-grid">${[['Elaborati',stats.processed],['Nuovi',stats.new],['Modificati',stats.changed],['Errori',stats.errors]].map(([k,v])=>`<div><strong>${num(v)}</strong><span>${k}</span></div>`).join('')}</div>
    ${stats.sources_total!=null?`<p class="run-coverage">${num(stats.sources_ok)} / ${num(stats.sources_total)} fonti elaborate${stats.cached?` · ${num(stats.cached)} annunci già acquisiti riutilizzati`:''}${stats.page_requests?` · ${num(stats.page_requests)} pagine aperte`:''}${stats.ai_calls?` · ${num(stats.ai_calls)} letture AI${stats.ai_estimated_eur?` · € ${num(stats.ai_estimated_eur,3)}`:''}`:''}</p>`:''}
    ${run.error?notice(e(run.error),'warning'):''}${analysisProgress(run)}${scoutTrail(run)}${researchTrace(run)}
    <details class="run-disclosure" id="run-log"><summary id="run-log-toggle">Registro attività<span>${num(events.length)} eventi</span></summary><div class="run-disclosure-body run-timeline">${events.length?events.map(ev=>`<div class="timeline-event ${e(ev.level)}"><span class="timeline-icon">${icon(ev.level==='error'?'warning':ev.level==='warning'?'info':'check')}</span><div><span class="event-step">${e(steps[ev.step]||ev.step)} <time>${new Date(ev.time).toLocaleTimeString('it-IT')}</time></span><p>${e(ev.message)}</p></div></div>`).join(''):'<p>Nessun evento registrato.</p>'}</div></details>
    ${run.agent_id?`<div class="run-next"><button class="btn" data-action="agent-results" data-id="${e(run.agent_id)}">${icon('arrow')} Risultati attuali della ricerca</button></div>`:''}
    <div class="run-footer"><span>Avvio ${stamp(run.created_at,true)}</span><span>${run.finished_at?`Fine ${stamp(run.finished_at,true)}`:active?'In corso':'Fine non registrata'}</span></div>`;
}

export function updateRunContent(container,run,canEdit=true) {
  // Polling must not close the evidence the user is reading or steal keyboard focus.
  const opened=new Set([...container.querySelectorAll('details[open][id]')].map(el=>el.id));
  const focused=container.contains(document.activeElement)?document.activeElement:null;
  const focusId=focused?.id, parent=focused?.closest('details[id]')?.id;
  const dialog=container.closest('dialog'), scrollTop=dialog?.scrollTop;
  container.innerHTML=runContent(run,canEdit);
  for(const el of container.querySelectorAll('details[id]'))el.open=opened.has(el.id);
  if(focusId)container.querySelector(`[id="${focusId}"]`)?.focus({preventScroll:true});
  else if(parent)container.querySelector(`[id="${parent}"]>summary`)?.focus({preventScroll:true});
  if(dialog)dialog.scrollTop=scrollTop;
}
