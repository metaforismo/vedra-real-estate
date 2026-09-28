import {e,num,amount,label,stamp,safeUrl} from './utils.js';
import {icon} from './icons.js';

export function comparablesContent(p,result){
  const count=result.count??result.items.length,enough=result.median_sqm!=null;
  // Whole euros per m², as in the sheet: the median of asking prices is not precise to the cent.
  const rate=value=>value==null?'—':`${p.currency==='EUR'?'€ ':''}${num(Math.round(value))}${p.currency==='EUR'?'':' '+e(p.currency==='XXX'?'(valuta n.d.)':p.currency)}/m²`;
  const surfaceUnit={commercial:'m² commerciali',gross:'m² lordi',net:'m² netti'}[p.area_basis]||'m² · base non indicata';
  const delta=result.asking_delta_pct;
  const comparison=delta==null?'':delta===0?'Richiesta in linea con la mediana':`Richiesta ${num(Math.abs(delta),1)}% ${delta<0?'sotto':'sopra'} la mediana`;
  return `<div class="modal-body comparables-body">
    <div class="comp-criteria"><span class="comp-criteria-label">Confronto su</span>${[p.city,p.zone,label(p.property_type),label(p.condition)].filter(Boolean).map(v=>`<span>${e(v)}</span>`).join('')}</div>
    <div class="comp-overview"><section class="comp-subject"><span>Immobile in esame</span><strong>${rate(p.price_sqm)}</strong><small>${amount(p.price,p.currency)} · ${num(p.surface)} ${surfaceUnit}</small></section>
    <section class="comp-median"><span>Mediana dei comparabili</span><strong class="${enough?'':'missing'}">${enough?rate(result.median_sqm):'Non disponibile'}</strong><small>${num(count)} annunci · ${num(result.source_count??0)} fonti</small></section>
    ${comparison?`<section class="comp-comparison ${delta<0?'below':''}"><span>Richiesta rispetto alla mediana</span><strong>${e(comparison.replace('Richiesta ',''))}</strong><small>Tra prezzi richiesti, non di vendita.</small></section>`:''}</div>
    ${!enough?`<div class="comp-empty"><strong>${count?'Campione insufficiente':'Nessun comparabile omogeneo'}</strong><p>${e(result.reason)}</p></div>`:''}
    ${result.sample_limited?'<p class="evidence-warning comp-limit">Campione limitato ai 1.000 annunci più recenti della zona.</p>':''}
    ${(result.warnings||[]).filter(w=>!w.startsWith('Mostrati i primi')).map(w=>`<p class="comp-warning">${e(w)}</p>`).join('')}
    ${result.items.length?`<section class="comp-sample"><div class="comp-sample-heading"><h3>Annunci a confronto</h3><span>${result.items.length<count?`${num(result.items.length)} di ${num(count)}`:num(count)} asset</span></div>
    <div class="comparable-list">${result.items.map(row=>`<article class="comparable-row"><div><button class="plain-link" data-action="property" data-id="${e(row.id)}">${e(row.title)}</button><small>${e(row.source||'Fonte non indicata')} · Rilevato ${stamp(row.last_seen||row.observed_at,true)}</small></div><div class="comp-row-price"><strong>${rate(row.price_sqm)}</strong><span>${num(row.surface)} m² · ${amount(row.price,p.currency)}</span></div>${safeUrl(row.url)?`<a class="btn small-btn" href="${safeUrl(row.url)}" target="_blank" rel="noopener noreferrer">Fonte<span class="sr-only">: ${e(row.title)}</span></a>`:''}</article>`).join('')}</div></section>`:''}
    <details class="comp-method"><summary>Metodo e limiti</summary><p>${e(result.method||result.reason)}</p>${result.q1_sqm!=null?`<dl><div><dt>Fascia centrale del campione</dt><dd>${rate(result.q1_sqm)} – ${rate(result.q3_sqm)}</dd></div><div><dt>Periodo osservato</dt><dd>${stamp(result.oldest_observed,true)} – ${stamp(result.newest_observed,true)}</dd></div></dl><p>La fascia centrale contiene il 50% dei prezzi, non è un intervallo di confidenza. Più fonti non garantiscono indipendenza.</p>`:''}<p>La mediana richiede almeno 3 asset. Il confronto non stima il valore di rivendita o il margine dell’operazione.</p></details>
  </div><div class="modal-form-footer comp-actions"><button class="btn footer-back" data-action="property" data-id="${e(p.id)}">Torna all’immobile</button><a class="btn" href="/api/properties/${e(p.id)}/memo.xlsx">${icon('download')} Excel</a></div>`;
}
