import {icon} from './icons.js';
import {e,label,num,stamp,relative,safeUrl,activeRun,tone,engineName} from './utils.js';
import {notice,badge} from './ui.js';

const plural=(n,one,many)=>`${num(n)} ${n===1?one:many}`;
function shortUrl(url){try{const u=new URL(url);return (u.host.replace(/^www\./,'')+u.pathname+u.search).slice(0,80);}catch{return url;}}
// Scout's own narration: which page it read, what it saw, what it acquired, what stopped it. Evidence for trusting the run.
function scoutTrail(run){
  if(run.runtime!=='scout')return '';
  const events=(run.events||[]).filter(x=>x.step==='scout'||(x.step==='extract'&&x.data?.property_id)||(x.step==='source'&&x.level!=='info'));
  if(!events.length)return '';
  const pages=events.filter(x=>x.step==='scout').length,listings=events.filter(x=>x.step==='extract').length;
  const row=x=>{
    if(x.step==='scout'){
      const failed=/^Pagina non interpretata/.test(x.message);
      let text=x.message.replace(/^Pagina (letta|non interpretata): /,''),meta='';
      // engine.py: "N annunci pertinenti, M altri, K sezioni da aprire. {nota}"
      const counts=text.match(/^(\d+) annunci pertinenti, (\d+) altri, (\d+) sezioni da aprire\.\s*/);
      if(counts){meta=[plural(Number(counts[1]),'annuncio pertinente','annunci pertinenti'),Number(counts[3])?plural(Number(counts[3]),'sezione da aprire','sezioni da aprire'):''].filter(Boolean).join(' · ');text=text.slice(counts[0].length);}
      return `<li class="trail-page ${failed?'trail-block':''}"><div><p class="trail-head"><span class="trail-kind">${failed?'Pagina non letta':'Pagina letta'}</span>${meta?`<span class="trail-meta">${meta}</span>`:''}</p>${text?`<p>${e(text)}</p>`:''}${safeUrl(x.data?.url)?`<a href="${safeUrl(x.data.url)}" target="_blank" rel="noopener noreferrer">${e(shortUrl(x.data.url))}</a>`:''}</div></li>`;
    }
    if(x.step==='extract'){
      // engine.py: fit = chosen as pertinent from the results page, reason = words of that card, open = what the page did not state.
      const d=x.data||{};
      const why=d.fit===false?'Aperto per completare la ricerca, non scelto come pertinente':d.reason?`Motivo: “${e(d.reason)}”`:d.fit?'Scelto dalla scheda dei risultati':'';
      const open=Array.isArray(d.open)?(d.open.length?`Non indicato nella pagina: ${e(d.open.join(', '))}`:'Prezzo, superficie, stato e recapito indicati'):'';
      return `<li class="trail-listing"><div><p class="trail-head"><span class="trail-kind">${d.new?'Nuovo annuncio':'Annuncio aggiornato'}</span></p><button class="plain-link" data-action="property" data-id="${e(d.property_id)}">${e(x.message.replace(/^Acquisito: /,''))}</button>${why?`<p class="trail-meta">${why}</p>`:''}${open?`<p class="trail-meta">${open}</p>`:''}</div></li>`;
    }
    return `<li class="trail-block"><div><p class="trail-head"><span class="trail-kind">Fonte bloccata</span></p><p>${e(x.message)}</p></div></li>`;
  };
  return `<details class="run-disclosure scout-trail" id="run-trail" open><summary>Cosa ha fatto Scout<span>${plural(pages,'pagina','pagine')} · ${plural(listings,'annuncio','annunci')}</span></summary><div class="run-disclosure-body"><ol class="trail">${events.slice(-40).map(row).join('')}</ol></div></details>`;
}

