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
// A compact strip of figures: label, value, optional detail or link.
export function statStrip(items){
  return `<dl class="pg-stats">${items.map(x=>`<div class="pg-stat"><dt>${e(x.label)}</dt><dd><strong>${x.value}</strong>${x.detail?`<span>${x.detail}</span>`:''}</dd></div>`).join('')}</dl>`;
}
export const plural=(n,one,many)=>`${grouped(n)} ${n===1?one:many}`;
