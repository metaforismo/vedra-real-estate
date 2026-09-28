import {icon} from './icons.js';
import {e} from './utils.js';
export const action = (name, text, ico = '', cls = 'btn', extra = '') => `<button class="${cls}" data-action="${name}" ${extra}>${ico?icon(ico):''}${text}</button>`;
export const badge = (text, style='neutral') => `<span class="badge ${style}"><span class="status-dot"></span>${e(text)}</span>`;
export function empty(title, text, button='', ico='layers') {
  return `<div class="empty-state"><div class="empty-icon">${icon(ico)}</div><h3>${e(title)}</h3>${text?`<p>${e(text)}</p>`:''}${button}</div>`;
}
const noticeIcons={warning:'warning',danger:'alert',error:'alert',success:'checkCircle',info:'info'};
export function notice(text, type='info') {return `<div class="notice ${type}">${icon(noticeIcons[type]||'info')}<div>${text}</div></div>`;}
export function pageHeading(kicker,title,description,buttons='') {
  return `<div class="page-heading"><div><h1>${e(title)}</h1></div><div class="heading-actions">${buttons}</div></div>`;
}

export function panelHeading(title, detail='', trailing='') {
  return `<div class="panel-heading"><div><h2>${e(title)}</h2>${detail?`<p>${e(detail)}</p>`:''}</div>${trailing}</div>`;
}
export function metricCard(title, value, detail, ico) {
  return `<section class="metric-card"><div class="metric-label"><span class="metric-icon">${icon(ico)}</span>${e(title)}</div><div class="metric-value">${value}</div><p class="metric-detail">${e(detail)}</p></section>`;
}
export function propertyThumb(property, cls='') {
  const photo=Array.isArray(property.images) && property.images.length;
  return `<span class="property-thumb ${e(cls)}"><span class="photo-placeholder" aria-label="Foto non disponibile">${icon('building')}<span>Foto non disponibile</span></span>${photo?`<img class="listing-photo" src="/api/properties/${encodeURIComponent(property.id)}/image" alt="Foto dell’annuncio" loading="lazy" decoding="async" referrerpolicy="no-referrer">`:''}</span>`;
}
// Recapiti: one rendering everywhere (Oggi, Broker, Confronto). Only the country code is split off:
// Italian numbers have no fixed grouping and a wrong split misleads. Invalid values are never linked.
export const phoneText=phone=>phone.startsWith('+39')?`+39 ${phone.slice(3)}`:phone;
const validPhone=value=>{const tel=String(value||'').replace(/[^\d+]/g,'');return /^\+?\d{6,16}$/.test(tel)?tel:'';};
const validEmail=value=>/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(value||'')?value:'';
// `after` is the row's single secondary action (e.g. "Registra esito"), laid out on the same line.
export function contactActions(contact, {size='', after=''}={}) {
  const c=contact||{}, phone=validPhone(c.telephone??c.phone), email=validEmail(c.email);
  if(!phone&&!email&&!after)return '';
  const cls=`contact-action${size==='sm'?' small':''}`;
  return `<div class="contact-actions">${phone?`<a class="${cls}" href="tel:${e(phone)}">${icon('phone')}<span>${e(phoneText(phone))}</span></a>`:''}${email?`<a class="${cls}" href="mailto:${encodeURIComponent(email)}" title="${e(email)}">${icon('mail')}<span>Email</span></a>`:''}${after}</div>`;
}
