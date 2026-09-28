import {todayPanel} from './decision-ui.js';
import {icon} from './icons.js';
import {e, num, amount, relative, activeRun} from './utils.js';
import {action, propertyThumb, panelHeading} from './ui.js';
import {mapPanel} from './map.js';
import {marketCell} from './signals-ui.js';
import {state as searchState} from './agents-ui.js';

// First run: three steps, the current one carries its action. Shown until the first search exists.
function gettingStarted(s) {
  const hasSource = s.data.sources.length > 0, admin = s.user.role === 'admin';
  const current = hasSource ? 2 : 1;
  const act = !admin ? (current === 1 ? '<a class="btn" href="#sources">Visualizza le fonti</a>' : '')
    : current === 1 ? action('new-source', 'Collega fonte', 'plus', 'btn primary') + action('import', 'Importa file', 'upload', 'btn')
    : action('new-agent', 'Nuova ricerca', 'plus', 'btn primary');
  const step = (n, title, text, href='') => {
    const state = n < current ? 'done' : n === current ? 'current' : '';
    const label = href && n !== current ? `<a href="${href}">${title}</a>` : title;
    return `<li class="${state}"><span class="start-mark" aria-hidden="true">${n < current ? icon('check') : n}</span><div><strong>${label}</strong><small>${text}</small>${n === current && act ? `<div class="start-actions">${act}</div>` : ''}</div></li>`;
  };
  return `<section class="start-card"><p class="start-kicker">Per iniziare</p><h2>${hasSource ? 'Crea la prima ricerca' : 'Collega la prima fonte'}</h2>
    <p class="start-lead">Scout legge i siti delle agenzie come faresti tu e porta qui chi contattare, con i dati per valutare.</p>
    <ol class="start-steps">${step(1, 'Collega una fonte', 'Una rete di agenzie pronta o un file da importare', '#sources')}${step(2, 'Crea una ricerca', 'Zona, budget e istruzioni', '#agents')}${step(3, 'Esegui la ricerca', 'I contatti da chiamare compaiono in questa pagina')}</ol></section>`;
}

function rankedProperty(p) {
  return `<button class="rank-property" data-action="property" data-id="${e(p.id)}">
    ${p.images?.length?propertyThumb(p, 'rank-thumb'):''}<span class="rank-text"><strong>${e(p.title)}</strong>
    <span>${[p.city,p.zone].filter(Boolean).map(e).join(' · ')}${p.price!=null?` · <span class="rank-price">${amount(p.price,p.currency)}</span>`:''}</span></span><span class="rank-result">${marketCell(p,{compact:true})}</span></button>`;
}

// Same status as the Ricerche page badge, told by the dot alone (tooltip and screen-reader text carry the words);
// the meta line is only what was found and when the last run ended.
function agentRow(a, editor) {
  const run=a.last_run, running=activeRun(run), [status,badgeTone]=searchState(a);
  const tone=running?'live':badgeTone==='warning'?'warn':badgeTone==='neutral'?'idle':'ok';
  return `<div class="agent-operation"><span class="agent-state ${tone}" title="${e(status)}" aria-hidden="true"></span><div>
    <button class="plain-link" data-action="edit-agent" data-id="${e(a.id)}"><span class="sr-only">${e(status)}: </span>${e(a.name)}</button>
    <small><span class="agent-found">${num(a.qualified)} nei criteri</span>${run?` · ${relative(run.finished_at || run.created_at)}`:''}</small></div>
    ${editor ? action('run-agent', '', running ? 'pulse' : 'play', 'icon-button', `data-id="${e(a.id)}" aria-label="${running?'Mostra':'Esegui'} ${e(a.name)}"`) : ''}</div>`;
}

// Novità: a marker column that stays quiet. Only a source problem earns a tinted icon; unread news is a dot.
function eventRow(n) {
  const warn = n.kind === 'source_blocked';
  return `<button class="${n.read_at ? '' : 'is-unread'}" data-action="notification-open" data-id="${e(n.id)}"><span class="event-mark ${warn ? 'is-warning' : ''}" aria-hidden="true">${warn ? icon('warning') : ''}</span><span>${n.read_at ? '' : '<span class="sr-only">Non letta: </span>'}<strong>${e(n.body || n.title)}</strong><small>${e(n.body ? n.title : '')}</small></span><time>${relative(n.created_at)}</time></button>`;
}

