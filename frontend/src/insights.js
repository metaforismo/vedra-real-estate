import {e, num, amount, relative, label} from './utils.js';
import {pageHeading, panelHeading, metricCard, empty, notice} from './ui.js';

export function insightsView(s) {
  const data=s.insights;
  if(!data)return empty('Insight non disponibili', 'Aggiorna il workspace per riprovare.');
  const a=data.archive;
  const segments=data.segments;
  return `${pageHeading('L’ARCHIVIO DEL TEAM','Segnali da approfondire','Cambiamenti osservati, qualità delle fonti e riferimenti confrontabili.')}
    <div class="metrics-grid">${metricCard('Nuovi in 7 giorni', num(a.new_7d),'Prime acquisizioni, non nuove pubblicazioni','building')}
      ${metricCard('Da ricontrollare',num(a.stale_7d),'Non riletti da oltre 7 giorni','clock')}
      ${metricCard('Ribassi osservati',num(data.price_reductions.length),'Ultimo ribasso per annuncio · fino a 20','chart')}
      ${metricCard('Con benchmark',num(a.benchmarked),`${num(a.total)} immobili nell’archivio`,'quality')}</div>
    ${data.actions.length?`<section class="panel next-actions">${panelHeading('Prossime verifiche')}<div>${data.actions.map(x=>`<a href="#${e(x.page)}"><span><strong>${e(x.title)}</strong><small>${e(x.detail)}</small></span><span aria-hidden="true">→</span></a>`).join('')}</div></section>`:''}
    <section class="panel insight-section">${panelHeading('Prezzi richiesti a confronto','Ultimi 90 giorni. Almeno cinque asset omogenei per pubblicare una mediana.')}
    ${segments.length?`<div class="table-scroll"><table class="insight-table"><thead><tr><th>ZONA / TIPO</th><th>STATO / SUPERFICIE</th><th>ASSET</th><th>MEDIANA / M²</th><th>INTERVALLO 25°–75°</th></tr></thead><tbody>${segments.map(x=>`<tr><td><strong>${e(x.city)} · ${e(x.zone)}</strong><small>${e(label(x.property_type))} · ${e(label(x.transaction_type))}</small></td><td>${e(label(x.condition))}<small>${e(x.size_band)} m² · ${e(label(x.area_basis))}</small></td><td>${num(x.n)}</td><td>${x.sufficient?amount(x.median_sqm,x.currency):'<span class="muted">Campione insufficiente</span>'}</td><td>${x.sufficient?`${amount(x.p25_sqm,x.currency)} – ${amount(x.p75_sqm,x.currency)}`:'—'}</td></tr>`).join('')}</tbody></table></div>`:empty('Non ci sono segmenti confrontabili','Servono zona, stato, superficie, valuta e tipologia verificabili. Nessun dato viene completato per supposizione.')}
    <p class="insight-method">${e(data.methodology)} Campione: ${num(data.sample.used)} / ${num(data.sample.observed_listings)} annunci recenti.${data.sample.truncated?' Analisi limitata ai 10.000 più recenti.':''}</p></section>
    <div class="insight-columns"><section class="panel">${panelHeading('Ribassi negli ultimi 30 giorni','Stesso annuncio, stessa valuta e stessa base di confronto.')}
      ${data.price_reductions.length?`<div class="insight-list">${data.price_reductions.map(x=>`<button data-action="property" data-id="${e(x.property_id)}"><span><strong>${e(x.title)}</strong><small>${amount(x.previous_price,x.currency)} → ${amount(x.price,x.currency)} · ${relative(x.observed_at)}</small></span><b class="discount-positive">−${num(x.reduction_pct,1)}%</b></button>`).join('')}</div>`:empty('Nessun ribasso confrontabile','Il confronto inizia con due osservazioni complete e coerenti. I vecchi dati senza contesto non vengono reinterpretati.')}
      ${data.sample.observations_truncated?notice('Storico limitato alle ultime 20.000 osservazioni con contesto.'):''}</section>
      <section class="panel">${panelHeading('Fonti e copertura','Le fonti non raggiungibili non equivalgono a zero opportunità.')}
      ${data.sources.length?`<div class="insight-list">${data.sources.map(x=>`<a href="#sources"><span><strong>${e(x.name)}</strong><small>${x.last_success?'Ultima acquisizione '+relative(x.last_success):'Nessuna acquisizione automatica completata'}</small></span><span>${num(x.listings)}<small>${x.enabled?e(label(x.status)):'Disabilitata'}</small></span></a>`).join('')}</div>`:empty('Nessuna fonte','Collega un catalogo o importa i dati del cliente.')}</section></div>`;
}
