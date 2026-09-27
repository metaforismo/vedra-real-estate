// Decision signals shared by table, Oggi and the property sheet.
// Every number comes from `signals` computed server-side; missing data stays visible as missing.
import {e,num,amount} from './utils.js';

const SHORT={to_renovate:'da ristrutturare',renovated:'ristrutturato',new:'nuovo'};

// "15% sotto" reads faster than "-15%", and avoids confusing sign conventions with the benchmark discount.
export function deltaText(value){
  if(value==null)return '';
  if(Math.abs(value)<.5)return 'in linea';
  return `${num(Math.abs(value),0)}% ${value<0?'sotto':'sopra'}`;
}
const deltaClass=value=>value==null?'':value<=-.5?'below':value>=.5?'above':'even';

export function ageText(days){
  if(days==null)return null;
  if(days<1)return 'oggi';
  if(days===1)return '1 giorno';
  if(days<60)return `${num(days)} giorni`;
  if(days<365)return `${num(Math.floor(days/30))} mesi`;
  const years=Math.floor(days/365);
  return years===1?'oltre 1 anno':`oltre ${num(years)} anni`;
}
// Without a declared publication date we only know when Vedra first saw it: a lower bound, shown as "≥".
const ageValue=sig=>`${sig.listed_basis==='published'?'':'≥ '}${ageText(sig.days_listed)}`;

function reductionText(r,long=false){
  if(!r?.count)return long?'Nessun ribasso osservato':'';
  const count=r.count===1?'1 ribasso':`${num(r.count)} ribassi`;
  return r.total_pct!=null?`${count} · ${num(r.total_pct,1)}%`:count;
}

// Like-for-like first: same condition median, then OMI, then the configured screening benchmark.
function primaryComparison(p){
  const m=p.signals?.market;
  const same=m?.refs?.find(r=>r.key===m.same_condition_key&&r.delta_pct!=null);
  if(same)return {value:same.delta_pct,label:`vs ${SHORT[same.key]} · ${num(same.count)} annunci`};
  if(m?.omi?.delta_pct!=null)return {value:m.omi.delta_pct,label:'vs OMI medio'};
  if(p.discount!=null)return {value:-p.discount,label:'vs benchmark'};
  return null;
}

export function marketCell(p){
  const c=primaryComparison(p);
  if(!c)return '<span class="muted">—</span><small>Confronto non disponibile</small>';
  return `<span class="signal-delta ${deltaClass(c.value)}">${deltaText(c.value)}</span><small>${e(c.label)}</small>`;
}

export function ageCell(p){
  const sig=p.signals;
  if(!sig||sig.days_listed==null)return '<span class="muted">—</span>';
  const reduced=reductionText(sig.reductions);
  return `<span title="${sig.listed_basis==='published'?'Dalla data di pubblicazione dichiarata':'Dalla prima rilevazione: l’annuncio può essere più vecchio'}">${e(ageValue(sig))}</span>${reduced?`<small class="signal-reduced">${e(reduced)}</small>`:''}`;
}

// Only a declared direct route adds information here; plain recapiti are in the contact section below.
function contactChip(c){
  if(c?.route==='owner_declared')return chip('Proprietario dichiarato','good');
  if(c?.route==='mandate_declared')return chip('Esclusiva dichiarata','good');
  return '';
}
const chip=(text,tone='',title='')=>`<span class="signal-chip ${tone}" ${title?`title="${e(title)}"`:''}>${e(text)}</span>`;

// Compact line for Oggi rows: only facts that are present, so the row never fills with "n.d.".
export function signalLine(p){
  const sig=p.signals;if(!sig)return '';
  const c=primaryComparison(p),parts=[];
  if(c)parts.push(`<span class="signal-delta ${deltaClass(c.value)}">${deltaText(c.value)}</span> ${e(c.label)}`);
  if(sig.days_listed!=null)parts.push(`Online da ${e(ageValue(sig))}`);
  const reduced=reductionText(sig.reductions);
  if(reduced)parts.push(`<span class="signal-reduced">${e(reduced)}</span>`);
  if(sig.change_of_use)parts.push('Cambio d’uso dichiarato');
  return parts.length?`<p class="signal-line">${parts.map(x=>`<span class="signal-part">${x}</span>`).join('')}</p>`:'';
}

export function signalFacts(p){
  const sig=p.signals;if(!sig)return '';
  const rows=[
    ['Online da',sig.days_listed==null?'Non indicato':ageValue(sig),sig.listed_since?`${sig.listed_basis==='published'?'pubblicato':'prima rilevazione'} ${new Date(sig.listed_since+'T12:00:00').toLocaleDateString('it-IT',{day:'numeric',month:'short',year:'numeric'})}`:''],
    ['Ribassi',reductionText(sig.reductions,true),sig.reductions?.from_price!=null?`da ${amount(sig.reductions.from_price,p.currency)}`:''],
    ['Catasto',sig.cadastral?short(sig.cadastral):'Non indicato',sig.cadastral?'dichiarato':''],
    ['Cambio d’uso',sig.change_of_use?'Dichiarato':'Non indicato',''],
  ];
  return `<dl class="signal-facts">${rows.map(([k,v,d])=>`<div><dt>${e(k)}</dt><dd>${e(v)}</dd>${d?`<small>${d}</small>`:''}</div>`).join('')}</dl>${sig.change_of_use?`<blockquote class="signal-quote">${e(sig.change_of_use)}</blockquote>`:''}${contactChip(sig.contact)?`<div class="signal-chips">${contactChip(sig.contact)}</div>`:''}`;
}
const short=text=>{const m=String(text).match(/\b[A-F]\s*\/\s*\d{1,2}\b/i);return m?m[0].replace(/\s+/g,'').toUpperCase():String(text).slice(0,40);};