// Four doors, each already filtered: what moved in the market and what the team holds.
// The call queue has its own count right below, so it is not repeated here.
function pulse(archive) {
  const tile=(value,labelText,detail,attrs,tag='button')=>`<${tag} class="pulse-tile" ${attrs}><span class="pulse-label">${labelText}</span><strong>${value==null?'—':num(value)}</strong><small>${detail}</small></${tag}>`;
  return `<section class="pulse" aria-label="Sintesi">
    ${tile(archive?.new_7d,'Nuovi in 7 giorni','Prima rilevazione','data-action="open-focus" data-focus="new"')}
    ${tile(archive?.reduced,'Con ribassi','Prezzo sceso dalla prima rilevazione','data-action="open-focus" data-focus="reduced"')}
    ${tile(archive?.below_benchmark,'Sotto prezzo di zona','Almeno il 10% sotto','data-action="open-focus" data-focus="below"')}
    ${tile(archive?.in_work,'In lavorazione','Pratiche aperte del team','href="#pipeline"','a')}
  </section>`;
}

// One line of scale and freshness: how much of the market is watched and when it was last read.
function todaySummary(s,total){
  const runs=s.data.agents.map(a=>a.last_run?.finished_at).filter(Boolean).sort();
  const parts=[];
  if(total)parts.push(`${num(total)} annunci monitorati`);
  if(runs.length)parts.push(`ultima ricerca ${relative(runs.at(-1))}`);
  return parts.length?`<p class="today-summary">${parts.join(' · ')}</p>`:'';
}

function todayDate() {
  const text=new Date().toLocaleDateString('it-IT',{weekday:'long',day:'numeric',month:'long'});
  return text.charAt(0).toUpperCase()+text.slice(1);
}

export function liveOverview(s) {
  const d = {...s.data,properties:s.data.properties.filter(p=>!['sold','rented','withdrawn','review'].includes(p.availability))};
  const archive = s.insights?.archive;
  const total = archive?.total ?? d.stats.properties;
  // The queue already lists its assets: the side list shows the next best ones, not the same five again.
  const queued = new Set([...(s.ops?.today?.call||[]),...(s.ops?.today?.verify||[])].map(p=>p.id));
  const ranked = d.properties.filter(p => p.priority?.score != null && !queued.has(p.id) && !['discarded', 'acquired'].includes(p.review_status)).sort((a,b)=>(b.priority?.score||0)-(a.priority?.score||0)).slice(0, 5);
  const editor = s.user.role !== 'viewer';
  const recent = s.notifications.slice(0, 4);
  const points = d.properties.filter(p => p.latitude != null && p.longitude != null).length;
  const heading = `<header class="today-heading"><div><p class="today-date">${todayDate()}</p><h1>Oggi</h1>${d.agents.length?todaySummary(s,total):''}</div><div class="heading-actions">${editor && d.agents.length ? action('new-agent', 'Nuova ricerca', 'plus', 'btn') : ''}</div></header>`;
  if (!d.agents.length) return heading + gettingStarted(s);
  return `${heading}${pulse(archive)}
    <div class="today-layout"><div class="today-main">${todayPanel(s)}</div>
    <aside class="today-side">
      <section class="panel side-panel overview-ranked">${panelHeading('Da approfondire', 'Scarto vs prezzo di zona', '<a href="#properties" class="text-link">Archivio</a>')}
        ${ranked.length ? '<div class="rank-list">' + ranked.map(rankedProperty).join('') + '</div>' : '<p class="side-empty">Nessun altro immobile da valutare.</p>'}</section>
      <section class="panel side-panel">${panelHeading('Ricerche', '', '<a href="#agents" class="text-link">Gestisci</a>')}
        ${d.agents.slice(0, 5).map(a => agentRow(a, editor)).join('')}</section>
      <section class="panel side-panel">${panelHeading('Novità', '', '<a href="#inbox" class="text-link">Inbox</a>')}
        ${recent.length ? '<div class="event-list">' + recent.map(eventRow).join('') + '</div>' : '<p class="side-empty">Nessun evento recente.</p>'}</section>
    </aside></div>
    ${points ? `<section class="panel overview-map">${panelHeading('Mappa', `${num(points)} posizioni dichiarate dalle fonti`, '')}<div id="overview-map">${mapPanel(d.properties, s.mapMode || 'italy')}</div></section>` : ''}`;
}
