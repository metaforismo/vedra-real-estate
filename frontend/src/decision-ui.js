import {e,stamp,num,amount,safeUrl,label} from './utils.js';
import {signalChips} from './signals-ui.js';
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
export function decisionSection(s,p){
  const d=p.decision;if(!d)return '';
  const c=d.contact||{},last=d.calls?.[0];
  return `<section class="detail-section decision-section"><div class="section-title"><h2>Contatto e verifiche</h2><button class="btn small-btn" data-action="contact-log" data-id="${e(p.id)}" ${s.user.role==='viewer'?'disabled':''}>Registra contatto</button></div>
  <div class="contact-row"><div><strong>${e(c.name||c.organization||'Contatto da trovare')}</strong><small>${e(c.organization&&c.organization!==c.name?c.organization+' · ':'')}${e(c.role||'Recapito non presente nei dati acquisiti')}</small></div><div class="contact-links">${contactLinks(c)}</div></div>
  ${d.contact_route?`<div class="contact-route"><span>${e(d.contact_route.label)}</span>${d.contact_route.quote?`<details><summary>Dichiarazione nella fonte</summary><blockquote>${e(d.contact_route.quote)}</blockquote></details>`:''}</div>`:''}
  ${lastContact(last)}
  ${preparation(p)}
  ${p.signals?(d.mandate?`<p class="small muted mandate-quote">Mandato nella fonte: “${e(d.mandate.quote)}”</p>`:''):`<details class="asset-facts"><summary>Catasto e storico${d.change_of_use?'<span class="setting-indicator">Cambio d’uso dichiarato</span>':''}</summary><div class="decision-grid"><div><span>Categoria catastale</span><strong>${e(d.cadastral?.quote||'Non indicata')}</strong></div><div><span>Cambio d’uso</span><strong>${e(d.change_of_use?.quote||'Non indicato')}</strong></div><div><span>Pubblicazione dichiarata</span><strong>${d.published_at?day(d.published_at):'Non indicata'}</strong><small>Prima rilevazione ${day(d.first_seen)}</small></div><div><span>Ribassi osservati</span><strong>${num(d.price_reductions)}</strong></div></div>
  ${d.mandate?`<p class="small muted">Mandato nella fonte: “${e(d.mandate.quote)}”</p>`:''}<small class="muted">Dichiarazioni dell’annuncio; catasto, fattibilità e mandato da verificare.</small></details>`}
  ${crossSourceSection(p)}
  ${d.calls?.length?`<details><summary>Storico contatti (${d.calls.length})</summary>${d.calls.map(x=>`<article class="contact-history"><strong>${e(outcomes[x.outcome])} · ${e(x.contact_name)}</strong><small>${stamp(x.created_at,true)} · ${e(x.author)} · ${e(mandates[x.mandate_status])}</small><p>${e(x.note)}</p>${x.next_contact?`<small>Richiama ${day(x.next_contact)}</small>`:''}</article>`).join('')}</details>`:''}</section>`;
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
    <dl><div><dt>Interlocutore</dt><dd>${e(last.contact_name||'Non indicato')}</dd></div><div><dt>Prossimo contatto</dt><dd>${last.next_contact?day(last.next_contact):'Non programmato'}</dd></div></dl>
    <small>${e(mandates[last.mandate_status]||'Mandato da verificare')} · ${e(last.author)}</small>
  </article>`;
}
export function todayPanel(s){
  const today=s.ops?.today||{call:[],verify:[]};
  const card=(p,canCall)=>{
    const reasons=(p.reasons||[]).filter(x=>!(p.signals&&x.startsWith('Scarto dal benchmark:'))),primary=reasons.find(x=>x.startsWith('Scarto dal benchmark:'))||reasons[0]||'Selezionato dal team',otherReasons=reasons.filter(x=>x!==primary),checks=[...new Set(p.checks||[])],contact=p.contact||{},url=safeUrl(p.url);
    return `<article class="today-item">
      ${propertyThumb(p,'today-thumb')}
      <div class="today-asset"><button class="today-title" data-action="property" data-id="${e(p.id)}">${e(p.title)}</button><small>${[p.city,p.zone].filter(Boolean).map(e).join(' · ')}${p.surface?` · ${num(p.surface)} m²`:''}</small><strong class="today-price">${amount(p.price,p.currency)}${p.signals?.market?.price_sqm?`<span>${amount(Math.round(p.signals.market.price_sqm),p.currency)}/m²</span>`:''}</strong>${signalChips(p)}</div>
      <div class="today-reason"><span class="mobile-column-label">Perché approfondire</span><p>${e(primary)}</p>${checks.length?`<ul class="today-checks">${checks.map(x=>`<li>${e(x)}</li>`).join('')}</ul>`:''}<details class="today-provenance" data-today-section="reason-${e(p.id)}" ${s.todayExpanded?.['reason-'+p.id]?'open':''}><summary id="today-reason-${e(p.id)}" data-today-toggle>Motivi e fonte</summary>${otherReasons.length?`<ul>${otherReasons.map(x=>`<li>${e(x)}</li>`).join('')}</ul>`:''}${p.source_name?`<small>${e(p.source_name)}</small>`:''}<small>Rilevato ${day(p.last_seen)}${p.linked_count>1?` · ${num(p.linked_count)} annunci collegati`:''}</small></details></div>
      <div class="today-contact"><span class="mobile-column-label">Contatto</span><strong>${e(contact.name||contact.organization||'Da trovare')}</strong>${p.contact_route?`<small>${e(p.contact_route.label)}</small>`:''}${p.last_contact?.next_contact?`<small class="callback-date">Richiama ${day(p.last_contact.next_contact)}</small>`:''}${canCall?`<div class="contact-links">${contactLinks(contact)}</div>`:''}</div>
      <div class="today-actions"><button class="btn primary" data-action="property" data-id="${e(p.id)}">Apri scheda</button>${canCall?`<button class="btn" data-action="contact-log" data-id="${e(p.id)}" ${s.user.role==='viewer'?'disabled':''}>Registra esito</button>`:url?`<a class="text-link" href="${url}" target="_blank" rel="noopener noreferrer">Apri fonte</a>`:''}</div>
    </article>`;
  };
  const headings='<div class="today-columns" aria-hidden="true"><span>Immobile</span><span>Perché approfondire</span><span>Contatto</span><span>Azioni</span></div>';
  const group=(rows,canCall,limit,key)=>headings+rows.slice(0,limit).map(p=>card(p,canCall)).join('')+(rows.length>limit?`<details class="today-overflow" data-today-section="${key}" ${s.todayExpanded?.[key]?'open':''}><summary id="today-toggle-${key}" data-today-toggle>Mostra altri ${num(rows.length-limit)} ${canCall?'contatti':'da verificare'}</summary>${rows.slice(limit).map(p=>card(p,canCall)).join('')}</details>`:'');
  return `<section class="panel today-panel"><div class="section-title"><h2>Chi contattare</h2><span class="quiet-pill">${num(today.call.length)} ${today.limited?'nel campione':today.call.length===1?'contatto':'contatti'}</span></div>${today.call.length?group(today.call,true,8,'call'):`<div class="today-empty"><strong>Nessun contatto pronto</strong><p>${today.verify.length?'Completa le verifiche qui sotto.':'Modifica la ricerca o eseguila di nuovo.'}</p><a class="btn" href="#agents">Gestisci ricerche</a></div>`}${today.verify.length?`<details class="today-missing" data-today-section="verify" ${s.todayExpanded?.verify===false?'':'open'}><summary id="today-toggle-verify" data-today-toggle>Da verificare <span class="quiet-pill">${num(today.verify.length)}</span></summary>${group(today.verify,false,4,'verifyMore')}</details>`:''}${today.limited?'<p class="today-limit">Primi 100 candidati esaminati. <a href="#properties">Apri tutto l’archivio</a></p>':''}</section>`;
}

function crossSourceSection(p){
  const cross=p.cross_sources;if(!cross||cross.count<2)return '';
  return `<div class="cross-source-summary">${cross.conflicts.length?`<p class="evidence-warning">${cross.conflicts.map(e).join(' · ')}</p>`:''}<details class="cross-source-details"><summary>Stesso asset · ${num(cross.count)} annunci</summary><p class="small muted">Collegamenti confermati dal team. Ogni fonte conserva i propri dati.</p>${cross.entries.map(row=>`<article class="cross-source-row"><div><strong>${e(row.source)}</strong><small>${day(row.last_seen)} · ${e(label(row.availability))}</small><span>${amount(row.price,row.currency)} · ${num(row.surface)} m² · ${e(label(row.area_basis))}</span><small>${e(row.contact.name||row.contact.organization||'Contatto non indicato')}</small>${row.mandate?`<small>“${e(row.mandate)}”</small>`:''}</div><div class="contact-links">${contactLinks(row.contact)}<a class="btn small-btn" href="${safeUrl(row.url)}" target="_blank" rel="noopener noreferrer">Fonte</a>${row.id!==p.id?`<button class="btn small-btn" data-action="property" data-id="${e(row.id)}">Scheda</button>`:''}</div></article>`).join('')}${cross.limited?'<p class="small muted">Mostrati 100 annunci collegati.</p>':''}</details></div>`;
}


function preparation(p){
  const support=p.decision_support;if(!support)return '';
  const age=support.freshness,other=support.related_contact;
  return `<div class="contact-preparation"><p class="small ${age.status==='stale'?'evidence-warning':'muted'}">${e(age.label)}${age.checked_at?` · ${e(age.method)} ${stamp(age.checked_at,true)}`:''}</p>${other?`<div class="related-contact"><strong>Già contattato su un annuncio collegato</strong><p>${e(outcomes[other.outcome])} · ${e(other.contact_name)} · ${stamp(other.created_at,true)}</p><p>${e(other.note)}</p>${other.next_contact?`<small>Richiama ${day(other.next_contact)}</small>`:''}<button class="btn small-btn" data-action="property" data-id="${e(other.property_id)}">Apri il contatto registrato</button></div>`:''}${support.questions.length?`<details class="call-questions"><summary>Da chiarire · ${support.questions.length}</summary><ul>${support.questions.map(q=>`<li>${e(q)}</li>`).join('')}</ul></details>`:''}</div>`;
}
