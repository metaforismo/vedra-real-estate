import {icon} from './icons.js';
import {e, num, amount, relative, label, score, discount, activeRun} from './utils.js';
import {action, empty, propertyThumb, panelHeading, metricCard} from './ui.js';
import {mapPanel} from './map.js';

function featured(property) {
  return `<article class="featured-property">
    <div class="featured-visual">${propertyThumb(property, 'hero-thumb')}<span class="featured-label">${icon('star')} Da valutare</span></div>
    <div class="featured-body"><div><span class="eyebrow">${e(property.city || 'Comune non indicato')}</span>
      <button class="featured-title" data-action="property" data-id="${e(property.id)}">${e(property.title)}</button>
      <div class="featured-facts"><span>${num(property.surface)} m²</span><span>${e(label(property.property_type))}</span><strong>${amount(property.price, property.currency)}</strong></div>
    </div>${action('property', 'Apri scheda', 'arrow', 'btn primary', `data-id="${e(property.id)}"`)}</div>
  </article>`;
}

function gettingStarted(s) {
  const hasSource = s.data.sources.length > 0;
  const hasAgent = s.data.agents.length > 0;
  return `<section class="start-card"><span class="eyebrow">IL PRIMO FLUSSO</span><h2>${hasSource ? 'Dalla fonte al primo risultato' : 'Collega la prima fonte'}</h2>
    <p>Usa i dati del cliente o un catalogo autorizzato. Nessun numero precompilato.</p>
    <ol class="start-steps"><li class="${hasSource ? 'done' : ''}"><span>${hasSource ? icon('check') : '1'}</span><a href="#sources">Verifica una fonte</a></li>
    <li class="${hasAgent ? 'done' : ''}"><span>${hasAgent ? icon('check') : '2'}</span><a href="#agents">Configura la ricerca</a></li>
    <li><span>3</span><a href="#activity">Controlla i risultati e i log</a></li></ol>
    ${s.user.role === 'admin' ? action('new-source', 'Configura fonte', 'plus', 'btn primary') + action('import', 'Importa file', 'upload', 'btn') : '<a class="btn" href="#sources">Visualizza le fonti</a>'}</section>`;
}

function rankedProperty(p) {
  return `<button class="rank-property" data-action="property" data-id="${e(p.id)}">
    ${propertyThumb(p, 'rank-thumb')}<span class="rank-text"><strong>${e(p.city || 'Comune n.d.')} · ${e(p.zone || label(p.property_type))}</strong>
    <span>${num(p.surface)} m² · ${amount(p.price_sqm, p.currency)}/m²</span></span><span class="rank-result">${score(p)}${discount(p)}</span></button>`;
}

function agentRow(a, editor) {
  return `<div class="agent-operation"><span class="agent-symbol">${icon('agent')}</span><div>
    <button class="plain-link" data-action="edit-agent" data-id="${e(a.id)}">${e(a.name)}</button>
    <small>${a.last_run ? label(a.last_run.status) + ' · ' + relative(a.last_run.finished_at || a.last_run.created_at) : 'Mai eseguito'}</small></div>
    ${editor ? action('run-agent', '', activeRun(a.last_run) ? 'pulse' : 'play', 'icon-button', `data-id="${e(a.id)}" aria-label="Esegui ${e(a.name)}"`) : ''}</div>`;
}

