import {e, num, relative, label} from './utils.js';
import {pageHeading, empty, notice} from './ui.js';
import {grouped, money, plural, statStrip} from './table-ui.js';

export function insightsView(s) {
  const data=s.insights;
  if(!data)return `${pageHeading('','Segnali','')}<section class="pg-surface">${empty('Segnali non disponibili','Aggiorna il workspace per riprovare.')}</section>`;
  const a=data.archive,segments=data.segments;
  return `${pageHeading('','Segnali','')}
    ${statStrip([
      {label:'Nuovi in 7 giorni',value:grouped(a.new_7d),detail:'prime acquisizioni'},
      {label:'Da ricontrollare',value:grouped(a.stale_7d),detail:'non riletti da 7 giorni'},
      {label:'Con ribassi',value:grouped(a.reduced??data.price_reductions.length),detail:'dalla prima rilevazione'},
      {label:'Con prezzo di zona',value:grouped(a.benchmarked),detail:`su ${grouped(a.total)} in archivio`},
    ])}
    ${data.actions.length?`<section class="pg-surface insight-actions" aria-label="Prossime verifiche">${data.actions.map(x=>`<a href="#${e(x.page)}"><strong>${e(x.title)}</strong><span>${e(x.detail)}</span><i aria-hidden="true">→</i></a>`).join('')}</section>`:''}
    <section class="pg-surface insight-section"><div class="pg-head"><div><h2>Prezzi richiesti per zona</h2><p>Ultimi 90 giorni · mediana da almeno cinque annunci omogenei</p></div></div>
      ${segments.length?segmentTables(segments):empty('Nessun segmento confrontabile','Servono zona, stato, superficie, valuta e tipologia verificabili. Nessun dato viene completato per supposizione.')}
      <details class="pg-method insight-method"><summary>Metodo e campione</summary><p>${e(data.methodology)} Campione: ${grouped(data.sample.used)} di ${plural(data.sample.observed_listings,'annuncio recente','annunci recenti')}.${data.sample.truncated?' Analisi limitata ai 10.000 più recenti.':''}</p></details></section>
    <div class="insight-columns">
      <section class="pg-surface"><div class="pg-head"><div><h2>Ribassi negli ultimi 30 giorni</h2><p>Stesso annuncio, stessa valuta, stessa base di confronto</p></div></div>
      ${data.price_reductions.length?`<div class="pg-scroll"><table class="pg-table insight-reductions"><thead><tr><th scope="col">Immobile</th><th scope="col" class="num">Prezzo</th><th scope="col" class="num">Ribasso</th></tr></thead><tbody>${data.price_reductions.map(x=>`<tr class="is-link"><td><button class="pg-link" data-action="property" data-id="${e(x.property_id)}">${e(x.title)}</button><small>${relative(x.observed_at)}</small></td><td class="num"><s class="pg-muted">${money(x.previous_price,x.currency)}</s><br>${money(x.price,x.currency)}</td><td class="num"><strong class="discount-positive">−${num(x.reduction_pct,1)}%</strong></td></tr>`).join('')}</tbody></table></div>`:empty('Nessun ribasso confrontabile','Il confronto inizia con due osservazioni complete e coerenti dello stesso annuncio.')}
      ${data.sample.observations_truncated?notice('Storico limitato alle ultime 20.000 osservazioni con contesto.'):''}</section>
      <section class="pg-surface"><div class="pg-head"><div><h2>Fonti e copertura</h2><p>Una fonte non raggiungibile non equivale a zero opportunità</p></div><a href="#sources" class="text-button">Gestisci</a></div>
      ${data.sources.length?`<div class="pg-scroll"><table class="pg-table insight-sources"><thead><tr><th scope="col">Fonte</th><th scope="col" class="num">Annunci</th><th scope="col">Stato</th></tr></thead><tbody>${data.sources.map(x=>`<tr><td><strong>${e(x.name)}</strong><small>${x.last_success?'Ultima acquisizione '+relative(x.last_success):'Nessuna acquisizione automatica'}</small></td><td class="num">${grouped(x.listings)}</td><td class="insight-status ${x.enabled?'':'pg-muted'}">${x.enabled?e(label(x.status)):'Disabilitata'}</td></tr>`).join('')}</tbody></table></div>`:empty('Nessuna fonte','Collega un catalogo o importa i dati del cliente.')}</section></div>`;
}

// Zones with a usable median first; thin samples stay available but folded away.
function segmentTables(segments){
  const table=list=>`<div class="pg-scroll"><table class="pg-table insight-table"><thead><tr><th scope="col">Zona</th><th scope="col">Stato e superficie</th><th scope="col" class="num">Annunci</th><th scope="col" class="num">Mediana</th><th scope="col" class="num">25°–75° percentile</th></tr></thead><tbody>${list.map(x=>`<tr><td><strong>${e(x.city)} · ${e(x.zone)}</strong><small>${e(label(x.property_type))} · ${e(label(x.transaction_type))}</small></td><td>${e(label(x.condition))}<small>${e(x.size_band)} m² · ${e(label(x.area_basis))}</small></td><td class="num">${grouped(x.n)}</td><td class="num">${x.sufficient?`<strong>${money(x.median_sqm,x.currency)}</strong>/m²`:'<span class="pg-muted">Campione insufficiente</span>'}</td><td class="num">${x.sufficient?`${money(x.p25_sqm,x.currency)} – ${money(x.p75_sqm,x.currency)}`:'<span class="pg-muted">—</span>'}</td></tr>`).join('')}</tbody></table></div>`;
  const ok=segments.filter(x=>x.sufficient),few=segments.filter(x=>!x.sufficient);
  return (ok.length?table(ok):'<p class="pg-note insight-empty">Nessuna zona ha ancora cinque annunci omogenei.</p>')
    +(few.length?`<details class="insight-few"><summary>Zone con campione insufficiente <span class="pg-count">${grouped(few.length)}</span></summary>${table(few)}</details>`:'');
}