function duration(run){
  const start=new Date(run.started_at||run.created_at),end=run.finished_at?new Date(run.finished_at):activeRun(run)?new Date():null;
  if(!end||isNaN(start)||end<start)return '';
  const s=Math.round((end-start)/1000);
  return s<60?`${s} s`:s<3600?`${Math.floor(s/60)} min${s%60?` ${s%60} s`:''}`:`${Math.floor(s/3600)} h ${Math.floor(s%3600/60)} min`;
}
// Four numbers that tell the run as a story: what was opened, what was acquired, what went wrong, what it cost.
function runStory(run){
  const st=run.stats||{},events=run.events||[];
  const blocked=events.filter(x=>x.step==='source'&&x.level!=='info').length;
  const sources=st.sources_total!=null?`${num(st.sources_ok)} / ${num(st.sources_total)} fonti riuscite`:'';
  const cell=(value,name,detail='')=>`<div><strong>${value}</strong><span>${name}</span>${detail?`<small>${detail}</small>`:''}</div>`;
  if(run.runtime==='scout'||st.page_requests!=null){
    const problems=st.errors==null&&!blocked?null:(st.errors||0)+blocked;
    return `<div class="run-stat-grid run-story">${[
      cell(num(st.page_requests),'Pagine aperte'),
      cell(num(st.processed),'Annunci acquisiti',st.processed!=null?[`${num(st.new)} nuovi`,`${num(st.changed)} aggiornati`,st.cached?`${num(st.cached)} già in archivio`:''].filter(Boolean).join(' · '):''),
      cell(num(problems),problems===1?'Problema':'Problemi',sources),
      cell(st.ai_estimated_eur!=null?`€ ${num(st.ai_estimated_eur,3)}`:'—','Costo AI',st.ai_calls?plural(st.ai_calls,'lettura AI','letture AI'):''),
    ].join('')}</div>`;
  }
  return `<div class="run-stat-grid run-story">${[cell(num(st.processed),'Elaborati'),cell(num(st.new),'Nuovi'),cell(num(st.changed),'Modificati'),cell(num(st.errors),'Errori',sources)].join('')}</div>${st.cached?`<p class="run-coverage">${num(st.cached)} annunci già acquisiti riutilizzati</p>`:''}`;
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
    ${c.opportunity_only?`<p>Solo sotto il prezzo di zona${c.min_discount?` · soglia ${num(c.min_discount)}%`:''}</p>`:''}
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
  // The outcome sentence answers "did it work, and why not": qualified count on success, the blocking reason otherwise.
  const blocker=!run.error&&['failed','partial','interrupted'].includes(run.status)?[...events].reverse().find(x=>x.step==='source'&&x.level!=='info'):null;
  const waiting=run.status==='running'&&run.runtime==='hermes'&&last?.step==='hermes';
  const headline={queued:'In attesa del servizio di ricerca.',running:waiting?'In attesa di Hermes.':'Raccolta e analisi in corso.',cancelling:'Interruzione richiesta.',completed:'Ricerca completata.',partial:'Ricerca parziale: controlla i passaggi mancanti.',failed:'Ricerca non riuscita.',cancelled:'Ricerca annullata.',interrupted:'Ricerca interrotta.'}[run.status]||'Stato non disponibile.';
  const steps={queue:'Avvio',source:'Fonte',discovery:'Raccolta',screening:'Selezione',hermes:'Hermes',scout:'Scout',research_brief:'Istruzioni',browser:'Browser',hermes_discovery:'Ricerca',hermes_discovery_failed:'Fonte non disponibile',hermes_acquire:'Acquisizione',availability:'Disponibilità',classify:'Analisi',error:'Errore',finish:'Esito'};
  return `<div class="run-meta">${badge(label(run.status),tone(run.status))}<span class="runtime-label">${icon(['hermes','scout'].includes(run.runtime)?'spark':'code')} ${engineName(run.runtime)}</span>${active&&canEdit?`<button id="run-cancel" class="btn small-btn danger-outline" data-action="cancel-run" data-id="${e(run.id)}" ${run.status==='cancelling'?'disabled':''}>${icon('stop')} Interrompi</button>`:''}</div>
    <p class="run-outcome" role="status">${active?'<span class="spinner"></span>':''}${headline}${run.status==='completed'&&stats.qualified!=null?` <span class="run-outcome-detail">${plural(stats.qualified,'annuncio nei criteri','annunci nei criteri')}.</span>`:''}</p>
    ${blocker?`<p class="run-reason">${e(blocker.message)}</p>`:''}
    ${waiting&&last?`<p class="small muted">Ultimo aggiornamento ${relative(last.time)}</p>`:''}
    ${run.error?notice(e(run.error),'warning'):''}
    ${runStory(run)}
    ${analysisProgress(run)}${scoutTrail(run)}${researchTrace(run)}
    <details class="run-disclosure" id="run-log"><summary id="run-log-toggle">Registro attività<span>${num(events.length)} eventi</span></summary><div class="run-disclosure-body run-timeline">${events.length?events.map(ev=>`<div class="timeline-event ${e(ev.level)}"><span class="timeline-icon">${icon(ev.level==='error'?'warning':ev.level==='warning'?'info':'check')}</span><div><span class="event-step">${e(steps[ev.step]||ev.step)} <time>${new Date(ev.time).toLocaleTimeString('it-IT')}</time></span><p>${e(ev.message)}</p></div></div>`).join(''):'<p>Nessun evento registrato.</p>'}</div></details>
    ${run.agent_id?`<div class="run-next"><button class="btn" data-action="agent-results" data-id="${e(run.agent_id)}">${icon('arrow')} Risultati attuali della ricerca</button></div>`:''}
    <div class="run-footer"><span>Avvio ${stamp(run.created_at,true)}</span><span>${run.finished_at?`Fine ${stamp(run.finished_at,true)}`:active?'In corso':'Fine non registrata'}${duration(run)?` · ${active?'da ':''}${duration(run)}`:''}</span></div>`;
}

export function updateRunContent(container,run,canEdit=true) {
  // Polling must not close the evidence the user is reading or steal keyboard focus.
  const opened=new Set([...container.querySelectorAll('details[open][id]')].map(el=>el.id));
  const known=new Set([...container.querySelectorAll('details[id]')].map(el=>el.id));
  const focused=container.contains(document.activeElement)?document.activeElement:null;
  const focusId=focused?.id, parent=focused?.closest('details[id]')?.id;
  const dialog=container.closest('dialog'), scrollTop=dialog?.scrollTop;
  container.innerHTML=runContent(run,canEdit);
  // A section that appears for the first time keeps its default state.
  for(const el of container.querySelectorAll('details[id]'))if(known.has(el.id))el.open=opened.has(el.id);
  if(focusId)container.querySelector(`[id="${focusId}"]`)?.focus({preventScroll:true});
  else if(parent)container.querySelector(`[id="${parent}"]>summary`)?.focus({preventScroll:true});
  if(dialog)dialog.scrollTop=scrollTop;
}
