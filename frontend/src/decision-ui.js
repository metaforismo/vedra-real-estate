import {e,stamp,num,amount,safeUrl,label} from './utils.js';
import {signalSummary} from './signals-ui.js';
import {icon} from './icons.js';
import {propertyThumb} from './ui.js';
export const outcomes={no_answer:'Nessuna risposta',reached:'Interlocutore raggiunto',documents_requested:'Documenti richiesti',not_relevant:'Non pertinente'};
const mandates={not_checked:'Mandato da verificare',declared:'Mandato dichiarato',confirmed_by_team:'Mandato verificato dal team'};
function day(value){
  if(!value)return 'Non indicata';
  const date=new Date(value.length===10?value+'T12:00:00':value);
  return Number.isNaN(date.getTime())?'Non indicata':date.toLocaleDateString('it-IT',{day:'2-digit',month:'short',year:'numeric'});
}
function contactLinks(c){
  const phone=/^\+?\d{6,16}$/.test(c.telephone||'')?c.telephone:'';
  const email=/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(c.email||'')?c.email:'';
  return `${phone?`<a class="btn" href="tel:${e(phone)}">${e(phone)}</a>`:''}${email?`<a class="btn" href="mailto:${encodeURIComponent(email)}">Email</a>`:''}`;
}
const mail='<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/></svg>';
// Sheet recapiti: real links with an icon, never input-looking boxes; invalid values are not linked.
function sheetLinks(c){
  const phone=/^\+?\d{6,16}$/.test(c.telephone||'')?c.telephone:'';
  const email=/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(c.email||'')?c.email:'';
  return `${phone?`<a class="contact-link" href="tel:${e(phone)}">${icon('phone')}<span>${e(phone)}</span></a>`:''}${email?`<a class="contact-link" href="mailto:${encodeURIComponent(email)}" title="${e(email)}">${mail}<span>Email</span></a>`:''}`;
}
export function decisionSection(s,p){
  const d=p.decision;if(!d)return '';
  const c=d.contact||{},last=d.calls?.[0],links=sheetLinks(c);
  const who=c.name||c.organization;
  return `<section class="detail-section decision-section"><div class="section-title"><h2>Contatto e verifiche</h2><button class="btn primary small-btn" data-action="contact-log" data-id="${e(p.id)}" ${s.user.role==='viewer'?'disabled':''}>Registra contatto</button></div>
  <div class="contact-row"><div class="contact-who"><strong class="${who?'':'missing'}">${e(who||'Contatto da trovare')}</strong><small>${e(c.organization&&c.organization!==c.name?c.organization+' · ':'')}${e(c.role||'Recapito non presente nei dati acquisiti')}</small></div>${links?`<div class="contact-links">${links}</div>`:''}</div>
  <dl class="contact-facts">
    ${d.contact_route?`<div><dt>Filiera</dt><dd class="contact-route"><span>${e(d.contact_route.label.replace(/^Filiera\s+(\S)/i,(_,c)=>c.toUpperCase()))}</span>${d.contact_route.quote?`<details><summary>Dichiarazione nella fonte</summary><blockquote>${e(d.contact_route.quote)}</blockquote></details>`:''}</dd></div>`:''}
    <div><dt>Ultimo contatto</dt><dd>${lastContact(last)}</dd></div>
    ${freshness(p)}
  </dl>
  ${p.signals?(d.mandate?`<p class="mandate-quote">Mandato nella fonte: “${e(d.mandate.quote)}”</p>`:''):`<details class="asset-facts"><summary>Catasto e storico${d.change_of_use?'<span class="section-meta">Cambio d’uso dichiarato</span>':''}</summary><div class="decision-grid"><div><span>Categoria catastale</span><strong>${e(d.cadastral?.quote||'Non indicata')}</strong></div><div><span>Cambio d’uso</span><strong>${e(d.change_of_use?.quote||'Non indicato')}</strong></div><div><span>Pubblicazione dichiarata</span><strong>${d.published_at?day(d.published_at):'Non indicata'}</strong><small>Prima rilevazione ${day(d.first_seen)}</small></div><div><span>Ribassi osservati</span><strong>${num(d.price_reductions)}</strong></div></div>
  ${d.mandate?`<p class="small muted">Mandato nella fonte: “${e(d.mandate.quote)}”</p>`:''}<small class="muted">Dichiarazioni dell’annuncio; catasto, fattibilità e mandato da verificare.</small></details>`}
  ${preparation(p)}
  ${crossSourceSection(p)}
  ${d.calls?.length?`<details class="contact-log-history"><summary>Storico contatti (${d.calls.length})</summary>${d.calls.map(x=>`<article class="contact-history"><strong>${e(outcomes[x.outcome])} · ${e(x.contact_name)}</strong><small>${stamp(x.created_at,true)} · ${e(x.author)} · ${e(mandates[x.mandate_status])}</small><p>${e(x.note)}</p>${x.next_contact?`<small>Richiama ${day(x.next_contact)}</small>`:''}</article>`).join('')}</details>`:''}</section>`;
}
export function contactForm(p){
  const contact=p.decision?.contact||{};
  return `<form class="modal-form contact-form" id="contact-form" data-id="${e(p.id)}" data-request="${crypto.randomUUID()}">
    <fieldset class="contact-fields"><legend class="sr-only">Esito del contatto</legend>
      <label for="contact-name">Interlocutore<input id="contact-name" name="contact_name" maxlength="240" value="${e(contact.name||contact.organization||'')}"></label>
      <div class="form-grid">
        <label for="contact-outcome">Esito<select id="contact-outcome" name="outcome" aria-label="Esito" required><option value="" disabled selected>Seleziona esito</option>${Object.entries(outcomes).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label>
        <label for="contact-next">Prossimo contatto<input id="contact-next" name="next_contact" aria-label="Prossimo contatto" type="date" aria-describedby="contact-next-help"><small id="contact-next-help" hidden>Non previsto per questo esito.</small></label>
      </div>
      <label for="contact-mandate">Mandato<select id="contact-mandate" name="mandate_status" aria-label="Mandato">${Object.entries(mandates).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label>
      <label for="contact-note">Note del contatto<textarea id="contact-note" name="note" aria-label="Note del contatto" maxlength="2000" rows="4" aria-describedby="contact-note-help" placeholder="Informazioni ricevute, documenti e verifiche"></textarea><small id="contact-note-help" hidden>Indica come hai verificato il mandato (almeno 10 caratteri).</small></label>
      <div id="modal-error" class="form-error" role="alert"></div>
      <div class="modal-form-footer"><button type="button" class="btn" data-action="property" data-id="${e(p.id)}">Annulla</button><button type="submit" class="btn primary">Salva esito</button></div>
    </fieldset>
  </form>`;
}
export function syncContactForm(form){
  const irrelevant=form.elements.outcome.value==='not_relevant';
  form.elements.next_contact.disabled=irrelevant;
  form.querySelector('#contact-next-help').hidden=!irrelevant;
  form.querySelector('#contact-note-help').hidden=form.elements.mandate_status.value!=='confirmed_by_team';
}
function lastContact(last){
  if(!last)return '<p class="contact-unrecorded">Nessun contatto registrato.</p>';
  return `<article class="contact-last"><div class="contact-last-heading"><strong>${e(outcomes[last.outcome]||'Esito non disponibile')}</strong><time>${stamp(last.created_at,true)}</time></div>
    <p>${e(last.contact_name||'Interlocutore non indicato')} · Prossimo contatto: ${last.next_contact?day(last.next_contact):'Non programmato'}</p>
    <small>${e(mandates[last.mandate_status]||'Mandato da verificare')} · ${e(last.author)}</small>
  </article>`;
}
// Oggi queue: one row per asset. What it is and why it matters on the left, the price as a column,
// the person to call and the way to reach them on the right. The whole row opens the sheet.
const shortDay=value=>{const date=value?new Date(value.length===10?value+'T12:00:00':value):null;return date&&!Number.isNaN(date.getTime())?date.toLocaleDateString('it-IT',{day:'numeric',month:'short'}):'';};
const perSqm=(value,currency)=>value==null?'':`${amount(Math.round(value),currency)}/m²`;
// Only the country code is split off: Italian numbers have no fixed grouping and a wrong split misleads.
const phoneText=phone=>phone.startsWith('+39')?`+39 ${phone.slice(3)}`:phone;
function reachLinks(c){
  const phone=/^\+?\d{6,16}$/.test(c.telephone||'')?c.telephone:'';
  const email=/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(c.email||'')?c.email:'';
  return `${phone?`<a class="today-phone" href="tel:${e(phone)}">${icon('phone')}<span>${e(phoneText(phone))}</span></a>`:''}${email?`<a class="today-mail" href="mailto:${e(email)}">Email</a>`:''}`;
}
// Where the row comes from: the searches that matched it, the source and when it was last seen there.
// Inline, never in a tooltip: the row overlay would keep a title from ever showing.
function provenance(p){
  const searches=(p.reasons||[]).filter(x=>x.startsWith('Nei criteri di ')).map(x=>x.slice(15));
  const parts=[searches.length?`${searches.length===1?'Ricerca':'Ricerche'} ${searches.map(x=>`«${x}»`).join(', ')}`:'Selezionato dal team'];
  if(p.source_name)parts.push(p.source_name);
  const seen=shortDay(p.last_seen);if(seen)parts.push(`rilevato ${seen}`);
  if(p.linked_count>1)parts.push(`${num(p.linked_count)} annunci collegati`);
  return `<p class="today-provenance">${parts.map(x=>`<span>${e(x)}</span>`).join('')}</p>`;
}
function todayRow(s,p,canCall){
  const contact=p.contact||{},checks=[...new Set(p.checks||[])],url=safeUrl(p.url),last=p.last_contact;
  const who=contact.name||contact.organization;
  const route=p.contact_route?.kind&&p.contact_route.kind!=='unknown'?p.contact_route.label:'';
  // Only a declared owner or mandate is good news; any other known route is plain information.
  const declared=['owner_declared','mandate_declared'].includes(p.contact_route?.kind);
  const lastLine=last?[e(outcomes[last.outcome]||'Contattato'),shortDay(last.created_at),last.next_contact?`<span class="callback-date">richiamo ${shortDay(last.next_contact)}</span>`:''].filter(Boolean).join(' · '):'';
  // Without market signals the benchmark discount is still a fact worth showing.
  const why=signalSummary(p)||(p.discount!=null&&Math.abs(p.discount)>=.5?`<p class="today-why"><span class="why-lead ${p.discount>0?'below':''}">${num(Math.abs(p.discount),0)}% ${p.discount>0?'sotto':'sopra'}</span> il prezzo di zona</p>`:'');
  const flagged=checks.length?`<ul class="today-checks">${checks.map(x=>`<li>${e(x)}</li>`).join('')}</ul>`:'';
  const sqm=perSqm(p.signals?.market?.price_sqm,p.currency);
  return `<article class="today-item${canCall?'':' is-blocked'}">
    <div class="today-asset">${p.images?.length?propertyThumb(p,'today-thumb'):''}<div class="today-text">
      <button class="today-title" data-action="property" data-id="${e(p.id)}">${e(p.title)}</button>
      <p class="today-meta">${[p.city,p.zone].filter(Boolean).map(e).join(' · ')}${p.surface?`${p.city||p.zone?' · ':''}${num(p.surface)} m²`:''}</p>
      ${why}${canCall?flagged:''}${provenance(p)}</div></div>
    <div class="today-figures"><strong class="today-price">${amount(p.price,p.currency)}</strong>${sqm?`<small>${sqm}</small>`:''}</div>
    <div class="today-contact">${who?`<strong>${e(who)}</strong>`:canCall?'<strong class="is-missing">Nome non indicato</strong>':''}
      ${route?`<small class="today-route${declared?' is-declared':''}">${e(route)}</small>`:''}
      ${lastLine?`<small class="today-last">${lastLine}</small>`:''}
      ${canCall?`<div class="today-reach">${reachLinks(contact)}</div>`:flagged}</div>
    <div class="today-actions">${canCall?`<button class="btn today-log" data-action="contact-log" data-id="${e(p.id)}" ${s.user.role==='viewer'?'disabled':''}>Registra esito</button>`:url?`<a class="btn today-source" href="${url}" target="_blank" rel="noopener noreferrer">Apri fonte ${icon('arrow')}</a>`:''}</div>
  </article>`;
}
export function todayPanel(s){
  const today=s.ops?.today||{call:[],verify:[]};
  const rows=(list,canCall)=>list.map(p=>todayRow(s,p,canCall)).join('');
  const group=(list,canCall,limit,key)=>rows(list.slice(0,limit),canCall)+(list.length>limit?`<details class="today-overflow" data-today-section="${key}" ${s.todayExpanded?.[key]?'open':''}><summary id="today-toggle-${key}" data-today-toggle>${list.length-limit===1?`Mostra un altro ${canCall?'contatto':'da verificare'}`:`Mostra altri ${num(list.length-limit)} ${canCall?'contatti':'da verificare'}`}</summary>${rows(list.slice(limit),canCall)}</details>`:'');
  const count=today.limited?`${num(today.call.length)} nel campione`:`${num(today.call.length)} ${today.call.length===1?'contatto':'contatti'}`;
  const columns='<div class="today-columns" aria-hidden="true"><span>Immobile e segnali</span><span>Prezzo</span><span>Contatto</span><span></span></div>';
  return `<section class="panel today-panel"><div class="section-title"><div><h2>Chi contattare</h2><p class="today-order">Prima i richiami in scadenza, poi chi ha una filiera chiara, poi la priorità</p></div><span class="today-count">${count}</span></div>
    ${today.call.length?columns+group(today.call,true,5,'call'):`<div class="today-empty"><strong>Nessun contatto pronto</strong><p>${today.verify.length?'Gli immobili qui sotto aspettano un recapito o una verifica.':'Modifica la ricerca o eseguila di nuovo.'}</p>${today.verify.length?'':'<a class="btn" href="#agents">Gestisci ricerche</a>'}</div>`}
    ${today.verify.length?`<details class="today-missing" data-today-section="verify" ${s.todayExpanded?.verify===false?'':'open'}><summary id="today-toggle-verify" data-today-toggle><span class="today-missing-title">Da verificare <span class="quiet-pill">${num(today.verify.length)}</span></span><small>Manca un recapito o un dato da ricontrollare</small></summary>${group(today.verify,false,4,'verifyMore')}</details>`:''}
    ${today.limited?'<p class="today-limit">Primi 100 candidati esaminati. <a href="#properties">Apri tutto l’archivio</a></p>':''}</section>`;
}

