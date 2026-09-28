import {marketCell,ageCell} from './signals-ui.js';
import {brokersView} from './brokers-ui.js';
import {sourceDirectory} from './sources-ui.js';
import {agentDirectory,frequency} from './agents-ui.js';
import {qualityView} from './quality-ui.js';
import {catalogView,catalogPlaceholder} from './catalog-ui.js';
import {action,badge,empty,notice,pageHeading,propertyThumb} from './ui.js';
import {liveOverview} from './overview.js';
import {insightsView} from './insights.js';
import {pipelineView,inboxView,marketView,savedViewBar,operationsSettings,stages} from './product-ui.js';
import {icon,mark} from './icons.js';
import {grouped} from './table-ui.js';
import {availabilityTag,e,label,reviewLabel,num,euro, amount,relative,stamp,initials,activeRun,tone,strategyTags,score,discount,selectOptions,engineName} from './utils.js';

export const pages = {
  overview:['grid','Oggi'], properties:['building','Immobili'], brokers:['user','Broker'], pipeline:['board','Lavorazione'], agents:['agent','Ricerche'],
  sources:['layers','Fonti e importazioni'], market:['chart','Prezzi di zona'], insights:['spark','Segnali'], quality:['quality','Qualità dati'], inbox:['bell','Inbox'], activity:['pulse','Esecuzioni'], settings:['settings','Impostazioni'],
};
export {badge,empty,notice,pageHeading} from './ui.js';
export function sourceMode() { return false; }
export function shownAgents(s) {return s.data.agents;}
export function shownSources(s) {return s.data.sources;}

export function loginView() {
  return `<div class="login-layout">
    <header class="login-top"><a class="brand" href="/">${mark}<span>vedra<span class="brand-dot">.</span></span></a></header>
    <main class="login-panel" id="main" tabindex="-1"><div class="login-box"><h1>Accedi</h1><p>Usa l’email e la password del tuo account.</p>
      <form id="login-form"><label>Email<input name="email" type="email" autocomplete="username" required placeholder="nome@azienda.it"></label><label>Password<div class="password-wrap"><input name="password" type="password" autocomplete="current-password" required>${action('show-password','', 'eye','icon-button','type="button" aria-label="Mostra password"')}</div></label><div class="form-error" id="login-error" role="alert"></div><button type="submit" class="btn primary full">Accedi al workspace</button></form>
    </div></main>
    <footer class="version">Vedra · Workspace privato</footer>
  </div>`;
}

const primaryPages=['overview','properties','brokers','agents','pipeline'];
// The mobile drawer slides in only when it opens, not on every background re-render while open.
let navWasOpen=false;

