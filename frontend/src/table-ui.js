// Shared pieces of the data pages (Broker, Lavorazione, Prezzi di zona, Segnali, Qualità, Inbox, Esecuzioni).
import {e} from './utils.js';

// it-IT leaves four-digit numbers ungrouped ("2349"); in columns every figure groups the same way.
const formats=new Map();
export function grouped(value,decimals=0){
  if(value==null||value===''||!Number.isFinite(Number(value)))return '—';
  if(!formats.has(decimals))formats.set(decimals,new Intl.NumberFormat('it-IT',{maximumFractionDigits:decimals,useGrouping:'always'}));
  return formats.get(decimals).format(Number(value));
}
// EUR is the house currency; any other currency is named on the value itself.
export function money(value,currency='EUR',decimals=0){
  if(value==null)return '—';
  if(currency==='EUR')return `€ ${grouped(value,decimals)}`;
  return `${grouped(value,decimals)} ${currency==='XXX'||!currency?'(valuta n.d.)':e(currency)}`;
}
// One metric: label, value, then a 12px detail line that may end in a link. Same type as the Oggi metric cards.
export function metric({label,value,detail='',link=''}){
  return `<div class="pg-stat"><dt class="metric-label">${e(label)}</dt><dd class="metric-value">${value}</dd>${detail||link?`<dd class="metric-detail">${detail?`<span>${detail}</span>`:''}${link}</dd>`:''}</div>`;
}
// A strip of metrics in one bordered band instead of a row of boxed cards.
export const statStrip=items=>`<dl class="pg-stats">${items.map(metric).join('')}</dl>`;
export const plural=(n,one,many)=>`${grouped(n)} ${n===1?one:many}`;