// Dot plot: one row per reference on a shared €/m² scale, the asking price as a vertical rule.
export function priceLadder(p){
  const m=p.signals?.market;if(!m)return '';
  const cur=m.currency||p.currency,ask=m.price_sqm;
  const rows=(m.refs||[]).map(r=>({label:r.label,key:r.key,mid:r.median_sqm,lo:r.q1_sqm,hi:r.q3_sqm,delta:r.delta_pct,note:r.median_sqm==null?(r.reason?.startsWith('Dati mancanti')?r.reason:r.count?`${num(r.count)} di 3 annunci necessari`:'Nessun comparabile'):`${num(r.count)} annunci · ${num(r.source_count)} ${r.source_count===1?'fonte':'fonti'}`,same:r.key===m.same_condition_key}));
  const o=m.omi;
  rows.push(o?{label:'OMI',key:'omi',mid:o.mid_sqm,lo:o.min_sqm,hi:o.max_sqm,delta:o.stale?null:o.delta_pct,note:`${o.period||''}${o.stale?' · da aggiornare':''}`,range:true}:{label:'OMI',key:'omi',mid:null,note:'Quotazione non disponibile'});
  // The screening benchmark is a different, configured source: shown last and labeled as such.
  const b=p.benchmark;
  if(b?.min_sqm!=null&&b?.max_sqm!=null){const mid=(b.min_sqm+b.max_sqm)/2;rows.push({label:'Benchmark',key:'benchmark',mid,lo:b.min_sqm,hi:b.max_sqm,delta:ask!=null?(ask/mid-1)*100:null,note:b.source_label||'Configurato',range:true});}
  const values=rows.flatMap(r=>[r.lo,r.hi,r.mid]).filter(v=>v!=null);
  if(!values.length){
    const reason=(m.refs||[]).find(r=>r.reason?.startsWith('Dati mancanti'))?.reason;
    return `<div class="ladder-empty"><strong>Nessun riferimento di prezzo per questo annuncio</strong><span>${e(reason||'Servono almeno 3 annunci confrontabili in zona o una quotazione OMI.')}</span></div>`;
  }
  if(ask!=null)values.push(ask);
  const min=Math.min(...values)*.9,max=Math.max(...values)*1.06,pos=v=>((v-min)/(max-min)*100).toFixed(2);
  const track=(r,row)=>{
    if(r.mid==null)return `<div class="ladder-track empty" style="grid-row:${row}"></div>`;
    const band=r.lo!=null&&r.hi!=null?`<span class="ladder-band ${r.range?'omi':''}" style="left:${pos(r.lo)}%;width:${(pos(r.hi)-pos(r.lo)).toFixed(2)}%"></span>`:'';
    const tip=r.range?`${r.label}: ${num(r.lo)}–${num(r.hi)} €/m²`:`${r.label}: mediana ${num(r.mid)} €/m²${r.lo!=null?` · 50% centrale ${num(r.lo)}–${num(r.hi)}`:''}`;
    return `<div class="ladder-track" style="grid-row:${row}">${band}${r.range?'':`<span class="ladder-dot" style="left:${pos(r.mid)}%" title="${e(tip)}"></span>`}</div>`;
  };
  const value=r=>r.mid==null?'<span class="muted">—</span>':r.range?`${num(r.lo)}–${num(r.hi)}`:num(r.mid);
  // The asking rule lives in the track column so its x matches the dots exactly at any width.
  const askX=ask==null?null:Math.min(100,Math.max(0,pos(ask)));
  const anchor=askX==null?'':askX>70?'end':askX<30?'start':'middle';
  return `<figure class="price-ladder" aria-label="Prezzo richiesto al metro quadro confrontato con i riferimenti di mercato">
    <div class="ladder-grid" style="--ladder-rows:${rows.length}">
    <span class="ladder-unit">€/m²</span><div class="ladder-head">${askX!=null?`<span class="ladder-ask-label ${anchor}" style="left:${askX}%">Richiesta <strong>${amount(ask,cur)}</strong></span>`:''}</div><span></span>
    ${askX!=null?`<div class="ladder-ask-col" aria-hidden="true"><span class="ladder-ask" style="left:${askX}%"></span></div>`:''}
    ${rows.map((r,i)=>`<div class="ladder-label ${r.mid==null?'missing':''} ${r.same?'same':''}" style="grid-row:${i+2}"><strong>${e(r.label)}</strong><small>${e(r.note)}</small></div>${track(r,i+2)}<div class="ladder-value ${r.mid==null?'missing':''}" style="grid-row:${i+2}"><strong>${value(r)}</strong>${r.delta!=null&&ask!=null?`<small class="signal-delta ${deltaClass(r.delta)}">${deltaText(r.delta)}</small>`:''}</div>`).join('')}</div>
    <figcaption>Mediane dei prezzi richiesti in zona, stessa tipologia, ultimi 90 giorni. OMI: fascia ufficiale.</figcaption></figure>`;
}
