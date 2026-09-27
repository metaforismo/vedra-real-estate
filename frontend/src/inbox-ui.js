import {e,num,stamp} from './utils.js';
import {icon} from './icons.js';
import {action,empty,pageHeading} from './ui.js';
import {inboxState} from './inbox-controller.js';
const kinds={all:'Tutti gli eventi',new_property:'Nuovi immobili',price_change:'Variazioni di prezzo',availability_change:'Disponibilità',source_blocked:'Problemi delle fonti'};
const typeNames={new_property:'Nuovo immobile',price_change:'Prezzo aggiornato',availability_change:'Disponibilità aggiornata',source_blocked:'Fonte da verificare'};
function notification(row,busy){
  const target=row.property_id?'Apri immobile':row.run_id?'Apri ricerca':'';
  const attrs=`data-id="${e(row.id)}" ${busy?'disabled':''}`;
  return `<li class="notification-row ${row.read_at?'is-read':'is-unread'}">
    <span class="notification-symbol" aria-hidden="true">${icon(row.kind==='source_blocked'?'warning':row.kind==='price_change'?'chart':'building')}</span>
    <div class="notification-content"><div class="notification-meta"><span>${e(typeNames[row.kind]||'Aggiornamento')}</span><time datetime="${e(row.created_at)}">${e(stamp(row.created_at))}</time>${row.read_at?'':'<span class="notification-unread">Non letta</span>'}</div>
      ${row.title===typeNames[row.kind]&&row.body?`<h2>${e(row.body)}</h2>`:`<h2>${e(row.title)}</h2>${row.body?`<p>${e(row.body)}</p>`:''}`}
      <div class="notification-actions">${target?action('notification-open',target,'arrow','btn small-btn',attrs):''}${row.read_at?'<span class="notification-read">Letta</span>':action('notification-read','Segna come letta','check','text-button',attrs)}</div>
    </div></li>`;
}
export function inboxView(s){
  const box=s.inbox||inboxState(),busy=!!s.inboxBusy,unread=s.ops?.unread??box.unread_total,mail=s.ops?.mail||{};
  return `${pageHeading('','Inbox','',action('inbox-retry','Aggiorna','refresh','btn',box.loading||busy?'disabled':''))}
    <section class="panel inbox-surface" aria-label="Notifiche">
      <div class="notification-toolbar"><div class="segmented" role="group" aria-label="Stato di lettura">
        ${action('inbox-filter','Tutte','',!box.unread?'active':'',`id="inbox-all" data-unread="false" aria-pressed="${!box.unread}" ${busy?'disabled':''}`)}
        ${action('inbox-filter',`Non lette <span class="notification-count">${num(unread)}</span>`,'',box.unread?'active':'',`id="inbox-unread" data-unread="true" aria-pressed="${box.unread}" ${busy?'disabled':''}`)}
      </div><label class="notification-kind"><span>Tipo di evento</span><select id="inbox-kind" aria-label="Tipo di evento" ${busy?'disabled':''}>${Object.entries(kinds).map(([value,name])=>`<option value="${value}" ${value===box.kind?'selected':''}>${name}</option>`).join('')}</select></label></div>
      <div class="notification-summary"><span role="status">${box.loading?'Caricamento…':box.error?'Caricamento non riuscito':`${num(box.items.length)} di ${num(box.total)} notifiche`}</span>${action('read-all','Segna l’intera Inbox come letta','','text-button',`title="Tutte le notifiche, anche quelle fuori dai filtri" ${busy||box.loading||!unread?'disabled':''}`)}</div>
      <div id="inbox-results" tabindex="-1" aria-busy="${box.loading}">${box.error?`<div class="notification-error" role="alert"><p>${e(box.error)}</p>${action('inbox-retry','Riprova','refresh','btn')}</div>`:box.items.length?`<ul class="notification-list">${box.items.map(row=>notification(row,busy)).join('')}</ul>`:box.loading?'<div class="notification-loading">Recupero delle notifiche…</div>':empty(box.unread?'Nessuna notifica da leggere':'Nessuna notifica',box.kind==='all'?'I nuovi eventi compariranno qui.':'Nessun evento di questo tipo.')}</div>
      ${box.moreError?`<p class="notification-error" role="alert">${e(box.moreError)}</p>`:''}
      ${box.has_more||box.items.length>40?`<div class="notification-pagination">${action('inbox-more',box.loading?'Caricamento…':box.moreError?'Riprova a caricare':box.has_more?'Mostra altre':'Tutto caricato','','btn',`id="inbox-more" ${!box.has_more||box.loading||busy?'disabled':''}`)}</div>`:''}
    </section><details class="notification-channels"><summary>Canali di notifica</summary><p>Inbox attiva · Email ${mail.enabled?'attive':'non configurate'}</p>${mail.enabled?`<p>${num(mail.pending)} in attesa · ${num(mail.failed)} non inviate</p>`:''}</details>`;
}
