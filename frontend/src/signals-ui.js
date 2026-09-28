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
const ageValue=sig=>sig.days_listed<1?(sig.listed_basis==='published'?'oggi':'rilevato oggi'):`${sig.listed_basis==='published'?'':'≥ '}${ageText(sig.days_listed)}`;
const ageChip=sig=>sig.days_listed<1?'Nuovo oggi':`Online da ${ageValue(sig)}`;

function reductionText(r){
  if(!r?.count)return '';
  const count=r.count===1?'1 ribasso':`${num(r.count)} ribassi`;
  return r.total_pct!=null?`${count} · ${num(r.total_pct,1)}%`:count;
}

// Like-for-like first: same condition median, then OMI, then the configured screening benchmark.
function primaryComparison(p){
  const m=p.signals?.market;
  const same=m?.refs?.find(r=>r.key===m.same_condition_key&&r.delta_pct!=null);
  if(same)return {value:same.delta_pct,label:`vs ${SHORT[same.key]} · ${num(same.count)} annunci`,count:same.count,basis:`${num(same.count)} comparabili`};
  if(m?.omi?.delta_pct!=null)return {value:m.omi.delta_pct,label:'vs OMI medio',basis:'OMI medio'};
  if(p.discount!=null)return {value:-p.discount,label:'vs prezzo di zona',basis:'prezzo di zona'};
  return null;
}

