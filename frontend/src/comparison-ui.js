import {e,num,label,reviewLabel,stamp,safeUrl} from './utils.js';

const missing='Non disponibile';
const text=value=>e(value||missing);
const small=value=>value?`<small>${e(value)}</small>`:'';
const money=(value,currency)=>value==null?missing:`${num(value,2)} ${e(currency&&currency!=='XXX'?currency:'(valuta non indicata)')}`;
const rate=(value,currency)=>value==null?missing:money(value,currency)+' / m²';
const dated=value=>value&&!Number.isNaN(new Date(value).getTime())?stamp(value,true):'Data non disponibile';
const link=(url,title)=>safeUrl(url)?`<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${e(title)}</a>`:text(title);
function contact(p){
  const c=p.decision?.contact||{};
  return `<strong>${text(c.name||c.organization||'Contatto da trovare')}</strong>${small(c.organization&&c.organization!==c.name?c.organization:'')}${small(c.role)}`;
}
function channels(p){
  const c=p.decision?.contact||{},links=[];
  if(/^\+?\d{6,16}$/.test(c.telephone||''))links.push(`<a href="tel:${e(c.telephone)}">${e(c.telephone)}</a>`);
  if(/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(c.email||''))links.push(`<a href="mailto:${encodeURIComponent(c.email)}">${e(c.email)}</a>`);
  return links.length?`<div class="comparison-links">${links.join('')}</div>`:'Recapito da trovare';
}
function reference(p,key){
  const group=p.market_references?.groups?.find(g=>g.key===key);
  if(!group)return missing;
  return `<strong>${rate(group.median_sqm,p.currency)}</strong>${small(`${num(group.count)} annunci · ${num(group.source_count??0)} ${group.source_count===1?'fonte':'fonti'}`)}${small(group.median_sqm==null?group.reason:'')}${(group.warnings||[]).map(small).join('')}`;
}
function omi(p){
  const o=p.market_references?.omi;
  if(o?.status!=='available'||o.stale||!o.rows?.length)return `Da verificare${small(o?.stale?'Periodo da aggiornare: '+o.period:o?.reason)}`;
  return o.rows.map(row=>`<div class="comparison-omi"><strong>${money(row.min_sqm,'EUR')}–${money(row.max_sqm,'EUR')} / m²</strong>${small([row.type,row.condition,row.area_basis==='gross'?'Superficie lorda':row.area_basis==='net'?'Superficie netta':'Base superficie non indicata'].filter(Boolean).join(' · '))}</div>`).join('')+small([o.period,o.zone_code].filter(Boolean).join(' · '))+link(o.source_url,o.source_label||'OMI')+small('Consultata: '+dated(o.retrieved_at));
}
function benchmark(p){
  const b=p.benchmark;
  return b?`<strong>${money(b.min_sqm,b.currency||p.currency)}–${money(b.max_sqm,b.currency||p.currency)} / m²</strong>${link(b.source_url,b.source_label||'Fonte non indicata')}${small(b.period)}`:'Nessun prezzo di zona compatibile';
}
function gap(p){
  if(p.discount==null||!p.benchmark)return 'Confronto non disponibile';
  if(p.discount===0)return 'In linea con il prezzo di zona';
  return `${num(Math.abs(p.discount),1)}% ${p.discount>0?'sotto':'sopra'} il prezzo di zona`;
}
function freshness(p){
  const f=p.decision_support?.freshness;
  return f?`<strong>${text(f.label)}</strong>${small(f.method)}${small(dated(f.checked_at))}`:missing;
}
export const comparisonSections=[
  {id:'decision',label:'Decisione',note:'Priorità di verifica, non rendimento. Pubblicato non significa disponibilità confermata.',rows:[
    ['Prezzo richiesto',p=>`<strong>${money(p.price,p.currency)}</strong>${small(p.transaction_type?label(p.transaction_type):'Operazione non indicata')} ${small(p.is_auction?'Asta':'')} `],
    ['Disponibilità',p=>text({listed:'Pubblicato',sold:'Venduto',rented:'Affittato',withdrawn:'Ritirato'}[p.availability]||'Da verificare')],
    ['Aggiornamento dati',freshness],
    ['Contatto',contact],['Recapiti',channels],
    ['Filiera',p=>text(p.decision?.contact_route?.label||'Da verificare')+(p.decision?.contact_route?.quote?`<details class="comparison-evidence"><summary>Dichiarazione nella fonte</summary><p>${e(p.decision.contact_route.quote)}</p></details>`:'')],
    ['Priorità di verifica',p=>{const value=p.priority?.score??p.priority_score;return value==null?missing:`${num(value)} / 100`;}],
    ['Fase del team',p=>text(reviewLabel(p.review_status))],
    ['Da chiarire',p=>p.decision_support?.questions?.length?`<details class="comparison-evidence"><summary>Domande · ${p.decision_support.questions.length}</summary><ul>${p.decision_support.questions.map(q=>`<li>${e(q)}</li>`).join('')}</ul></details>`:'Nessuna domanda disponibile'],
  ]},
  {id:'market',label:'Mercato',note:'Mediane di prezzi richiesti, non prezzi di vendita. OMI è una fascia di zona. Lo scostamento dal prezzo di zona non misura il margine.',rows:[
    ['Prezzo richiesto al m²',p=>rate(p.price_sqm,p.currency)],
    ['Da ristrutturare',p=>reference(p,'to_renovate')],['Ristrutturato',p=>reference(p,'renovated')],['Nuovo',p=>reference(p,'new')],['OMI',omi],
    ['Prezzo di zona',benchmark],['Scostamento dal prezzo di zona',gap],
  ]},
  {id:'facts',label:'Dati',note:'Caratteristiche dichiarate nelle fonti. Catasto, cambio d’uso e mandato richiedono verifica. Completezza misura la presenza dei campi, non la loro accuratezza.',rows:[
    ['Superficie',p=>p.surface==null?missing:`${num(p.surface,2)} m²${small(label(p.area_basis))}`],
    ['Tipologia',p=>text(label(p.property_type))],['Stato manutentivo',p=>text(label(p.condition))],
    ['Strategie',p=>text((p.analysis?.strategies||[]).map(x=>label(x.strategy)).join(', '))],
    ['Categoria catastale',p=>text(p.decision?.cadastral?.quote)],['Cambio d’uso',p=>text(p.decision?.change_of_use?.quote)],
    ['Pubblicazione dichiarata',p=>dated(p.decision?.published_at)],['Prima rilevazione',p=>dated(p.first_seen)],
    ['Ribassi osservati',p=>p.decision?.price_reductions==null?missing:num(p.decision.price_reductions)],
    ['Completezza',p=>p.completeness==null?missing:num(p.completeness)+'%'],
    ['Fonte',p=>link(p.url,p.source_name||'Fonte non indicata')],['Ultima acquisizione',p=>dated(p.last_seen)],
  ]},
];
export function comparisonContent(properties){
  const ids=new Set(properties.map(p=>p.id));
  const sameAsset=properties.some(p=>p.cross_sources?.entries?.some(row=>row.id!==p.id&&ids.has(row.id)));
  const currencies=new Set(properties.map(p=>p.currency||'XXX'));
  const operations=new Set(properties.map(p=>p.transaction_type||'unknown'));
  const warning=currencies.size>1||currencies.has('XXX')||operations.size>1||operations.has('unknown');
  return `<div class="comparison-toolbar"><div class="comparison-tabs" role="tablist" aria-label="Sezioni del confronto">${comparisonSections.map((section,i)=>`<button type="button" role="tab" id="compare-tab-${section.id}" aria-controls="compare-panel-${section.id}" aria-selected="${i===0}" tabindex="${i===0?0:-1}">${section.label}</button>`).join('')}</div><button class="btn" data-action="comparison-export" data-ids="${e(JSON.stringify(properties.map(p=>p.id)))}">Excel selezione</button></div>
    <div class="comparison-body">${sameAsset?'<p class="comparison-warning">Annunci dello stesso asset: fonti diverse, non opportunità distinte.</p>':''}${warning?'<p class="comparison-warning">Valute o operazioni diverse o mancanti: prezzi non confrontabili direttamente.</p>':''}
    ${comparisonSections.map((section,i)=>`<section id="compare-panel-${section.id}" role="tabpanel" aria-labelledby="compare-tab-${section.id}" tabindex="0" ${i?'hidden':''}>
    <div class="comparison-table-wrap"><table class="compare-table decision-comparison" data-count="${properties.length}"><caption class="sr-only">${e(section.label)}: ${properties.length} immobili selezionati</caption><thead><tr><th scope="col">${e(section.label)}</th>${properties.map((p,index)=>`<th scope="col"><span class="compare-city">${index+1} · ${e(p.city||'Comune non indicato')}${p.zone?' · '+e(p.zone):''}</span><button data-action="property" data-id="${e(p.id)}">${e(p.title)}</button></th>`).join('')}</tr></thead>
    <tbody>${section.rows.map(([name,render])=>`<tr><th scope="row">${e(name)}</th>${properties.map((p,index)=>`<td><span class="comparison-mobile-asset" aria-hidden="true">${index+1} · ${e(p.city||'Immobile')}</span>${render(p)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
    <details class="comparison-method"><summary>Come leggere il confronto</summary><p>${e(section.note)}</p></details></section>`).join('')}</div>`;
}
export function setupComparison(dialog){
  const tabs=[...dialog.querySelectorAll('[role="tab"]')];
  const activate=tab=>{
    for(const item of tabs){const selected=item===tab;item.setAttribute('aria-selected',String(selected));item.tabIndex=selected?0:-1;dialog.querySelector('#'+item.getAttribute('aria-controls')).hidden=!selected;}
    dialog.querySelector('.comparison-body').scrollTop=0;
  };
  for(const tab of tabs){
    tab.addEventListener('click',()=>activate(tab));
    tab.addEventListener('keydown',event=>{
      let index=tabs.indexOf(tab);
      if(event.key==='ArrowRight')index=(index+1)%tabs.length;
      else if(event.key==='ArrowLeft')index=(index+tabs.length-1)%tabs.length;
      else if(event.key==='Home')index=0;
      else if(event.key==='End')index=tabs.length-1;
      else return;
      event.preventDefault();activate(tabs[index]);tabs[index].focus();
    });
  }
}
