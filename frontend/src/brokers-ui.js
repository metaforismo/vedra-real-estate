// Broker directory: who publishes which assets, grouped by phone/e-mail across all sources.
import {api} from './api.js';
import {icon} from './icons.js';
import {e,num,euro,amount,selectOptions,label} from './utils.js';
import {empty,pageHeading} from './ui.js';
import {createRequestGuard} from './request-guard.js';

const PRICES=[['','Qualsiasi prezzo'],['500000','Da € 500k'],['1000000','Da € 1 M'],['2000000','Da € 2 M'],['4000000','Da € 4 M']];
export const brokerState=()=>({filters:{q:'',city:'',min_price:'',direct_only:false},data:null,loading:false,error:'',open:{}});

function phoneLink(phone){
  const tel=String(phone||'').replace(/[^\d+]/g,'');
  return /^\+?\d{6,16}$/.test(tel)?`<a class="btn small-btn" href="tel:${e(tel)}">${icon('phone')}${e(phone)}</a>`:'';
}

function row(b,s){
  const open=Boolean(s.brokers.open[b.id]);
  const who=b.organization&&b.name&&b.organization!==b.name?`<small>${e(b.organization)}</small>`:'';
  return `<article class="broker-row ${open?'open':''}">
    <div class="broker-who"><strong>${e(b.name||b.organization||'Inserzionista senza nome')}</strong>${who}
      ${b.direct?`<span class="signal-chip good">${num(b.direct)} ${b.direct===1?'diretto dichiarato':'diretti dichiarati'}</span>`:''}</div>
    <div class="broker-book"><strong>${num(b.count)} ${b.count===1?'annuncio':'annunci'}</strong><small>${b.value_eur?`${euro(b.value_eur,true)} in totale · fino a ${euro(b.max_price_eur,true)}`:'Valore non indicato'}</small>
      <span class="broker-zones">${[...b.cities.slice(0,2),...b.zones.slice(0,3)].map(z=>`<span>${e(z)}</span>`).join('')}</span></div>
    <div class="broker-reach">${phoneLink(b.phone)}${b.email?`<a class="btn small-btn" href="mailto:${encodeURIComponent(b.email)}">Email</a>`:''}${!b.phone&&!b.email?'<small class="muted">Recapito da trovare</small>':''}</div>
    <button class="broker-toggle" data-action="broker-toggle" data-id="${e(b.id)}" aria-expanded="${open}" aria-label="${open?'Nascondi':'Mostra'} annunci di ${e(b.name||b.organization||'inserzionista')}">${icon('chevron')}</button>
    ${open?`<ul class="broker-listings">${b.listings.map(l=>`<li><button class="plain-link" data-action="property" data-id="${e(l.id)}">${e(l.title)}</button><span>${[l.city,l.zone].filter(Boolean).map(e).join(' · ')}</span><strong>${amount(l.price,l.currency)}</strong><span>${l.route?`<span class="signal-chip good">${e(l.route)}</span>`:''}</span></li>`).join('')}${b.count>b.listings.length?`<li class="muted small">Mostrati i ${num(b.listings.length)} di prezzo più alto.</li>`:''}</ul>`:''}
  </article>`;
}

export function brokersView(s){
  const st=s.brokers,f=st.filters,d=st.data;
  const cities=[...new Set((s.catalog?.facets?.cities||[]).concat(s.data.agents.map(a=>a.city)))].filter(Boolean).sort();
  const summary=d?`${num(d.total)} ${d.total===1?'inserzionista':'inserzionisti'} su ${num(d.examined)} annunci${d.unattributed?` · ${num(d.unattributed)} senza recapito`:''}`:'';
  const body=st.error?`<div class="catalog-error" role="alert"><strong>Elenco non disponibile</strong><p>${e(st.error)}</p><button class="btn" data-action="brokers-retry">${icon('refresh')}Riprova</button></div>`
    :!d?`<div class="catalog-loading" role="status"><span class="catalog-loader"></span>Raccolta degli inserzionisti…</div>`
    :d.items.length?`<div class="broker-list" aria-busy="${st.loading}">${d.items.map(b=>row(b,s)).join('')}</div>${d.limited?'<p class="small muted broker-limit">Mostrati i primi 200: restringi i filtri.</p>':''}`
    :empty('Nessun inserzionista con questi filtri','I recapiti compaiono quando Scout o l’importazione li trovano negli annunci.');
  return `${pageHeading('','Broker','')}
    <p class="page-summary">${summary}</p>
    <section class="catalog-surface broker-surface"><div class="broker-filters">
      <div class="search-input">${icon('search')}<input id="broker-search" type="search" value="${e(f.q)}" maxlength="200" placeholder="Nome, agenzia o zona" aria-label="Cerca broker"></div>
      <label class="filter-select"><span class="sr-only">Comune</span><select id="broker-city" aria-label="Comune">${selectOptions([['','Tutti i comuni'],...cities.map(c=>[c,c])],f.city)}</select></label>
      <label class="filter-select"><span class="sr-only">Prezzo minimo</span><select id="broker-price" aria-label="Prezzo minimo degli annunci">${selectOptions(PRICES,f.min_price)}</select></label>
      <button class="filter-button ${f.direct_only?'active':''}" data-action="broker-direct" aria-pressed="${f.direct_only}">${icon('check')} Solo diretti</button>
    </div>${body}</section>`;
}

export function createBrokersController({s,render:draw,request=api}){
  s.brokers=brokerState();
  // Results re-render the page: keep the field the user is typing in focused, caret included.
  const render=()=>{const a=document.activeElement,id=a?.id,pos=a?.selectionStart;draw();
    const n=id&&document.getElementById(id);if(n){n.focus({preventScroll:true});if(pos!=null&&n.setSelectionRange)try{n.setSelectionRange(pos,pos);}catch{/* not a text field */}}};
  const guard=createRequestGuard();let abort=null,timer=null;
  async function load({delay=0}={}){
    clearTimeout(timer);
    if(delay){timer=setTimeout(()=>load(),delay);return;}
    if(s.page!=='brokers')return;
    guard.invalidate();abort?.abort();abort=new AbortController();const current=guard.capture();
    const st=s.brokers,f=st.filters;st.loading=true;st.error='';
    const query=new URLSearchParams({q:f.q,city:f.city,direct_only:String(f.direct_only)});
    if(f.min_price)query.set('min_price',f.min_price);
    try{
      const data=await request('/brokers?'+query,{signal:abort.signal});
      if(!current()||s.page!=='brokers')return;
      st.data=data;st.loading=false;
    }catch(error){
      if(!current()||error.name==='AbortError')return;
      st.loading=false;st.error=error.message;
    }
    render();
  }
  function cancel(){clearTimeout(timer);guard.invalidate();abort?.abort();}
  return {load,cancel,actions:{
    'broker-toggle'(el){s.brokers.open[el.dataset.id]=!s.brokers.open[el.dataset.id];render();document.querySelector(`[data-action="broker-toggle"][data-id="${CSS.escape(el.dataset.id)}"]`)?.focus({preventScroll:true});},
    'broker-direct'(){s.brokers.filters.direct_only=!s.brokers.filters.direct_only;return load();},
    'brokers-retry'(){return load();},
  },input(target){
    const f=s.brokers.filters;
    if(target.id==='broker-search'){f.q=target.value;load({delay:250});return true;}
    if(target.id==='broker-city'){f.city=target.value;load();return true;}
    if(target.id==='broker-price'){f.min_price=target.value;load();return true;}
    return false;
  }};
}
