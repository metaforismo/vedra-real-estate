import {marketCell,ageCell} from './signals-ui.js';
import {brokersView} from './brokers-ui.js';
import {sourceDirectory} from './sources-ui.js';
import {qualityView} from './quality-ui.js';
import {catalogView,catalogPlaceholder} from './catalog-ui.js';
import {action,badge,empty,notice,pageHeading,propertyThumb} from './ui.js';
import {liveOverview} from './overview.js';
import {insightsView} from './insights.js';
import {pipelineView,inboxView,marketView,savedViewBar,operationsSettings,stages} from './product-ui.js';
import {icon,mark} from './icons.js';
import {availabilityTag,e,label,reviewLabel,num,euro, amount,relative,stamp,initials,activeRun,tone,strategyTags,score,discount,selectOptions} from './utils.js';

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
    <main class="login-panel" id="main" tabindex="-1"><div class="login-box"><h2>Accedi</h2>
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
function tableRows(s, rows, selectable=false) {
  return rows.map(p=>`<tr data-property-row="${e(p.id)}">${selectable?`<td class="check-cell"><input type="checkbox" id="select-${e(p.id)}" data-select-property="${e(p.id)}" ${s.selected.has(p.id)?'checked':''} aria-label="Seleziona ${e(p.title)}"></td>`:''}<td class="property-cell"><button class="property-link" data-action="property" data-id="${e(p.id)}">${Array.isArray(p.images)&&p.images.length?propertyThumb(p,'property-mini table-thumb'):`<span class="property-mini type-${e(p.property_type)}">${icon('building')}</span>`}<span><strong>${e(p.title)}</strong><span class="property-location">${[p.city,p.zone].filter(Boolean).map(e).join(' · ')||'Località n.d.'} ${availabilityTag(p,true)}</span></span></button></td><td class="numeric"><strong>${amount(p.price,p.currency)}</strong><small>${p.surface==null?'Superficie n.d.':num(p.surface)+' m²'}${p.price_sqm!=null?` · ${amount(p.price_sqm,p.currency)}/m²`:''}</small></td><td class="market-cell">${marketCell(p)}</td><td class="age-cell">${ageCell(p)}</td><td><div class="strategy-group">${strategyTags(p,2)}</div></td><td class="right"><button class="icon-button star-button ${p.starred?'selected':''}" data-action="star" data-id="${e(p.id)}" aria-label="${p.starred?'Rimuovi':'Aggiungi'} preferito" ${s.user.role==='viewer'?'disabled':''}>${icon('star')}</button></td></tr>`).join('');
}
function table(s, rows, selectable=false) {
  if (!rows.length) return empty('Nessuna opportunità in questa vista','Modifica i filtri oppure acquisisci il primo campione di dati.');
  return `<div class="table-scroll"><table class="properties-table"><thead><tr>${selectable?'<th class="check-cell"><span class="sr-only">Confronta</span></th>':''}<th>IMMOBILE</th><th class="numeric">PREZZO</th><th title="Prezzo richiesto al m² rispetto agli annunci comparabili nello stesso stato, all’OMI o al benchmark">VS MERCATO</th><th title="Da quanto è pubblicato e ribassi osservati">ONLINE DA</th><th>STRATEGIA</th><th><span class="sr-only">Preferito</span></th></tr></thead><tbody>${tableRows(s,rows,selectable)}</tbody></table></div>`;
}
export function propertyResults(s) {
  if(s.catalog){const placeholder=catalogPlaceholder(s);if(placeholder)return placeholder;}
  const rows=s.catalog.items;
  // Seven numeric columns do not fit a phone: cards carry the same data and selection.
  const phone=typeof matchMedia==='function'&&matchMedia('(max-width: 700px)').matches;
  if(s.layout==='grid'||phone)return rows.length?`<div class="property-grid">${rows.map(p=>`<article class="property-card"><div class="property-art type-${e(p.property_type)}"><label class="card-select"><input type="checkbox" id="select-${e(p.id)}" data-select-property="${e(p.id)}" ${s.selected.has(p.id)?'checked':''} aria-label="Seleziona ${e(p.title)}"><span>Seleziona</span></label>${propertyThumb(p,'card-thumb')}<button class="icon-button star-button ${p.starred?'selected':''}" data-action="star" data-id="${e(p.id)}" aria-label="${p.starred?'Rimuovi':'Aggiungi'} preferito" aria-pressed="${Boolean(p.starred)}" ${s.user.role==='viewer'?'disabled':''}>${icon('star')}</button></div><div class="property-card-body"><div class="property-card-place">${icon('pin')}${[p.city,p.zone].filter(Boolean).map(e).join(' · ')||'Località n.d.'} ${availabilityTag(p)}</div><button class="card-title" data-action="property" data-id="${e(p.id)}">${e(p.title)}</button><div class="property-card-price"><strong>${amount(p.price,p.currency)}</strong><span>${num(p.surface)} m²</span></div><div class="strategy-group">${strategyTags(p)}</div><div class="property-card-bottom"><div class="card-benchmark">${marketCell(p)}</div><button class="icon-button" data-action="property" data-id="${e(p.id)}" aria-label="Apri scheda">${icon('arrow')}</button></div></div></article>`).join('')}</div>`:empty('Nessun immobile corrisponde ai filtri','Prova ad allargare la ricerca.');
  return table(s,rows,true);
}
export function propertiesView(s) {
  return catalogView(s,propertyResults(s),savedViewBar(s));
}

