import {icon} from './icons.js';
import {e} from './utils.js';
export const action = (name, text, ico = '', cls = 'btn', extra = '') => `<button class="${cls}" data-action="${name}" ${extra}>${ico?icon(ico):''}${text}</button>`;
export const badge = (text, style='neutral') => `<span class="badge ${style}"><span class="status-dot"></span>${e(text)}</span>`;
export function empty(title, text, button='') {
  return `<div class="empty-state"><div class="empty-icon">${icon('layers')}</div><h3>${e(title)}</h3><p>${e(text)}</p>${button}</div>`;
}
export function notice(text, type='info') {return `<div class="notice ${type}">${icon(type==='warning'?'warning':'info')}<div>${text}</div></div>`;}
export function pageHeading(kicker,title,description,buttons='') {
  return `<div class="page-heading"><div><div class="eyebrow">${e(kicker)}</div><h1>${e(title)}</h1><p>${e(description)}</p></div><div class="heading-actions">${buttons}</div></div>`;
}
