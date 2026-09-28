import {e,label,num,stamp} from './utils.js';
import {action} from './ui.js';

// Each observation keeps its own currency; missing historical context stays missing.
export function historicalPrice(value,currency){
  if(value==null)return 'Non disponibile';
  return currency==='EUR'?`€ ${num(value,2)}`:`${num(value,2)} ${currency&&currency!=='XXX'?currency:'(valuta non registrata)'}`;
}
function display(field,value,context){
  if(field==='availability')return !value?'Non registrata':value==='unknown'?'Da verificare':label(value);
  if(value==null||value==='')return 'Non disponibile';
  if(field==='price')return historicalPrice(value,context?.currency);
  if(typeof value==='boolean')return value?'Sì':'No';
  if(typeof value==='number')return num(value,4)+(field==='surface'?' m²':'');
  return ['description','title','address','city','zone'].includes(field)?String(value):label(String(value));
}
export function priceMovement(item){
  const pct=item.price_change_pct;
  if(!Number.isFinite(pct)||pct===0)return '';
  return `${pct<0?'Ribasso':'Aumento'} ${num(Math.abs(pct),1)}%`;
}
function fieldChange(change,item){
  const before=display(change.field,change.before,item.previous_price_context),after=display(change.field,change.after,item.price_context);
  const values=`<div class="history-values"><div><small>Prima</small><p>${e(before)}</p></div><div><small>Dopo</small><p>${e(after)}</p></div></div>`;
  const long=before.length>220||after.length>220;
  return `<div class="history-change"><dt>${e(label(change.field))}</dt><dd>${long?`<details class="history-text"><summary>Leggi il confronto completo</summary>${values}</details>`:values}</dd></div>`;
}
export function historyItems(items){
  return items.map(item=>{
    const movement=priceMovement(item),count=item.changes.length;
    const status=count?`${count} ${count===1?'campo modificato':'campi modificati'}`:item.comparable?'Nessuna variazione':item.baseline?'Prima rilevazione':'Confronto non disponibile';
    const priority=['price','availability','surface','description'];
    const main=item.changes.filter(change=>priority.includes(change.field)).sort((a,b)=>priority.indexOf(a.field)-priority.indexOf(b.field));
    if(!main.length)main.push(...item.changes.slice(0,3));
    const extra=item.changes.filter(change=>!main.includes(change));
    const changesHtml=`<dl class="history-changes">${main.map(change=>fieldChange(change,item)).join('')}</dl>${extra.length?`<details class="history-extra"><summary>Altri campi (${num(extra.length)})</summary><dl class="history-changes">${extra.map(change=>fieldChange(change,item)).join('')}</dl></details>`:''}`;
    return `<li class="history-event" data-observation-id="${e(item.id)}"><div class="history-event-heading"><time datetime="${e(item.observed_at)}">${e(stamp(item.observed_at,true))}</time>${movement?`<span class="history-movement">${e(movement)}</span>`:''}</div><h3>${status}</h3>
      ${count?changesHtml:item.snapshot?`<dl class="history-snapshot"><div><dt>Prezzo richiesto</dt><dd>${e(historicalPrice(item.snapshot.price,item.snapshot.currency))}</dd></div><div><dt>Disponibilità</dt><dd>${e(display('availability',item.snapshot.availability))}</dd></div></dl>`:''}
      ${!item.has_evidence?'<p class="history-gap">Campi originali non conservati.</p>':!item.comparable&&!item.baseline?'<p class="history-gap">Manca una copia dei campi della rilevazione precedente.</p>':''}
      <details class="history-technical"><summary>Dettagli rilevazione</summary><p>Parser: ${e(item.parser_version||'Non registrato')}</p></details></li>`;
  }).join('');
}
export function historyFooter(data,id,{loading=false,error=''}={}){
  return `${error?`<p class="history-error" role="alert">${e(error)}</p>`:''}<div class="history-pagination"><span id="history-count" tabindex="-1" role="status">${num(data.items.length)} di ${num(data.total)} rilevazioni</span>${data.next_cursor?action('history-more',loading?'Caricamento…':error?'Riprova':'Mostra precedenti','clock','btn',`id="history-more" data-id="${e(id)}" ${loading?'disabled':''}`):''}</div>`;
}
export function historyContent(data,propertyId){
  return `<div class="modal-body history-content" id="history-content" aria-busy="false"><div class="history-toolbar"><span>${num(data.with_fields)} di ${num(data.total)} rilevazioni con campi conservati</span></div>
    <p class="history-scope">Le date indicano quando Vedra ha rilevato l’annuncio, non quando è stato pubblicato.</p>
    <ol class="evidence-timeline history-events">${historyItems(data.items)}</ol>${!data.items.length?'<p class="history-gap">Nessuna rilevazione disponibile.</p>':''}
    <div id="history-footer">${historyFooter(data,propertyId)}</div><details class="history-method"><summary>Come leggere lo storico</summary><p>Il confronto usa i campi conservati nelle due rilevazioni. I dati mancanti non vengono ricostruiti.</p><p>La variazione percentuale del prezzo compare solo con valuta, operazione, superficie e base di superficie invariate. Non misura lo sconto sul mercato.</p></details><div class="modal-form-footer"><button type="button" class="btn footer-back" data-action="property" data-id="${e(propertyId)}">Torna all’immobile</button></div></div>`;
}
export function historyPreview(p){
  const rows=(p.observations||[]).slice(-3).reverse(),total=p.observations?.length||0;
  return `<section class="detail-section history-preview"><div class="section-title"><h2>Storico annuncio</h2>${action('property-history','Apri cronologia','clock','btn small-btn',`data-id="${e(p.id)}"`)}</div><p class="history-scope">${num(total)} ${total===1?'rilevazione':'rilevazioni'} · ${total?'dal '+stamp(p.observations?.[0]?.observed_at||p.first_seen,true):'Nessuno storico disponibile'}</p>${rows.length?`<ol>${rows.map(o=>`<li><time datetime="${e(o.observed_at)}">${e(stamp(o.observed_at,true))}</time><strong>${e(historicalPrice(o.price,o.currency))}</strong></li>`).join('')}</ol>`:''}${total>3?'<small>Ultime 3 rilevazioni · tutte nella cronologia</small>':''}</section>`;
}