export function agentsView(s) {
  const agents=[...shownAgents(s)].sort((a,b)=>Number(!!b.criteria.online_discovery)-Number(!!a.criteria.online_discovery)), canEdit=s.user.role!=='viewer';
  return `${pageHeading('','Ricerche','',canEdit?action('new-agent','Nuova ricerca','plus','btn primary'):'')}
    <div class="agent-grid">${agents.map((a,i)=>`<article class="agent-card"><div class="agent-card-head"><span class="agent-symbol large">${icon(a.runtime==='scout'||a.criteria.online_discovery?'search':'layers')}</span>${badge(activeRun(a.last_run)?label(a.last_run.status):a.last_run?.status==='failed'?'Verifica fallita':a.last_run?.status==='partial'?'Verifica parziale':a.active?(a.interval_minutes?'Programmato':'Manuale'):'In pausa',['failed','partial'].includes(a.last_run?.status)?'warning':a.active?'success':'neutral')}<button class="icon-button" data-action="edit-agent" data-id="${e(a.id)}" aria-label="Configura ${e(a.name)}">${icon(canEdit?'edit':'eye')}</button></div><div class="agent-card-title"><h2>${e(a.name)}</h2><span>${icon('pin')} ${e(a.city)}${a.criteria.location_query?` · ${e(a.criteria.location_query)}`:''} </span><small class="agent-scope">${a.runtime==='scout'||a.criteria.online_discovery?'Cerca nuovi annunci online':'Filtra gli annunci già acquisiti'}</small></div><div class="agent-criteria"><div><span>Budget</span><strong>${a.criteria.min_price?`${euro(a.criteria.min_price,true)} – `:"Fino a "}${euro(a.criteria.max_price,true)}</strong></div><div><span>Superficie minima</span><strong>${a.criteria.min_surface?num(a.criteria.min_surface)+' m²':'Nessun minimo'}</strong></div><div><span>Strategia</span><strong>${a.criteria.strategies.length?a.criteria.strategies.map(label).join(', '):'Tutte'}</strong></div><div><span>Frequenza</span><strong>${a.interval_minutes?a.interval_minutes%60===0?a.interval_minutes===60?'Ogni ora':`Ogni ${a.interval_minutes/60} ore`:`Ogni ${num(a.interval_minutes)} min`:'Manuale'}</strong></div></div>${a.criteria.opportunity_only?'<p class="small muted">Solo sotto il prezzo di zona</p>':''}${a.criteria.contact_policy&&a.criteria.contact_policy!=='any'?`<p class="small muted">${a.criteria.contact_policy==='require_direct'?'Richiede contatto diretto dichiarato':'Priorità al contatto diretto'}</p>`:''}${a.criteria.custom_prompt?`<details class="agent-custom"><summary>Criteri personalizzati</summary><p>${e(a.criteria.custom_prompt)}</p></details>`:''}<div class="agent-outcomes"><button class="stat-button" data-action="agent-results" data-id="${e(a.id)}"><strong>${num(a.qualified)}</strong><span>nei criteri su ${num(a.total)} trovati ${icon('arrow')}</span></button><span class="runtime-label ${a.runtime==='hermes'?'hermes':''}" title="Motore di analisi">${icon(['hermes','scout'].includes(a.runtime)?'spark':'code')} ${{hermes:'Hermes',scout:'Scout',llm:'AI sull’archivio'}[a.runtime]||'Solo regole'}</span></div><div class="agent-schedule">${icon('clock')}<span>${a.last_run?`${a.last_run.status==='completed'?'Ultima ricerca':'Ultimo tentativo'} ${relative(a.last_run.finished_at||a.last_run.created_at)}`:'Mai eseguita'}${a.next_run&&a.active&&a.interval_minutes?(new Date(a.next_run)>new Date()?` · Prossima ${relative(a.next_run)}`:' · In coda'):''}</span></div><div class="agent-actions">${canEdit?`${action('run-agent',activeRun(a.last_run)?'Mostra esecuzione':'Esegui ora',activeRun(a.last_run)?'pulse':'play','btn primary',`data-id="${e(a.id)}"`)}${action('toggle-agent',a.active?'Pausa':'Riprendi',a.active?'pause':'play','btn',`data-id="${e(a.id)}"`)}`:''}${action('agent-readiness','Verifica accesso','quality','btn small-btn',`data-id="${e(a.id)}"`)}</div><div class="agent-secondary">${a.last_run?action('run-detail','Ultima esecuzione','list','text-button',`data-id="${e(a.last_run.id)}"`):''}${canEdit?action('duplicate-agent','Duplica','plus','text-button',`data-id="${e(a.id)}" title="Crea una variante con gli stessi criteri"`):''}</div></article>`).join('')}${!agents.length?empty('Nessuna ricerca',canEdit?'Crea una ricerca per definire asset, criteri e fonti.':'Le ricerche del team compariranno qui.'):''}</div>`;
}

