import {todayPanel} from './decision-ui.js';
import {icon} from './icons.js';
import {e, num, amount, relative, score, discount, activeRun} from './utils.js';
import {action, empty, propertyThumb, panelHeading} from './ui.js';
import {mapPanel} from './map.js';

function gettingStarted(s) {
  const hasSource = s.data.sources.length > 0;
  const hasAgent = s.data.agents.length > 0;
  if (hasSource && hasAgent) {
    const blocked=s.data.sources.filter(x=>x.enabled&&x.status==='blocked').length;
    return `<section class="start-card"><span class="eyebrow">RICERCA</span><h2>Nessuna opportunità disponibile</h2>
      <p>${blocked?`${blocked} ${blocked===1?'fonte non accessibile':'fonti non accessibili'}. Controlla le fonti.`:'Gli annunci chiusi restano nell’archivio.'}</p>
      <a class="btn primary" href="#agents">Gestisci ricerche ${icon('arrow')}</a><a class="btn" href="#sources">Controlla fonti</a></section>`;
  }
  return `<section class="start-card"><span class="eyebrow">Per iniziare</span><h2>${hasSource ? 'Crea la prima ricerca' : 'Collega la prima fonte'}</h2>
    <p>Scout legge i siti delle agenzie come faresti tu e porta qui chi contattare, con i dati per valutare.</p>
    <ol class="start-steps"><li class="${hasSource ? 'done' : ''}"><span>${hasSource ? icon('check') : '1'}</span><a href="#sources">Scegli una rete di agenzie pronta o importa un file</a></li>
    <li class="${hasAgent ? 'done' : ''}"><span>${hasAgent ? icon('check') : '2'}</span><a href="#agents">Crea una ricerca: zona, budget, istruzioni</a></li>
    <li><span>3</span><span>Esegui ora: i contatti compaiono in questa pagina</span></li></ol>
    ${s.user.role === 'admin' ? (hasSource ? action('new-agent', 'Nuova ricerca', 'plus', 'btn primary') : action('new-source', 'Collega fonte', 'plus', 'btn primary') + action('import', 'Importa file', 'upload', 'btn')) : '<a class="btn" href="#sources">Visualizza le fonti</a>'}</section>`;
}

function rankedProperty(p) {
  return `<button class="rank-property" data-action="property" data-id="${e(p.id)}">
    ${propertyThumb(p, 'rank-thumb')}<span class="rank-text"><strong>${e(p.title)}</strong>
    <span>${[p.city,p.zone].filter(Boolean).map(e).join(' · ')}${p.price!=null?` · ${amount(p.price,p.currency)}`:''}</span></span><span class="rank-result">${score(p)}${discount(p)}</span></button>`;
}

function agentRow(a, editor) {
  const run=a.last_run, running=activeRun(run);
  const state=running?'Ricerca in corso':!run?'Mai eseguita':run.status==='failed'?'Non riuscita':run.status==='partial'?'Parziale':'Aggiornata';
  const tone=running?'live':!run||run.status==='completed'?'ok':'warn';
  return `<div class="agent-operation"><span class="agent-state ${tone}" aria-hidden="true"></span><div>
    <button class="plain-link" data-action="edit-agent" data-id="${e(a.id)}">${e(a.name)}</button>
    <small>${state}${run?` · ${relative(run.finished_at || run.created_at)}`:''}${a.active&&a.next_run&&a.interval_minutes&&!running?(new Date(a.next_run)>new Date()?` · prossima ${relative(a.next_run)}`:' · in coda'):''}</small></div>
    <span class="agent-found" title="Annunci nei criteri">${num(a.qualified)}</span>
    ${editor ? action('run-agent', '', running ? 'pulse' : 'play', 'icon-button', `data-id="${e(a.id)}" aria-label="${running?'Mostra':'Esegui'} ${e(a.name)}"`) : ''}</div>`;
}