export function shell(s) {
  const user=s.user, healthy=Boolean(s.ops?.worker?.healthy);
  const scheduled=s.data.agents.filter(a=>a.active&&a.interval_minutes).length;
  const entering=s.mobileNav&&!navWasOpen;navWasOpen=s.mobileNav;
  const workspaceName=s.ops?.workspace?.name||'Workspace';
  return `<div class="workspace ${s.mobileNav?'nav-open':''} ${entering?'nav-entering':''}" data-page="${e(s.page)}">
    <aside class="sidebar"><a class="brand" href="#overview">${mark}<span>vedra<span class="brand-dot">.</span></span></a>
      <div class="workspace-switch" title="Workspace privato"><span class="workspace-initial">${e(initials(workspaceName))}</span><div><strong>${e(workspaceName)}</strong></div><span class="little-lock" aria-label="Privato">${icon('lock')}</span></div>
      <nav aria-label="Navigazione principale">${primaryPages.map(key=>navLink(key,s)).join('')}</nav><details class="nav-management plain" ${!primaryPages.includes(s.page)?'open':''}><summary>Gestione</summary><nav aria-label="Gestione">${Object.keys(pages).filter(key=>![...primaryPages,'settings'].includes(key)).map(key=>navLink(key,s)).join('')}</nav></details>
      <div class="sidebar-spacer"></div><div class="engine-card" role="status"><span class="status-dot ${healthy?'green':'amber'}"></span><div><strong>${healthy?'Servizio attivo':'Servizio da verificare'}</strong><span>${scheduled?`${scheduled} ${scheduled===1?'ricerca periodica':'ricerche periodiche'}`:'Nessuna ricerca periodica'}</span></div></div>
      ${navLink('settings',s)}
      <div class="profile"><span class="avatar">${e(initials(user.name))}</span><div><strong>${e(user.name)}</strong><span>${e({admin:'Amministratore',analyst:'Analista',viewer:'Sola lettura'}[user.role])}</span></div>${action('logout','', 'logout','icon-button','aria-label="Esci dal workspace" title="Esci"')}</div>
    </aside>
    <button class="nav-scrim" data-action="mobile-menu" aria-label="Chiudi navigazione"></button>
    <div class="workspace-main"><header class="topbar"><div class="breadcrumb">${action('mobile-menu','', 'menu','icon-button mobile-only','aria-label="Apri navigazione" aria-expanded="'+Boolean(s.mobileNav)+'"')}</div><div class="topbar-actions"><form id="global-search" class="global-search" role="search">${icon('search')}<input id="global-query" name="q" aria-label="Cerca immobili" placeholder="Cerca immobili" autocomplete="off" value="${e(s.filters.q)}"><button type="submit" class="icon-button" aria-label="Cerca">${icon('arrow')}</button></form><a href="#inbox" class="icon-button inbox-shortcut" aria-label="${s.ops?.unread?'Inbox, notifiche non lette':'Inbox'}" title="Inbox">${icon('bell')}${s.ops?.unread?'<span class="notification-indicator"></span>':''}</a>${action('refresh','', 'refresh',`icon-button ${s.busy?'rotating':''}`,'aria-label="Aggiorna dati" title="Aggiorna dati"')}${action('theme','',document.documentElement.dataset.theme==='dark'?'sun':'moon','icon-button','aria-label="Cambia tema" title="Cambia tema"')}<span class="header-divider"></span><span class="header-avatar" title="${e(user.name)}">${e(initials(user.name))}</span></div></header>
      <main class="main-content" id="main" tabindex="-1"><div id="page">${s.data.has_more&&s.page!=='properties'?'<div class="notice info">Sintesi calcolata su 2.000 annunci; Immobili e Segnali consultano l’intero archivio.</div>':''}${renderPage(s)}</div></main>
    </div>
  </div>`;
}

export function renderPage(s) {
  return ({brokers:brokersView,overview:liveOverview,insights:insightsView,pipeline:pipelineView,inbox:inboxView,market:marketView,properties:propertiesView,agents:agentsView,sources:sourcesView,quality:qualityView,activity:activityView,settings:settingsView}[s.page] || liveOverview)(s);
}
function metric(title,value,detail,ico,extra='') {
  return `<section class="metric-card ${extra}"><div class="metric-label">${e(title)}<span class="metric-icon">${icon(ico)}</span></div><div class="metric-value">${value}</div><div class="metric-detail">${detail}</div></section>`;
}
const hasPhoto=p=>Array.isArray(p.images)&&p.images.length>0;
const place=p=>[p.city,p.zone].filter(Boolean).map(e).join(' · ')||'Località non indicata';
function size(p){
  const parts=[p.surface==null?'Superficie n.d.':`${num(p.surface)} m²`];
  if(p.price_sqm!=null)parts.push(`${amount(Math.round(p.price_sqm),p.currency)}/m²`);
  return parts.join(' · ');
}
const star=(s,p)=>`<button class="icon-button star-button ${p.starred?'selected':''}" data-action="star" data-id="${e(p.id)}" aria-label="${p.starred?'Rimuovi':'Aggiungi'} preferito" aria-pressed="${Boolean(p.starred)}" ${s.user.role==='viewer'?'disabled':''}>${icon('star')}</button>`;
const selectBox=(s,p)=>`<input type="checkbox" class="catalog-check" id="select-${e(p.id)}" data-select-property="${e(p.id)}" ${s.selected.has(p.id)?'checked':''} aria-label="Seleziona ${e(p.title)}">`;
// Page checkbox: checked when the whole page is selected, "mixed" when only part of it is.
function pageBox(s,rows,text=''){
  const count=rows.filter(p=>s.selected.has(p.id)).length;
  const all=rows.length>0&&count===rows.length;
  return `<input type="checkbox" class="catalog-check ${count&&!all?'mixed':''}" id="select-page-all" data-action="select-page" ${all?'checked':''} ${s.catalog.loading||s.catalog.error||!rows.length?'disabled':''} aria-label="${all?'Deseleziona':'Seleziona'} gli annunci della pagina${count&&!all?` · ${count} di ${rows.length} selezionati`:''}">${text}`;
}