export function sourcesView(s) {return sourceDirectory(s,shownSources(s));}


export function activityView(s) {
  return `${pageHeading('OPERATIONS','Esecuzioni','Esecuzioni, errori e risultati: ciò che è successo, non ciò che il sistema avrebbe dovuto fare.')}
    <section class="panel activity-panel">${s.data.runs.length?`<div class="table-scroll"><table class="activity-table"><thead><tr><th>AGENTE / ESECUZIONE</th><th>STATO</th><th>MOTORE</th><th>ACQUISITI</th><th>NUOVI</th><th>ERRORI</th><th>AVVIO</th><th></th></tr></thead><tbody>${s.data.runs.map(r=>`<tr><td><button class="plain-link" data-action="run-detail" data-id="${e(r.id)}">${e(r.agent_name)}</button><small>${e(r.id.slice(0,8))} · ${e({manual:'avvio manuale',schedule:'programmata',external:'trigger esterno'}[r.trigger] || r.trigger)}</small></td><td>${badge(label(r.status),tone(r.status))}</td><td><span class="runtime-label">${icon(['hermes','scout'].includes(r.runtime)?'spark':'code')}${{hermes:'Hermes',scout:'Scout',llm:'AI sull’archivio'}[r.runtime]||'Regole'}</span></td><td>${num(r.stats.processed||0)}</td><td>${num(r.stats.new||0)}</td><td class="${r.stats.errors?'danger-text':''}">${num(r.stats.errors||0)}</td><td>${stamp(r.created_at)}</td><td>${action('run-detail','','chevron','icon-button',`data-id="${e(r.id)}" aria-label="Dettagli run"`)}</td></tr>`).join('')}</tbody></table></div>`:empty('Nessuna esecuzione','Crea un agente e avvia il primo run dalla dashboard.')}</section>`;
}

// Vedra Capture: the team browses portals themselves and sends listings with one click.
// Technical detail for administrators: allowed domains, browser, scheduler, storage.
function accessSettings(s){
  return `<section class="panel settings-panel"><span class="setting-icon">${icon('quality')}</span><h2>Accesso ai dati</h2><p>Ogni dominio deve essere inserito in <code>LIVE_ALLOWED_DOMAINS</code>. Il permesso della fonte viene registrato nella sua configurazione.</p><dl class="settings-facts"><div><dt>Browser opzionale</dt><dd>${s.data.runtime.browser_enabled?'Abilitato':'Disabilitato'}</dd></div><div><dt>Scheduler del workspace</dt><dd>${s.data.runtime.scheduler_enabled?'Attivo':'Disattivato'}</dd></div><div><dt>Persistenza</dt><dd>${s.data.runtime.database==='postgres'?'PostgreSQL':'SQLite'} + snapshot locali</dd></div><div><dt>Ambito</dt><dd>Singolo workspace privato</dd></div></dl><p class="small">Per usare il cron di Hermes come trigger esterno, imposta la ricerca su Manuale: un solo scheduler deve avviare il lavoro.</p></section>`;
}