function crossSourceSection(p){
  const cross=p.cross_sources;if(!cross||cross.count<2)return '';
  return `<div class="cross-source-summary"><details class="cross-source-details"><summary>Stesso asset · ${num(cross.count)} annunci${cross.conflicts.length?`<span class="section-meta warn">${cross.conflicts.map(e).join(' · ')}</span>`:''}</summary><p class="small muted">Collegamenti confermati dal team. Ogni fonte conserva i propri dati.</p>${cross.entries.map(row=>`<article class="cross-source-row"><div><strong>${e(row.source)}</strong><span>${amount(row.price,row.currency)} · ${num(row.surface)} m² · ${e(label(row.area_basis))}</span><small>${e(row.contact.name||row.contact.organization||'Contatto non indicato')} · ${day(row.last_seen)} · ${e(label(row.availability))}</small>${row.mandate?`<small>“${e(row.mandate)}”</small>`:''}</div><div class="contact-links">${sheetLinks(row.contact)}<a class="btn small-btn" href="${safeUrl(row.url)}" target="_blank" rel="noopener noreferrer">Fonte</a>${row.id!==p.id?`<button class="btn small-btn" data-action="property" data-id="${e(row.id)}">Scheda</button>`:''}</div></article>`).join('')}${cross.limited?'<p class="small muted">Mostrati 100 annunci collegati.</p>':''}</details></div>`;
}

// How fresh the acquired data is: one line in the contact facts, a warning only when stale.
function freshness(p){
  const age=p.decision_support?.freshness;if(!age)return '';
  return `<div><dt>Dati</dt><dd class="${age.status==='stale'?'evidence-warning':''}">${e(age.label)}${age.checked_at?`<small>${e(age.method)} · ${stamp(age.checked_at,true)}</small>`:''}</dd></div>`;
}

function preparation(p){
  const support=p.decision_support;if(!support)return '';
  const other=support.related_contact;
  return `${other?`<div class="related-contact"><strong>Già contattato su un annuncio collegato</strong><p>${e(outcomes[other.outcome])} · ${e(other.contact_name)} · ${stamp(other.created_at,true)}</p><p>${e(other.note)}</p>${other.next_contact?`<small>Richiama ${day(other.next_contact)}</small>`:''}<button class="btn small-btn" data-action="property" data-id="${e(other.property_id)}">Apri il contatto registrato</button></div>`:''}${support.questions.length?`<details class="call-questions"><summary>Da chiarire · ${support.questions.length}</summary><ul>${support.questions.map(q=>`<li>${e(q)}</li>`).join('')}</ul></details>`:''}`;
}