function tableRows(s, rows, selectable=false) {
  // A thumbnail column only earns its width when the page has photos to show.
  const photos=rows.some(hasPhoto);
  return rows.map(p=>`<tr data-property-row="${e(p.id)}" class="${s.selected.has(p.id)?'is-selected':''}">${selectable?`<td class="check-cell">${selectBox(s,p)}</td>`:''}<td class="property-cell"><button class="property-link" data-action="property" data-id="${e(p.id)}" title="${e(p.title)}">${photos?(hasPhoto(p)?propertyThumb(p,'property-mini table-thumb'):`<span class="property-mini table-thumb empty" aria-hidden="true">${icon('building')}</span>`):''}<span><strong>${e(p.title)}</strong><span class="property-location">${place(p)}${availabilityTag(p,true)}</span></span></button></td><td class="numeric price-cell"><strong>${amount(p.price,p.currency)}</strong><small>${size(p)}</small></td><td class="numeric market-cell">${marketCell(p,{compact:true})}</td><td class="numeric age-cell">${ageCell(p)}</td><td class="strategy-cell"><div class="strategy-group">${strategyTags(p,2)}</div></td><td class="star-cell">${star(s,p)}</td></tr>`).join('');
}
function sortHeader(s,key,text,hint){
  const active=s.filters.sort===key;
  return `<th class="numeric sortable" ${active?'aria-sort="'+(key==='price'?'ascending':'descending')+'"':''}><button id="sort-${key}" data-action="catalog-sort" data-sort="${key}" title="${active?'Torna all’ordine consigliato':hint}">${e(text)}<span class="sort-mark ${active?'on':''}" aria-hidden="true">${icon('down')}</span></button></th>`;
}
function table(s, rows, selectable=false) {
  if (!rows.length) return empty('Nessuna opportunità in questa vista','Modifica i filtri oppure acquisisci il primo campione di dati.');
  return `<div class="table-scroll"><table class="properties-table"><thead><tr>${selectable?`<th class="check-cell">${pageBox(s,rows)}</th>`:''}<th>Immobile</th>${sortHeader(s,'price','Prezzo','Ordina per prezzo, dal più basso')}<th class="numeric" title="Prezzo richiesto al m² rispetto ai comparabili nello stesso stato o all’OMI, se indicati; altrimenti al prezzo di zona">vs mercato</th>${sortHeader(s,'listed','Online da','Ordina dal più vecchio online')}<th class="strategy-cell">Strategia</th><th class="star-cell"><span class="sr-only">Preferito</span></th></tr></thead><tbody>${tableRows(s,rows,selectable)}</tbody></table></div>`;
}
function card(s,p){
  return `<article class="property-card ${hasPhoto(p)?'with-photo':''} ${s.selected.has(p.id)?'is-selected':''}"><div class="property-art"><label class="card-select">${selectBox(s,p)}<span class="sr-only">Seleziona</span></label>${propertyThumb(p,'card-thumb')}${star(s,p)}</div><div class="property-card-body"><button class="card-title" data-action="property" data-id="${e(p.id)}">${e(p.title)}</button><div class="property-card-place">${place(p)}${availabilityTag(p,true)}</div><div class="property-card-price"><strong>${amount(p.price,p.currency)}</strong><span>${size(p)}</span></div><div class="card-signals"><span class="card-market">${marketCell(p,{compact:true})}</span><span class="card-age">${p.signals?.days_listed!=null?'<small>Online da</small>':''}${ageCell(p)}</span></div>${strategyTags(p,2)?`<div class="strategy-group">${strategyTags(p,2)}</div>`:''}</div></article>`;
}
export function propertyResults(s) {
  if(s.catalog){const placeholder=catalogPlaceholder(s);if(placeholder)return placeholder;}
  const rows=s.catalog.items;
  // Seven numeric columns do not fit a phone: cards carry the same data and selection.
  const phone=typeof matchMedia==='function'&&matchMedia('(max-width: 700px)').matches;
  if(s.layout==='grid'||phone)return rows.length?`<div class="grid-head"><label>${pageBox(s,rows,'<span>Seleziona pagina</span>')}</label><span class="grid-count">${s.catalog.loading?'Aggiornamento…':`${num(s.catalog.total)} ${s.catalog.total===1?'annuncio':'annunci'}`}</span></div><div class="property-grid">${rows.map(p=>card(s,p)).join('')}</div>`:empty('Nessun immobile corrisponde ai filtri','Prova ad allargare la ricerca.');
  return table(s,rows,true);
}
export function propertiesView(s) {
  return catalogView(s,propertyResults(s),savedViewBar(s));
}

export function agentsView(s) {
  // Online searches come first: they are the ones that find new listings.
  return agentDirectory(s,shownAgents(s));
}

