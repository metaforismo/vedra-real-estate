import {action,badge,empty,pageHeading} from './ui.js';
import {icon} from './icons.js';
import {monogram} from './sources-ui.js';
import {cardMenu} from './menu-ui.js';
import {e,label,num,relative,stamp,activeRun,engineName} from './utils.js';

const online=a=>a.runtime==='scout'||!!a.criteria.online_discovery;

export function frequency(minutes){
  if(!minutes)return 'Avvio manuale';
  if(minutes%1440===0)return minutes===1440?'Ogni giorno':minutes===10080?'Ogni settimana':`Ogni ${minutes/1440} giorni`;
  if(minutes%60===0)return minutes===60?'Ogni ora':`Ogni ${minutes/60} ore`;
  return `Ogni ${num(minutes)} min`;
}
// Future times read in the unit people plan with: "tra 4 ore", not "tra 250 min".
function until(value){
  const minutes=Math.max(1,Math.round((new Date(value)-Date.now())/60000));
  if(minutes<60)return `tra ${minutes} min`;
  if(minutes<1440){const h=Math.round(minutes/60);return `tra ${h} ${h===1?'ora':'ore'}`;}
  return new Date(value).toLocaleString('it-IT',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
}
// Budgets read the way they are said: "fino a 3 mln €", "500 mila – 1,5 mln €".
function short(value,unit=true){
  if(value>=1e6)return `${num(value/1e6,2)}${unit?' mln €':''}`;
  if(value>=1e3)return `${num(value/1e3)}${unit?' mila €':''}`;
  return `${num(value)}${unit?' €':''}`;
}
export function budget(c){
  if(!c.min_price)return `Fino a ${short(c.max_price)}`;
  // One unit for the pair when both sides share it: "1–3 mln €".
  const same=(c.min_price>=1e6)===(c.max_price>=1e6)&&(c.min_price>=1e3)===(c.max_price>=1e3);
  return same?`${short(c.min_price,false)}–${short(c.max_price)}`:`${short(c.min_price)} – ${short(c.max_price)}`;
}
function surface(c){
  if(c.min_surface&&c.max_surface)return `${num(c.min_surface)}–${num(c.max_surface)} m²`;
  if(c.min_surface)return `Da ${num(c.min_surface)} m²`;
  if(c.max_surface)return `Fino a ${num(c.max_surface)} m²`;
  return '';
}
// The status lives in the badge only: the schedule line never repeats it. Oggi reuses it for its status dot.
const queued=a=>a.active&&a.interval_minutes&&a.next_run&&new Date(a.next_run)<=new Date();
export function state(a){
  if(activeRun(a.last_run))return [label(a.last_run.status),'success'];
  if(a.last_run?.status==='failed')return ['Ultima ricerca non riuscita','warning'];
  if(a.last_run?.status==='partial')return ['Ricerca parziale','warning'];
  if(!a.active)return ['In pausa','neutral'];
  if(queued(a))return ['In coda','success'];
  return [a.interval_minutes?'Programmata':'Manuale','success'];
}
// Engine, then the named sources: more useful than a count, shortened after two.
function engineLine(a,sources){
  const own=a.source_ids.map(id=>sources.find(x=>x.id===id)).filter(Boolean);
  const engine=online(a)?engineName(a.runtime):engineName(a.runtime==='llm'?'llm':'local');
  const names=own.slice(0,2).map(x=>e(x.name)).join(', ')+(own.length>2?` e altre ${own.length-2}`:'');
  return `<p class="search-card-engine">${icon(online(a)?'spark':'code')}<span><strong>${engine}</strong>${names?` · ${names}`:''}</span></p>`;
}

function card(a,s,canEdit){
  const c=a.criteria,[status,tone]=state(a),running=activeRun(a.last_run);
  const facts=[budget(c),surface(c),c.property_types?.length?c.property_types.map(label).join(', '):'',c.strategies.length?c.strategies.map(label).join(', '):''].filter(Boolean);
  const filters=[c.opportunity_only?`Solo sotto il prezzo di zona${c.min_discount?` (−${num(c.min_discount)}%)`:''}`:'',c.contact_policy==='require_direct'?'Solo contatto diretto':c.contact_policy==='prefer_direct'?'Precedenza al contatto diretto':'',c.include_auctions?'':'Aste escluse'].filter(Boolean);
  const place=[a.city,c.location_query].filter(Boolean).map(e).join(' · ');
  const at=a.last_run?.finished_at||a.last_run?.created_at;
  const last=a.last_run?`${a.last_run.status==='completed'?'Ultima ricerca':'Ultimo tentativo'} ${relative(at)}`:'Mai eseguita';
  const next=a.active&&a.interval_minutes&&a.next_run&&!queued(a)?`prossima ${until(a.next_run)}`:'';
  const menu=[
    canEdit?action('duplicate-agent','Crea una variante','plus','menu-item',`data-id="${e(a.id)}"`):'',
    canEdit?action('toggle-agent',a.active?'Pausa':'Riprendi',a.active?'pause':'play','menu-item',`data-id="${e(a.id)}"`):'',
    action('agent-readiness','Verifica accesso','quality','menu-item',`data-id="${e(a.id)}"`),
  ];
  return `<article class="agent-card search-card" data-tone="${tone}">
    <header class="search-card-head"><div class="search-card-title"><h2>${e(a.name)}</h2><p>${icon('pin')}<span>${place}</span></p></div>${badge(status,tone)}</header>
    <p class="search-card-facts">${facts.map(x=>`<span>${e(x)}</span>`).join('')}</p>
    ${filters.length?`<p class="search-card-filters">${filters.map(e).join(' · ')}</p>`:''}
    ${c.custom_prompt?`<details class="agent-custom"><summary>Criteri personalizzati</summary><p>${e(c.custom_prompt)}</p></details>`:''}
    <button class="stat-button search-card-result" data-action="agent-results" data-id="${e(a.id)}"><strong>${a.last_run?num(a.qualified):'—'}</strong><span>nei criteri</span><small>${a.last_run?`su ${num(a.total)} trovati`:'Nessuna esecuzione'}</small>${icon('arrow')}</button>
    ${engineLine(a,s.data.sources)}
    <p class="search-card-schedule">${frequency(a.interval_minutes)} · ${a.last_run?`<button class="plain-link" data-action="run-detail" data-id="${e(a.last_run.id)}" title="${e(stamp(at,true))}">${last}</button>`:last}${next?` · ${next}`:''}</p>
    <footer class="agent-actions">${canEdit?action('run-agent',running?'Mostra esecuzione':'Esegui ora',running?'pulse':'play','btn',`data-id="${e(a.id)}"`):''}<button class="btn" data-action="edit-agent" data-id="${e(a.id)}" aria-label="${canEdit?'Configura':'Vedi'} ${e(a.name)}">${canEdit?'Configura':'Vedi criteri'}</button>
      ${cardMenu(e(a.id),e(a.name),menu)}</footer>
  </article>`;
}

export function agentDirectory(s,agents){
  const canEdit=s.user.role!=='viewer';
  return `${pageHeading('','Ricerche','',canEdit?action('new-agent','Nuova ricerca','plus','btn primary'):'')}
    <div class="agent-grid search-grid">${[...agents].sort((a,b)=>Number(online(b))-Number(online(a))).map(a=>card(a,s,canEdit)).join('')}${!agents.length?empty('Nessuna ricerca',canEdit?'Crea una ricerca: zona, budget, fonti e istruzioni per Scout.':'Le ricerche del team compariranno qui.','','search'):''}</div>`;
}

// Agent readiness: a local configuration check, shown as a checklist that ends in a verdict.
export function readinessContent(data,canEdit){
  const blocking=data.checks.filter(x=>!x.ok&&x.blocking).length;
  const verdict=blocking?`${num(blocking)} ${blocking===1?'problema blocca':'problemi bloccano'} l’esecuzione`:'Pronta per l’esecuzione';
  const row=check=>`<li class="readiness-check" data-state="${check.ok?'ok':check.blocking?'block':'warn'}">${icon(check.ok?'check':check.blocking?'close':'info')}<p>${e(check.message)}</p><span>${check.ok?'OK':check.blocking?'Da configurare':'Attenzione'}</span></li>`;
  return `<div class="modal-body readiness">
    <p class="readiness-verdict" data-state="${blocking?'block':'ok'}">${icon(blocking?'warning':'check')}<span>${verdict}</span></p>
    <ul class="readiness-checks">${data.checks.map(row).join('')}</ul>
    <h3 class="readiness-heading">Fonti di questa ricerca</h3>
    ${data.sources.length?`<ul class="readiness-sources">${data.sources.map(src=>`<li class="preflight-source">${monogram(src)}<div><strong>${e(src.name)}</strong>${src.blockers.map(x=>`<p class="danger-text">${e(x)}</p>`).join('')}${src.warnings.map(x=>`<p>${e(x)}</p>`).join('')}${!src.blockers.length&&!src.warnings.length?'<p>Pronta</p>':''}</div></li>`).join('')}</ul>`:empty('Nessuna fonte','Configura la ricerca.','','document')}
    <p class="readiness-note">${e(data.notice)}</p>
    ${canEdit&&(data.can_enqueue||data.active_run)?`<div class="modal-form-footer">${action('run-agent',data.active_run?'Mostra esecuzione':'Esegui ora',data.active_run?'pulse':'play','btn primary',`data-id="${e(data.agent_id)}"`)}</div>`:''}
  </div>`;
}

// Research dialog: the section bar jumps to a section and follows the scroll, so a long form reads as four short steps.
function spy(form){
  const nav=form.querySelector('.research-steps');if(!nav)return;
  const sections=[...form.querySelectorAll('.research-section')],line=form.scrollTop+nav.offsetHeight+32;
  const atEnd=form.scrollTop+form.clientHeight>=form.scrollHeight-4;
  const current=atEnd?sections.at(-1):sections.filter(x=>x.offsetTop<=line).at(-1)||sections[0];
  const key=current?.getAttribute('aria-labelledby')?.replace(/-heading$/,'');
  for(const button of nav.querySelectorAll('button')){if(button.dataset.researchJump===key)button.setAttribute('aria-current','true');else button.removeAttribute('aria-current');}
  // On narrow screens the bar scrolls sideways: keep the current step in view.
  const active=nav.querySelector('[aria-current]');
  if(active&&(active.offsetLeft<nav.scrollLeft||active.offsetLeft+active.offsetWidth>nav.scrollLeft+nav.clientWidth))nav.scrollLeft=active.offsetLeft-16;
}
if(typeof document!=='undefined'){
  document.addEventListener('click',event=>{
    const jump=event.target.closest?.('[data-research-jump]');if(!jump)return;
    const form=jump.closest('form'),section=form?.querySelector(`[aria-labelledby="${jump.dataset.researchJump}-heading"]`);if(!section)return;
    const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
    form.scrollTo({top:section.offsetTop-form.querySelector('.research-steps').offsetHeight,behavior:reduce?'auto':'smooth'});
  });
  document.addEventListener('scroll',event=>{if(event.target.classList?.contains('research-form'))spy(event.target);},true);
  // Budgets are typed as digits and read back grouped ("1.500.000") once the field is left.
  document.addEventListener('focusout',event=>{
    const field=event.target;if(!field.matches?.('input[data-thousands]'))return;
    const value=amountValue(field.value);if(Number.isFinite(value)&&field.value.trim())field.value=num(value);
  });
}
// "1.500.000", "1 500 000" and "1500000" are the same budget; a decimal comma is honoured, then rounded.
export function amountValue(text){
  const clean=String(text??'').replace(/[.\s\u00a0€]/g,'').replace(',','.');
  return clean===''||!/^\d+(\.\d+)?$/.test(clean)?NaN:Math.round(Number(clean));
}
