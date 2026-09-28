import {e,num} from './utils.js';
import {icon} from './icons.js';
import {action,empty,pageHeading} from './ui.js';
import {inboxState} from './inbox-controller.js';
import {grouped} from './table-ui.js';
const kinds={all:'Tutti gli eventi',new_property:'Nuovi immobili',price_change:'Variazioni di prezzo',availability_change:'Disponibilità',source_blocked:'Problemi delle fonti'};
const typeNames={new_property:'Nuovo immobile',price_change:'Prezzo aggiornato',availability_change:'Disponibilità aggiornata',source_blocked:'Fonte da verificare'};
const dayKey=value=>{const d=new Date(value);return Number.isNaN(d.getTime())?'':`${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;};
function dayLabel(value,now=new Date()){
  const d=new Date(value);if(Number.isNaN(d.getTime()))return 'Data non disponibile';
  const yesterday=new Date(now);yesterday.setDate(now.getDate()-1);
  if(dayKey(d)===dayKey(now))return 'Oggi';
  if(dayKey(d)===dayKey(yesterday))return 'Ieri';
  return d.toLocaleDateString('it-IT',{weekday:'long',day:'numeric',month:'long',...(d.getFullYear()===now.getFullYear()?{}:{year:'numeric'})});
}
const time=value=>{const d=new Date(value);return Number.isNaN(d.getTime())?'':d.toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit'});};

// One line per event: the row opens its target; reading state is the dot and the weight of the title.
function notification(row,busy){
  const target=row.property_id?'Apri immobile':row.run_id?'Apri ricerca':'';
  const attrs=`data-id="${e(row.id)}" ${busy?'disabled':''}`;
  const type=typeNames[row.kind]||'Aggiornamento';
  const [title,detail]=row.title===typeNames[row.kind]&&row.body?[row.body,type]:[row.title,[type,row.body].filter(Boolean).join(' · ')];
  return `<li class="notification-row ${row.read_at?'is-read':'is-unread'} ${target?'has-target':''}">
    <span class="notification-dot" aria-hidden="true"></span>
    <span class="notification-symbol" aria-hidden="true">${icon(row.kind==='source_blocked'?'warning':row.kind==='price_change'?'chart':'building')}</span>
    <div class="notification-content"><h3>${row.read_at?'':'<span class="sr-only">Non letta: </span>'}${e(title)}</h3><p>${e(detail)}</p></div>
    <time datetime="${e(row.created_at)}">${e(time(row.created_at))}</time>
    <div class="notification-actions">${row.read_at?'':action('notification-read',icon('check'),'','icon-button notification-mark',`${attrs} aria-label="Segna come letta" title="Segna come letta"`)}${target?action('notification-open',icon('chevron'),'','icon-button notification-go',`${attrs} aria-label="${target}" title="${target}"`):''}</div>
  </li>`;
}
function byDay(items,busy){
  const groups=[];for(const row of items){const key=dayKey(row.created_at),last=groups.at(-1);if(last&&last.key===key)last.rows.push(row);else groups.push({key,label:dayLabel(row.created_at),rows:[row]});}
  return groups.map(g=>`<section class="notification-day"><h2>${e(g.label)}</h2><ul class="notification-list">${g.rows.map(row=>notification(row,busy)).join('')}</ul></section>`).join('');
}
export function inboxView(s){
  const box=s.inbox||inboxState(),busy=!!s.inboxBusy,unread=s.ops?.unread??box.unread_total,mail=s.ops?.mail||{};
  const more=box.has_more||box.items.length>40;
  return `${pageHeading('','Inbox','')}
    <section class="pg-surface inbox-surface" aria-label="Notifiche">
      <div class="pg-toolbar notification-toolbar"><div class="pg-segmented segmented" role="group" aria-label="Stato di lettura">
        ${action('inbox-filter','Tutte','',!box.unread?'active':'',`id="inbox-all" data-unread="false" aria-pressed="${!box.unread}" ${busy?'disabled':''}`)}
        ${action('inbox-filter',`Non lette <span class="notification-count pg-count">${num(unread)}</span>`,'',box.unread?'active':'',`id="inbox-unread" data-unread="true" aria-pressed="${box.unread}" ${busy?'disabled':''}`)}
      </div><select id="inbox-kind" aria-label="Tipo di evento" ${busy?'disabled':''}>${Object.entries(kinds).map(([value,name])=>`<option value="${value}" ${value===box.kind?'selected':''}>${name}</option>`).join('')}</select>
      <div class="pg-end">${action('read-all','Segna tutte come lette','','text-button',`title="Tutte le notifiche, anche quelle fuori dai filtri" ${busy||box.loading||!unread?'disabled':''}`)}</div></div>
      <div id="inbox-results" tabindex="-1" aria-busy="${box.loading}">${box.error?`<div class="notification-error" role="alert"><p>${e(box.error)}</p>${action('inbox-retry','Riprova','refresh','btn')}</div>`:box.items.length?byDay(box.items,busy):box.loading?'<div class="notification-loading">Recupero delle notifiche…</div>':empty(box.unread?'Nessuna notifica da leggere':'Nessuna notifica',box.kind==='all'?'I nuovi eventi compariranno qui.':'Nessun evento di questo tipo.')}</div>
      ${box.moreError?`<p class="notification-error pg-note" role="alert">${e(box.moreError)}</p>`:''}
      <div class="pg-foot notification-summary"><span role="status">${box.loading?'Caricamento…':box.error?'Caricamento non riuscito':`${grouped(box.items.length)} di ${grouped(box.total)} notifiche`}</span>${more?`<div class="notification-pagination">${action('inbox-more',box.loading?'Caricamento…':box.moreError?'Riprova a caricare':box.has_more?'Mostra altre':'Tutto caricato','','btn',`id="inbox-more" ${!box.has_more||box.loading||busy?'disabled':''}`)}</div>`:''}</div>
    </section><details class="pg-method notification-channels"><summary>Canali di notifica</summary><p>Inbox attiva · email ${mail.enabled?'attive':'non configurate'}${mail.enabled?` · ${num(mail.pending)} in attesa · ${num(mail.failed)} non inviate`:''}</p></details>`;
}