function editorCapture(s){
  if(s.user.role==='viewer')return '';
  const tokens=s.captureTokens;
  return `<section class="panel settings-panel full-settings capture-settings"><div class="section-heading"><div><h2>Vedra Capture</h2><p>Naviga immobiliare.it, idealista o qualsiasi sito come fai sempre: con un clic l’annuncio arriva in Vedra, Scout lo legge e lo confronta con il mercato.</p></div>${action('capture-token-new','Collega un browser','plus','btn primary')}</div>
    <ol class="capture-steps"><li><strong>Installa</strong><span>Chrome › <code>chrome://extensions</code> › Modalità sviluppatore › Carica estensione non pacchettizzata › cartella <code>extension</code> di Vedra.</span></li><li><strong>Collega</strong><span>Premi “Collega un browser”, copia il token e incollalo nell’estensione.</span></li><li><strong>Invia</strong><span>Su un annuncio premi l’icona Vedra o <kbd>Alt</kbd> <kbd>Shift</kbd> <kbd>V</kbd>.</span></li></ol>
    <div class="capture-tokens">${tokens==null?'<p class="small muted">Caricamento…</p>':tokens.length?tokens.map(t=>`<div class="capture-token"><span><strong>${e(t.label)}</strong><small>Creato ${stamp(t.created_at)}${t.last_used_at?` · ultimo invio ${relative(t.last_used_at)}`:' · mai usato'}</small></span>${action('capture-token-delete','Scollega','close','btn small-btn',`data-id="${e(t.id)}"`)}</div>`).join(''):'<p class="small muted">Nessun browser collegato.</p>'}</div></section>`;
}

export function settingsView(s) {
  const admin=s.user.role==='admin';
  return `${pageHeading('WORKSPACE SETTINGS','Impostazioni','Il workspace è privato. Credenziali e permessi di rete restano sul server.')}
    <div class="settings-grid"><section class="panel settings-panel"><span class="setting-icon">${icon('agent')}</span><h2>Modello AI</h2><p>Configurato sul server. Senza modello restano attive le regole.</p><div class="setting-status">${badge((s.data.runtime.ai_configured||s.data.runtime.hermes_configured)?'Configurato':'Non configurato',(s.data.runtime.ai_configured||s.data.runtime.hermes_configured)?'success':'neutral')}</div><div class="code-config">AI_API_BASE_URL<br>AI_API_KEY<br>AI_MODEL</div><p class="small">${s.data.runtime.ai_configured?"Modello: "+e(s.data.runtime.ai_model):"Nessun modello configurato."} Per cambiarlo modifica <code>.env</code> e riavvia il servizio.</p>${admin&&s.data.runtime.ai_configured?action('ai-test','Verifica modello','pulse','btn primary'):''}${admin&&s.data.runtime.hermes_configured?action('runtime-test','Verifica Hermes','pulse','btn'):''}<div id="runtime-result"></div></section>

    ${editorCapture(s)}
    <details class="settings-advanced full-settings" ${s.settingsAdvanced?'open':''}><summary>Account e sistema</summary><div class="settings-grid">${accessSettings(s)}${operationsSettings(s)}</div></details>${admin?`<section class="panel settings-panel full-settings"><div class="table-panel-heading"><div><div class="panel-label">TEAM ACCESS</div><h2>Team</h2></div>${action('new-user','Invita un utente','plus','btn')}</div><p class="small muted">Crea un account con password iniziale. Nessuna email viene inviata automaticamente.</p><div id="users-list">${s.users?`<div class="users-list">${s.users.map(u=>`<div class="user-row"><span class="avatar">${e(initials(u.name))}</span><div><strong>${e(u.name)}</strong><small>${e(u.email)}</small></div><span class="quiet-pill">${e(u.role)}</span></div>`).join('')}</div>`:'<div class="loading-line">Caricamento utenti…</div>'}</div></section>`:''}</div>`;
}

function navLink(key,s){const [ic,text]=pages[key];return `<a href="#${key}" class="nav-link ${s.page===key?'active':''}" ${s.page===key?'aria-current="page"':''}>${icon(ic)}<span>${text}</span></a>`;}