// Four numbers that each open the archive already filtered: counts are doors, not decoration.
function pulse(s, archive) {
  const t=s.ops?.today||{call:[],verify:[]};
  const tile=(value,labelText,detail,attrs)=>`<button class="pulse-tile" ${attrs}><strong>${value==null?'—':num(value)}</strong><span>${labelText}</span><small>${detail}</small></button>`;
  return `<section class="pulse" aria-label="Sintesi">
    ${tile(t.call.length,'Da contattare',t.verify.length?`${num(t.verify.length)} da verificare`:'Recapiti pronti','data-action="scroll-today"')}
    ${tile(archive?.new_7d,'Nuovi · 7 giorni','Prime acquisizioni','data-action="open-focus" data-focus="new"')}
    ${tile(archive?.reduced,'Con ribassi','Prezzo sceso dalla prima rilevazione','data-action="open-focus" data-focus="reduced"')}
    ${tile(archive?.below_benchmark,'Sotto benchmark','Almeno 10% sotto il riferimento','data-action="open-focus" data-focus="below"')}
  </section>`;
}

// One line of scale: what is ready now and how much of the market was screened to find it.
function todaySummary(s,total){
  const t=s.ops?.today;if(!t||!s.data.agents.length)return '';
  const parts=[`${num(t.call.length)} ${t.call.length===1?'contatto pronto':'contatti pronti'}`];
  if(total)parts.push(`${num(total)} annunci monitorati`);
  return `<p class="today-summary">${parts.join(' · ')}</p>`;
}

function todayDate() {
  const text=new Date().toLocaleDateString('it-IT',{weekday:'long',day:'numeric',month:'long'});
  return text.charAt(0).toUpperCase()+text.slice(1);
}

export function liveOverview(s) {
  const d = {...s.data,properties:s.data.properties.filter(p=>!['sold','rented','withdrawn','review'].includes(p.availability))};
  const archive = s.insights?.archive;
  const total = archive?.total ?? d.stats.properties;
  const ranked = d.properties.filter(p => p.priority?.score != null && !['discarded', 'acquired'].includes(p.review_status)).sort((a,b)=>(b.priority?.score||0)-(a.priority?.score||0)).slice(0, 5);
  const editor = s.user.role !== 'viewer';
  const recent = s.notifications.slice(0, 4);
  const points = d.properties.filter(p => p.latitude != null && p.longitude != null).length;
  const heading = `<header class="today-heading"><div><p class="today-date">${todayDate()}</p><h1>Oggi</h1>${todaySummary(s,total)}</div><div class="heading-actions">${editor ? action('new-agent', 'Nuova ricerca', 'plus', 'btn primary') : ''}</div></header>`;
  if (!d.agents.length) return heading + gettingStarted(s);
  return `${heading}${pulse(s, archive)}
    <div class="today-layout"><div class="today-main">${todayPanel(s)}</div>
    <aside class="today-side">
      <section class="panel side-panel overview-ranked">${panelHeading('Da approfondire', '', '<a href="#properties" class="text-link">Archivio</a>')}
        ${ranked.length ? '<div class="rank-list">' + ranked.map(rankedProperty).join('') + '</div>' : empty('Nessun immobile da valutare', 'Esegui una ricerca o importa annunci.')}</section>
      <section class="panel side-panel">${panelHeading('Ricerche', '', '<a href="#agents" class="text-link">Gestisci</a>')}
        ${d.agents.slice(0, 5).map(a => agentRow(a, editor)).join('')}</section>
      <section class="panel side-panel">${panelHeading('Novità', '', '<a href="#inbox" class="text-link">Inbox</a>')}
        ${recent.length ? '<div class="event-list">' + recent.map(n => `<button data-action="notification-open" data-id="${e(n.id)}"><span class="event-icon">${icon(n.kind === 'price_change' ? 'chart' : n.kind === 'source_blocked' ? 'warning' : 'building')}</span><span><strong>${e(n.body || n.title)}</strong><small>${e(n.body ? n.title : '')}</small></span><time>${relative(n.created_at)}</time></button>`).join('') + '</div>' : '<p class="side-empty">Nessun evento recente.</p>'}</section>
    </aside></div>
    ${points ? `<section class="panel overview-map">${panelHeading('Mappa', `${num(points)} posizioni dichiarate dalle fonti`, '')}<div id="overview-map">${mapPanel(d.properties, s.mapMode || 'italy')}</div></section>` : ''}`;
}