export function sourcesView(s) {return sourceDirectory(s,shownSources(s));}


// Every row says how it started, so the table keeps one rhythm; a scheduled run names its cadence.
const TRIGGERS={manual:'Avvio manuale',schedule:'Programmata',external:'Avvio esterno',seed:'Dati iniziali'};
function trigger(r,agents){
  if(r.trigger!=='schedule')return TRIGGERS[r.trigger]||'Avvio non registrato';
  const minutes=agents.find(a=>a.id===r.agent_id)?.interval_minutes;
  return minutes?`Programmata · ${frequency(minutes).toLowerCase()}`:'Programmata';
}
export function activityView(s) {
  const runs=s.data.runs;
  return `${pageHeading('','Esecuzioni','')}
    ${runs.length?`<p class="page-summary">Ultime ${grouped(runs.length)} esecuzioni delle ricerche</p>
    <section class="pg-surface activity-panel"><div class="pg-scroll"><table class="pg-table activity-table"><thead><tr><th scope="col">Ricerca</th><th scope="col">Esito</th><th scope="col">Motore</th><th scope="col" class="num">Acquisiti</th><th scope="col" class="num">Nuovi</th><th scope="col" class="num">Errori</th><th scope="col" class="num">Avvio</th><th scope="col"><span class="sr-only">Dettagli</span></th></tr></thead><tbody>${runs.map(r=>`<tr class="is-link"><td><button class="pg-link" data-action="run-detail" data-id="${e(r.id)}">${e(r.agent_name)}</button><small>${e(trigger(r,s.data.agents))}</small></td><td>${badge(label(r.status),tone(r.status))}</td><td class="pg-muted">${engineName(r.runtime)}</td><td class="num">${grouped(r.stats.processed||0)}</td><td class="num">${grouped(r.stats.new||0)}</td><td class="num ${r.stats.errors?'danger-text':'pg-zero'}">${grouped(r.stats.errors||0)}</td><td class="num pg-muted">${stamp(r.created_at)}</td><td class="pg-chevron" aria-hidden="true">${icon('chevron')}</td></tr>`).join('')}</tbody></table></div></section>`
    :`<section class="pg-surface">${empty('Nessuna esecuzione','Avvia una ricerca: qui compariranno esito, annunci acquisiti ed errori.','<a href="#agents" class="btn">Vai alle ricerche</a>','clock')}</section>`}`;
}

// Settings share one layout: a titled section, then label/value rows; actions sit in the section header.
const ROLES={admin:'Amministratore',analyst:'Analista',viewer:'Sola lettura'};
export const settingRows=rows=>`<dl class="set-rows">${rows.map(([k,v])=>`<div><dt>${e(k)}</dt><dd>${v}</dd></div>`).join('')}</dl>`;
export const settingHead=(title,text,trailing='')=>`<div class="pg-head"><div><h2>${e(title)}</h2>${text?`<p>${text}</p>`:''}</div>${trailing?`<div class="set-actions">${trailing}</div>`:''}</div>`;

// Technical detail for administrators: allowed domains, browser, scheduler, storage.
function accessSettings(s){
  const r=s.data.runtime;
  return `<section class="pg-surface settings-panel set-section">${settingHead('Accesso ai dati','Ogni dominio va autorizzato in <code>LIVE_ALLOWED_DOMAINS</code>; il permesso della fonte resta nella sua configurazione.')}
    ${settingRows([['Browser opzionale',r.browser_enabled?'Abilitato':'Disabilitato'],['Scheduler del workspace',r.scheduler_enabled?'Attivo':'Disattivato'],['Persistenza',`${r.database==='postgres'?'PostgreSQL':'SQLite'} e snapshot locali`],['Ambito','Singolo workspace privato'],['Estensione Vedra Capture','In Chrome apri <code>chrome://extensions</code>, attiva Modalità sviluppatore e carica la cartella <code>extension</code> di Vedra.']])}
    <p class="pg-note">Per avviare le ricerche dal cron di Hermes imposta la ricerca su Manuale: un solo scheduler deve avviare il lavoro.</p></section>`;
}
function aiSettings(s){
  const admin=s.user.role==='admin',r=s.data.runtime,configured=r.ai_configured||r.hermes_configured;
  return `<section class="pg-surface settings-panel set-section ai-settings">${settingHead('Modello AI','Senza modello restano attive le regole.',`<span class="pg-pill set-status ${configured?'is-on':''}"><i aria-hidden="true"></i>${configured?'Configurato':'Non configurato'}</span>`)}
      ${settingRows([['Modello',r.ai_configured?`<code>${e(r.ai_model)}</code>`:'Nessun modello configurato'],['Configurazione','<code>AI_API_BASE_URL</code> <code>AI_API_KEY</code> <code>AI_MODEL</code> nel file <code>.env</code>, poi riavvia il servizio']])}
      ${admin&&configured?`<div class="set-foot">${r.ai_configured?action('ai-test','Verifica modello','pulse','btn'):''}${r.hermes_configured?action('runtime-test','Verifica Hermes','pulse','btn'):''}</div>`:''}<div id="runtime-result"></div></section>`;
}

