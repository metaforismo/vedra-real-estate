// Broker directory: who publishes which assets, grouped by phone/e-mail across all sources.
import {api} from './api.js';
import {icon} from './icons.js';
import {e,num,selectOptions} from './utils.js';
import {empty,pageHeading} from './ui.js';
import {grouped,money,plural} from './table-ui.js';
import {createRequestGuard} from './request-guard.js';

const PRICES=[['','Qualsiasi prezzo'],['500000','Da € 500.000'],['1000000','Da € 1 milione'],['2000000','Da € 2 milioni'],['4000000','Da € 4 milioni']];
export const brokerState=()=>({filters:{q:'',city:'',min_price:'',direct_only:false},data:null,loading:false,error:'',open:{}});

function phoneLink(phone){
  const tel=String(phone||'').replace(/[^\d+]/g,'');
  return /^\+?\d{6,16}$/.test(tel)?`<a class="broker-contact" href="tel:${e(tel)}">${icon('phone')}${e(phone)}</a>`:'';
}
const who=b=>b.name||b.organization||'Inserzionista senza nome';

function row(b,s){
  const open=Boolean(s.brokers.open[b.id]);
  const org=b.organization&&b.name&&b.organization!==b.name?`<small>${e(b.organization)}</small>`:'';
  // Cities first, then the most frequent micro-zones: one line, the full list on hover.
  const places=[...new Set([...b.cities,...b.zones])];
  const reach=[phoneLink(b.phone),b.email?`<a class="broker-contact" href="mailto:${encodeURIComponent(b.email)}" title="${e(b.email)}">Email</a>`:''].filter(Boolean).join('');
  return `<tr class="is-link broker-tr ${open?'open':''}">
    <td class="broker-name-cell"><button class="pg-link broker-name" data-action="broker-toggle" data-id="${e(b.id)}" aria-expanded="${open}">${e(who(b))}</button>${b.direct?` <span class="pg-tag good" title="Annunci con contatto diretto dichiarato">${num(b.direct)} ${b.direct===1?'diretto':'diretti'}</span>`:''}${org}</td>
    <td class="num"><strong>${grouped(b.count)}</strong><span class="broker-unit"> ${b.count===1?'annuncio':'annunci'}</span></td>
    <td class="num">${b.value_eur?money(b.value_eur):'<span class="pg-muted">—</span>'}</td>
    <td class="num">${b.max_price_eur?money(b.max_price_eur):'<span class="pg-muted">—</span>'}</td>
    <td class="broker-places" title="${e(places.join(', '))}">${places.length?e(places.slice(0,4).join(', '))+(places.length>4?` <span class="pg-muted">+${places.length-4}</span>`:''):'<span class="pg-muted">—</span>'}</td>
    <td class="broker-contacts">${reach||'<span class="pg-muted">Non indicato</span>'}</td>
    <td class="pg-chevron broker-chevron" aria-hidden="true">${icon('chevron')}</td>
  </tr>${open?`<tr class="broker-detail"><td colspan="7"><ul class="broker-sublist">${b.listings.map(l=>`<li><button class="plain-link" data-action="property" data-id="${e(l.id)}">${e(l.title)}</button><span>${[l.city,l.zone].filter(Boolean).map(e).join(' · ')||'—'}</span><span class="num">${l.surface?grouped(l.surface)+' m²':'—'}</span><strong class="num">${money(l.price,l.currency)}</strong><span>${l.route?`<span class="pg-tag good">${e(l.route)}</span>`:''}</span></li>`).join('')}</ul>${b.count>b.listings.length?`<p class="broker-more">Mostrati i ${num(b.listings.length)} di prezzo più alto su ${num(b.count)}.</p>`:''}</td></tr>`:''}`;
}

export function brokersView(s){
  const st=s.brokers,f=st.filters,d=st.data;
  const cities=[...new Set((s.catalog?.facets?.cities||[]).concat(s.data.agents.map(a=>a.city)))].filter(Boolean).sort();
  const summary=d?`${plural(d.total,'inserzionista','inserzionisti')} su ${plural(d.examined,'annuncio','annunci')}${d.unattributed?` · ${grouped(d.unattributed)} senza recapito`:''}`:'';
  const filtered=Boolean(f.q.trim()||f.city||f.min_price||f.direct_only);
  const body=st.error?`<div class="catalog-error" role="alert"><strong>Elenco non disponibile</strong><p>${e(st.error)}</p><button class="btn" data-action="brokers-retry">${icon('refresh')}Riprova</button></div>`
    :!d?`<div class="catalog-loading" role="status"><span class="catalog-loader"></span>Raccolta degli inserzionisti…</div>`
    :d.items.length?`<div class="pg-scroll"><table class="pg-table broker-table" aria-busy="${st.loading}"><thead><tr><th scope="col">Inserzionista</th><th scope="col" class="num">Annunci</th><th scope="col" class="num">Valore in vendita</th><th scope="col" class="num">Prezzo più alto</th><th scope="col">Zone</th><th scope="col">Recapito</th><th scope="col"><span class="sr-only">Annunci</span></th></tr></thead><tbody>${d.items.map(b=>row(b,s)).join('')}</tbody></table></div>${d.limited?'<p class="pg-note">Mostrati i primi 200: restringi i filtri.</p>':''}`
    :empty(filtered?'Nessun inserzionista con questi filtri':'Nessun inserzionista',filtered?'Modifica o azzera i filtri.':'I recapiti compaiono quando Scout o l’importazione li trovano negli annunci.');
  return `${pageHeading('','Broker','')}
    <p class="page-summary">${summary||'&nbsp;'}</p>
    <section class="pg-surface broker-surface"><div class="pg-toolbar">
      <div class="pg-search">${icon('search')}<input id="broker-search" type="search" value="${e(f.q)}" maxlength="200" placeholder="Nome, agenzia o zona" aria-label="Cerca broker"></div>
      <select id="broker-city" aria-label="Comune">${selectOptions([['','Tutti i comuni'],...cities.map(c=>[c,c])],f.city)}</select>
      <select id="broker-price" aria-label="Prezzo minimo degli annunci">${selectOptions(PRICES,f.min_price)}</select>
      <button class="catalog-chip ${f.direct_only?'active':''}" data-action="broker-direct" aria-pressed="${f.direct_only}">Solo diretti</button>
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