// `compact` is for the archive table: the column header already says "vs mercato", so the second line
// names only the basis, and the full comparison stays in the tooltip.
export function marketCell(p,{compact=false}={}){
  const c=primaryComparison(p);
  if(!c)return compact?'<span class="muted" title="Confronto non disponibile">—</span>':'<span class="muted">—</span><small>Confronto non disponibile</small>';
  // The plain zone benchmark is the default basis (see the column tooltip); only the others are spelled out.
  if(compact)return `<span class="signal-delta ${deltaClass(c.value)}" title="${e(c.label)}">${deltaText(c.value)}</span>${c.basis==='prezzo di zona'?'':`<small>${e(c.basis)}</small>`}`;
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

// Oggi rows read as one sentence of evidence: the market gap leads, then age, cuts and declared use.
// Only facts that are present, so the row never fills with "n.d.".
export function signalSummary(p){
  const sig=p.signals;if(!sig)return '';
  const c=primaryComparison(p),parts=[];
  // The comparable count stays in the sentence: "15% sotto 12 comparabili" says how solid the gap is.
  const target=c&&(c.label.startsWith('vs OMI')?'la media OMI':c.label.startsWith('vs prezzo di zona')?'il prezzo di zona':`${num(c.count)} comparabili`);
  if(c)parts.push(deltaClass(c.value)==='even'?`<span class="why-lead even">In linea</span> con ${target}`:`<span class="why-lead ${deltaClass(c.value)}">${deltaText(c.value)}</span> ${target}`);
  if(sig.days_listed!=null)parts.push(e(ageChip(sig)));
  const reduced=reductionText(sig.reductions);
  if(reduced)parts.push(`<span class="why-cut">${e(reduced)}</span>`);
  if(sig.change_of_use)parts.push('Cambio d’uso dichiarato');
  return parts.length?`<p class="today-why">${parts.map(x=>`<span>${x}</span>`).join('')}</p>`:'';
}

export function signalLine(p){
  const sig=p.signals;if(!sig)return '';
  const c=primaryComparison(p),parts=[];
  if(c)parts.push(`<span class="signal-delta ${deltaClass(c.value)}">${deltaText(c.value)}</span> ${e(c.label)}`);
  if(sig.days_listed!=null)parts.push(e(ageChip(sig)));
  const reduced=reductionText(sig.reductions);
  if(reduced)parts.push(`<span class="signal-reduced">${e(reduced)}</span>`);
  if(sig.change_of_use)parts.push('Cambio d’uso dichiarato');
  return parts.length?`<p class="signal-line">${parts.map(x=>`<span class="signal-part">${x}</span>`).join('')}</p>`:'';
}

// Hero figure of the sheet: the same like-for-like comparison the table shows, in words.
export function marketPosition(p){
  const c=primaryComparison(p);
  return c?{text:deltaText(c.value),tone:deltaClass(c.value),label:c.label}:null;
}

export function signalFacts(p){
  const sig=p.signals;if(!sig)return '';
  const listed=sig.listed_since?new Date(sig.listed_since+'T12:00:00').toLocaleDateString('it-IT',{day:'numeric',month:'short',year:'numeric'}):'';
  const rows=[
    ['Online da',sig.days_listed==null?null:ageValue(sig),listed?`${sig.listed_basis==='published'?'Pubblicato':'Prima rilevazione'} ${listed}`:''],
    ['Ribassi',sig.reductions?.count?reductionText(sig.reductions):'Nessuno osservato',sig.reductions?.from_price!=null?`da ${amount(sig.reductions.from_price,p.currency)}`:''],
    ['Catasto',sig.cadastral?short(sig.cadastral):null,sig.cadastral?'Dichiarato nell’annuncio':''],
    ['Cambio d’uso',sig.change_of_use?'Dichiarato':null,''],
  ];
  // Missing values stay in place, quieter than observed ones, so the strip never changes shape.
  return `<dl class="signal-facts">${rows.map(([k,v,d])=>`<div class="${v==null?'missing':''}"><dt>${e(k)}</dt><dd>${e(v??'Non indicato')}</dd>${d?`<small>${d}</small>`:''}</div>`).join('')}</dl>${sig.change_of_use?`<blockquote class="signal-quote">${e(sig.change_of_use)}</blockquote>`:''}${contactChip(sig.contact)?`<div class="signal-chips">${contactChip(sig.contact)}</div>`:''}`;
}
const short=text=>{const m=String(text).match(/\b[A-F]\s*\/\s*\d{1,2}\b/i);return m?m[0].replace(/\s+/g,'').toUpperCase():String(text).slice(0,40);};

// Difference between asking and renovated/new medians, times the surface. A data point, not a margin:
// works, taxes and time are the analyst's to add (Scenario economico does that explicitly).
function headroom(p,m,ask,cur){
  const surface=p.surface;if(ask==null||!surface)return '';
  const pick=key=>m.refs?.find(r=>r.key===key&&r.median_sqm!=null);
  const parts=[['renovated','ristrutturato'],['new','nuovo']].map(([key,name])=>{const r=pick(key);if(!r)return '';const gap=r.median_sqm-ask;
    return `<div class="headroom-item"><span>Verso ${name}</span><strong>${gap>0?'+':''}${amount(Math.round(gap),cur)}/m²</strong><small>${amount(Math.round(gap*surface/1000)*1000,cur)} su ${num(surface)} m²</small></div>`;}).filter(Boolean);
  return parts.length?`<div class="ladder-headroom">${parts.join('')}<p>Mediana meno richiesta, prima di lavori, imposte e tempi.</p></div>`:'';
}

// Three or four round values inside the scale, so a position on the track can be read without hovering.
function ticks(min,max){
  const raw=(max-min)/4,pow=10**Math.floor(Math.log10(raw));
  const step=[1,2,2.5,5,10].map(f=>f*pow).find(s=>s>=raw)||pow*10;
  const out=[];for(let v=Math.ceil(min/step)*step;v<max;v+=step)out.push(v);
  return out;
}

// Dot plot: one row per reference on a shared €/m² scale, the asking price as a vertical rule.
export function priceLadder(p){
  const m=p.signals?.market;if(!m)return '';
  const cur=m.currency||p.currency,ask=m.price_sqm;
  const rows=(m.refs||[]).map(r=>({label:r.label,key:r.key,mid:r.median_sqm,lo:r.q1_sqm,hi:r.q3_sqm,delta:r.delta_pct,note:r.median_sqm==null?(r.reason?.startsWith('Dati mancanti')?r.reason:r.count?`${num(r.count)} di 3 annunci necessari`:'Nessun comparabile'):`${num(r.count)} annunci · ${num(r.source_count)} ${r.source_count===1?'fonte':'fonti'}`,same:r.key===m.same_condition_key}));
  const o=m.omi;
  rows.push(o?{label:'OMI',key:'omi',mid:o.mid_sqm,lo:o.min_sqm,hi:o.max_sqm,delta:o.stale?null:o.delta_pct,note:`${o.period||''}${o.stale?' · da aggiornare':''}`,range:true}:{label:'OMI',key:'omi',mid:null,note:'Quotazione non disponibile'});
  // The screening benchmark is a different, configured source: shown last and labeled as such.
  const b=p.benchmark;
  if(b?.min_sqm!=null&&b?.max_sqm!=null){const mid=(b.min_sqm+b.max_sqm)/2;rows.push({label:'Benchmark',key:'prezzo di zona',mid,lo:b.min_sqm,hi:b.max_sqm,delta:ask!=null?(ask/mid-1)*100:null,note:b.source_label||'Configurato',range:true});}
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
    return `<div class="ladder-track" style="grid-row:${row}" title="${e(tip)}">${band}${r.range?'':`<span class="ladder-dot" style="left:${pos(r.mid)}%"></span>`}</div>`;
  };
  const value=r=>r.mid==null?'<span class="muted">—</span>':r.range?`${num(r.lo)}–${num(r.hi)}`:num(r.mid);
  // The asking rule lives in the track column so its x matches the dots exactly at any width.
  const askX=ask==null?null:Math.min(100,Math.max(0,pos(ask)));
  const anchor=askX==null?'':askX>70?'end':askX<30?'start':'middle';
  const axis=ticks(min,max).map(v=>`<span style="left:${pos(v)}%">${num(v)}</span>`).join('');
  const hasBand=rows.some(r=>!r.range&&r.lo!=null&&r.mid!=null),hasRange=rows.some(r=>r.range&&r.mid!=null);
  return `<figure class="price-ladder" aria-label="Prezzo richiesto al metro quadro confrontato con i riferimenti di mercato">
    <div class="ladder-grid" style="--ladder-rows:${rows.length}">
    <span class="ladder-unit">€/m²</span><div class="ladder-head">${askX!=null?`<span class="ladder-ask-label ${anchor}" style="left:${askX}%">Richiesta <strong>${amount(ask,cur)}</strong></span>`:''}</div><span></span>
    ${askX!=null?`<div class="ladder-ask-col" aria-hidden="true"><span class="ladder-ask" style="left:${askX}%"></span></div>`:''}
    ${rows.map((r,i)=>`<div class="ladder-label ${r.mid==null?'missing':''} ${r.same?'same':''}" style="grid-row:${i+2}"><strong>${e(r.label)}${r.same?'<span class="ladder-same">stesso stato</span>':''}</strong><small>${e(r.note)}</small></div>${track(r,i+2)}<div class="ladder-value ${r.mid==null?'missing':''}" style="grid-row:${i+2}"><strong>${value(r)}</strong>${r.delta!=null&&ask!=null?`<small class="signal-delta ${deltaClass(r.delta)}">${deltaText(r.delta)}</small>`:''}</div>`).join('')}
    <div class="ladder-axis" aria-hidden="true" style="grid-row:${rows.length+2}">${axis}</div></div>
    <figcaption><span class="ladder-legend" aria-hidden="true"><span><i class="legend-dot"></i>Mediana</span>${hasBand?'<span><i class="legend-band"></i>50% centrale</span>':''}${hasRange?'<span><i class="legend-range"></i>Fascia OMI</span>':''}${askX!=null?'<span><i class="legend-rule"></i>Richiesta</span>':''}</span><span>Prezzi richiesti in zona, stessa tipologia, ultimi 90 giorni.</span></figcaption>
    ${headroom(p,m,ask,cur)}</figure>`;
}