// Vedra Capture: the team browses portals themselves and sends listings with one click.
function editorCapture(s){
  if(s.user.role==='viewer')return '';
  const tokens=s.captureTokens;
  return `<section class="pg-surface settings-panel set-section capture-settings">${settingHead('Vedra Capture','Da immobiliare.it, idealista o qualsiasi sito: un clic e l’annuncio arriva in Vedra, dove Scout lo legge e lo confronta con il mercato.',action('capture-token-new','Collega un browser','plus','btn primary'))}
    <ol class="capture-steps"><li><strong>Installa</strong><span>Chiedi al tuo referente tecnico di aggiungere l’estensione Vedra a Chrome.</span></li><li><strong>Collega</strong><span>Premi Collega un browser e incolla il codice nell’estensione.</span></li><li><strong>Invia</strong><span>Su un annuncio premi l’icona Vedra o <span class="kbd-combo"><kbd>Alt</kbd> <kbd>Shift</kbd> <kbd>V</kbd></span>.</span></li></ol>
    <div class="capture-tokens">${tokens==null?'<p class="pg-note">Caricamento…</p>':tokens.length?tokens.map(t=>`<div class="capture-token"><span><strong>${e(t.label)}</strong><small>Collegato ${stamp(t.created_at)}${t.last_used_at?` · ultimo invio ${relative(t.last_used_at)}`:' · nessun invio'}</small></span>${action('capture-token-delete','Scollega','','btn pg-ghost',`data-id="${e(t.id)}"`)}</div>`).join(''):'<p class="pg-note">Nessun browser collegato.</p>'}</div></section>`;
}

function accountSettings(s,wide){
  const user=s.user;
  return `<section class="pg-surface settings-panel set-section account-settings ${wide?'set-wide':''}">${settingHead('Account','',action('password','Cambia password','lock','btn'))}
    ${settingRows([['Nome',e(user.name)],['Email',e(user.email||'—')],['Ruolo',e(ROLES[user.role]||user.role)]])}</section>`;
}

// The technical disclosure keeps its state across background refreshes, like the card menus.
let technicalOpen=false;
if(typeof document!=='undefined')document.addEventListener('toggle',event=>{if(event.target.matches?.('details.set-advanced')&&event.target.isConnected)technicalOpen=event.target.open;},true);

// Client-facing sections first; what only an installer needs waits in one closed disclosure.
export function settingsView(s) {
  const admin=s.user.role==='admin';
  const team=admin?`<section class="pg-surface settings-panel set-section team-settings">${settingHead('Team','Gli account nascono con una password iniziale; nessuna email viene inviata.',action('new-user','Invita un utente','plus','btn'))}
    <div id="users-list">${s.users?`<ul class="users-list">${s.users.map(u=>`<li class="user-row"><span class="avatar">${e(initials(u.name))}</span><span><strong>${e(u.name)}</strong><small>${e(u.email)}</small></span><span class="pg-pill">${e(ROLES[u.role]||u.role)}</span></li>`).join('')}</ul>`:'<p class="pg-note">Caricamento utenti…</p>'}</div></section>`:'';
  return `${pageHeading('','Impostazioni','')}
    <div class="set-grid">
    ${editorCapture(s)}
    ${accountSettings(s,!team)}
    ${team}
    <details class="settings-advanced set-advanced" ${technicalOpen||s.settingsAdvanced?'open':''}><summary>Configurazione tecnica<span class="set-intro">Per chi installa Vedra. Non serve per l’uso quotidiano.</span></summary><div class="set-stack">${aiSettings(s)}${operationsSettings(s)}${accessSettings(s)}</div></details>
    </div>`;
}

function navLink(key,s){const [ic,text]=pages[key];return `<a href="#${key}" class="nav-link ${s.page===key?'active':''}" ${s.page===key?'aria-current="page"':''}>${icon(ic)}<span>${text}</span></a>`;}
