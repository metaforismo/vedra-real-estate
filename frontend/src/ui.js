import {icon} from './icons.js';
import {e} from './utils.js';
export const action = (name, text, ico = '', cls = 'btn', extra = '') => `<button class="${cls}" data-action="${name}" ${extra}>${ico?icon(ico):''}${text}</button>`;
export const badge = (text, style='neutral') => `<span class="badge ${style}"><span class="status-dot"></span>${e(text)}</span>`;
export function empty(title, text, button='') {
  return `<div class="empty-state"><div class="empty-icon">${icon('layers')}</div><h3>${e(title)}</h3><p>${e(text)}</p>${button}</div>`;
}
export function notice(text, type='info') {return `<div class="notice ${type}">${icon(type==='warning'?'warning':'info')}<div>${text}</div></div>`;}
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