export function liveOverview(s) {
  const d = s.data;
  const insight = s.insights;
  const archive = insight?.archive;
  const total = archive?.total ?? d.stats.properties;
  const ranked = d.properties.filter(p => p.score != null && !['discarded', 'acquired'].includes(p.review_status)).slice(0, 5);
  const newest = [...d.properties].sort((a, b) => b.first_seen.localeCompare(a.first_seen))[0];
  const lead = ranked[0] || newest;
  const worker = s.ops?.worker;
  const recent = s.notifications.slice(0, 3);
  const quality = archive?.completeness ?? d.stats.quality;
  return `<section class="overview-intro"><div class="intro-copy"><span class="eyebrow">REAL ESTATE INTELLIGENCE</span>
    <h1>Panoramica</h1><p class="intro-subtitle">Il mercato osservato.<br>Le decisioni, in prospettiva.</p>
    <p class="intro-note">Annunci, riferimenti di prezzo e verifiche del team. Con la fonte sempre a portata di mano.</p>
    <div class="intro-actions">${s.user.role !== 'viewer' ? action('new-agent', 'Crea agente', 'plus', 'btn primary') : ''}<a href="#insights" class="btn">Leggi gli insight ${icon('arrow')}</a></div>
    <div class="connection-note"><span class="status-dot ${worker?.healthy ? 'green' : ''}"></span>${worker?.healthy ? 'Worker collegato' : 'Worker non rilevato'}<span>·</span>${worker?.last_tick ? 'Ultimo segnale ' + relative(worker.last_tick) : 'In attesa del primo segnale'}</div>
    </div>${lead ? featured(lead) : gettingStarted(s)}</section>
    <div class="metrics-grid">${metricCard('Immobili', num(total), `${num(archive?.new_7d ?? 0)} nuovi negli ultimi 7 giorni`, 'building')}
    ${metricCard('In lavorazione', num(archive?.in_work ?? 0), `${num(archive?.priority ?? 0)} con score ≥ 75`, 'board')}
    ${metricCard('Agenti', num(d.agents.length), `${d.agents.filter(a => a.active && a.interval_minutes > 0).length} programmati · ${d.agents.filter(a => a.runtime !== 'local').length} con AI`, 'agent')}
    ${metricCard('Completezza', total ? num(quality, 1) + '<span class="value-unit">%</span>' : '—', 'Presenza dei campi, non accuratezza', 'quality')}</div>
    <div class="overview-trio"><section class="panel overview-map">${panelHeading('Opportunità sulla mappa', 'Posizioni dichiarate, non verificate.', `<span class="quiet-pill">${num(d.properties.filter(p => p.latitude != null && p.longitude != null).length)} punti</span>`)}
      <div id="overview-map">${mapPanel(d.properties, s.mapMode || 'italy')}</div></section>
    <section class="panel overview-ranked">${panelHeading('Da approfondire', 'Score preliminari con benchmark.', '<a href="#properties" class="icon-button" aria-label="Tutte le opportunità">' + icon('arrow') + '</a>')}
      ${ranked.length ? '<div class="rank-list">' + ranked.map(rankedProperty).join('') + '</div>' : empty('Nessuno score disponibile', 'Gli annunci restano consultabili. Per il punteggio serve un riferimento compatibile.', '<a class="btn small-btn" href="#market">Controlla benchmark</a>')}
      <a class="panel-link" href="#properties">Tutte le opportunità ${icon('arrow')}</a></section>
    <div class="overview-side"><section class="panel">${panelHeading('Agenti', 'Esecuzioni tracciabili.', '<a href="#agents" class="icon-button" aria-label="Gestisci agenti">' + icon('arrow') + '</a>')}
      ${d.agents.length ? d.agents.slice(0, 3).map(a => agentRow(a, s.user.role !== 'viewer')).join('') : empty('Nessuna ricerca attiva', 'Crea un agente dopo aver collegato la fonte.')}</section>
    <section class="panel">${panelHeading('Attività', 'Cosa è cambiato.', '<a href="#inbox" class="text-link">Tutte</a>')}
      ${recent.length ? '<div class="event-list">' + recent.map(n => `<button data-action="notification-open" data-id="${e(n.id)}"><span class="event-icon">${icon(n.kind === 'price_change' ? 'chart' : n.kind === 'source_blocked' ? 'warning' : 'bell')}</span><span><strong>${e(n.title)}</strong><small>${e(n.body)}</small></span><time>${relative(n.created_at)}</time></button>`).join('') + '</div>' : empty('Nessun evento', 'Gli aggiornamenti compariranno dopo le prime esecuzioni.')}</section></div></div>
    ${(insight?.actions || []).length ? `<section class="panel next-actions">${panelHeading('Prossime verifiche', 'Azioni suggerite dai dati, non da un modello generativo.', '<a href="#insights" class="text-link">Tutti gli insight</a>')}<div>${insight.actions.slice(0, 3).map(a => `<a href="#${e(a.page)}"><span class="action-symbol">${icon(a.kind === 'source' ? 'warning' : 'check')}</span><span><strong>${e(a.title)}</strong><small>${e(a.detail)}</small></span>${icon('arrow')}</a>`).join('')}</div></section>` : ''}`;
}
