import {action,empty,pageHeading,notice,badge} from './ui.js';
import {icon} from './icons.js';
import {e,label,reviewLabel,num,selectOptions} from './utils.js';

const STAGES=['new','reviewing','shortlisted','due_diligence','negotiation','acquired','discarded'];
export const defaultFilters=()=>({missing_field:'',availability:'open',q:'',city:'',type:'',strategy:'',status:'',agent_id:'',qualified:false,
  starred:false,sort:'score',source_id:'',currency:'',min_price:null,max_price:null,min_surface:null,max_surface:null,focus:'all'});
const FOCUS=[['all','Tutti'],['new','Nuovi · 7 giorni'],['reduced','Con ribassi'],['below','Sotto benchmark'],['stale','Da aggiornare'],['unbenchmarked','Senza benchmark'],['overdue','Revisioni scadute'],['unassigned','Senza responsabile']];
const select=(name,title,options,value)=>`<label class="filter-select"><span>${e(title)}</span><select id="catalog-${name}" data-filter="${name}" aria-label="${e(title)}">${selectOptions(options,value)}</select></label>`;

export function pagination(s){
  const c=s.catalog;
  const unavailable=c.loading||Boolean(c.error);
  const summary=c.error?'Risultati non disponibili':c.loading?'Aggiornamento…':null;
  const start=c.total?(c.page-1)*c.page_size+1:0;
  return `<div class="catalog-pagination"><span>${summary||`${num(start)}–${num(Math.min(c.page*c.page_size,c.total))} di ${num(c.total)} annunci`}</span><div><label class="catalog-page-size">Per pagina <select id="catalog-page-size" data-page-size aria-label="Annunci per pagina">${selectOptions([['25','25'],['50','50'],['100','100']],String(c.page_size))}</select></label><button class="btn small-btn" data-action="catalog-prev" ${c.page<=1||unavailable?'disabled':''} aria-label="Pagina precedente">${icon('chevron')} Indietro</button><span class="small">${unavailable?'—':`${c.page} / ${c.pages||1}`}</span><button class="btn small-btn" data-action="catalog-next" ${!c.has_next||unavailable?'disabled':''} aria-label="Pagina successiva">Avanti ${icon('arrow')}</button></div></div>`;
}

export function catalogView(s,results,savedViews){
  const c=s.catalog,f=s.filters,facets=c.facets||{cities:[],currencies:[]};
  const currencies=[...new Set(['EUR',...facets.currencies])];
  const editor=s.user.role!=='viewer';
  return `${pageHeading('ARCHIVIO','Immobili','Filtra, confronta e seleziona.',`<div class="catalog-export"><div class="export-menu" role="group" aria-label="Esporta i risultati filtrati"><button class="btn primary" data-action="export" data-export-scope="catalog" data-format="xlsx">${icon('download')} Excel</button><button class="btn" data-action="export" data-export-scope="catalog" data-format="csv">CSV</button></div></div>`)}
    ${savedViews}
    ${f.source_id?`<div class="catalog-missing-filter catalog-source-filter"><span>Fonte: ${e(s.data.sources.find(src=>src.id===f.source_id)?.name||'Fonte non disponibile')}</span>${action('clear-source-filter','Rimuovi filtro fonte','close','text-button')}</div>`:''}
    ${f.missing_field?`<div class="catalog-missing-filter"><span>Dato mancante: ${e(label(f.missing_field))}</span>${action('clear-missing-field','Rimuovi filtro','close','text-button')}</div>`:''}
    <div class="catalog-focus" role="group" aria-label="Viste operative">${FOCUS.map(([key,name])=>`<button class="catalog-chip ${f.focus===key?'active':''}" data-action="catalog-focus" data-focus="${key}" aria-pressed="${f.focus===key}">${e(name)}</button>`).join('')}</div>
    <section class="catalog-surface ${s.catalogFiltersOpen?'filters-open':''}"><div class="property-toolbar"><div class="search-input">${icon('search')}<input id="property-search" type="search" value="${e(f.q)}" maxlength="200" placeholder="Cerca immobile, zona o indirizzo" aria-label="Cerca immobili"><kbd>/</kbd></div><button class="btn filters-toggle" data-action="catalog-filters-toggle" aria-expanded="${Boolean(s.catalogFiltersOpen)}" aria-controls="catalog-filter-row">${icon('filter')} Filtri${['availability','agent_id','city','type','status','qualified','starred'].filter(k=>f[k]!==defaultFilters()[k]).length?` <span class="filters-count">${['availability','agent_id','city','type','status','qualified','starred'].filter(k=>f[k]!==defaultFilters()[k]).length}</span>`:''}</button><div class="property-toolbar-right"><span id="filtered-count" role="status" aria-live="polite">${num(c.total)} risultati</span><div class="segmented"><button data-action="layout" data-layout="list" class="${s.layout==='list'?'active':''}" aria-label="Vista tabella">${icon('list')}</button><button data-action="layout" data-layout="grid" class="${s.layout==='grid'?'active':''}" aria-label="Vista schede">${icon('grid')}</button></div></div></div>
    <div class="filter-row" id="catalog-filter-row">${select('availability','Disponibilità',[['open','Non archiviati'],['all','Tutti gli annunci'],['sold','Venduti'],['rented','Affittati'],['withdrawn','Ritirati'],['review','Da verificare']],f.availability)}${select('agent_id','Ricerca agente',[['','Tutte le ricerche'],...s.data.agents.map(a=>[a.id,a.name])],f.agent_id)}
      ${select('city','Comune',[['','Tutti i comuni'],...facets.cities.map(x=>[x,x])],f.city)}
      ${select('type','Tipologia',[['','Tutte le tipologie'],...['residential','office','commercial','logistics','land','hospitality','unknown'].map(x=>[x,label(x)])],f.type)}
      ${select('status','Stato revisione',[['','Tutti gli stati'],...STAGES.map(x=>[x,reviewLabel(x)])],f.status)}
      <div class="catalog-filter-toggles"><button class="filter-button ${f.qualified?'active':''}" data-action="filter-qualified" aria-pressed="${f.qualified}">${icon('check')} Nei criteri</button>
      <button class="filter-button ${f.starred?'active':''}" data-action="filter-star" aria-pressed="${f.starred}">${icon('star')} Preferiti</button>
      <button class="text-button" data-action="reset-filters">Azzera</button></div>
    </div>
    <details id="catalog-advanced" class="catalog-advanced" ${s.catalogAdvanced?'open':''}><summary>${icon('filter')} Prezzo, superficie e altre opzioni</summary><div class="catalog-filter-grid">
      ${select('source_id','Fonte',[['','Tutte le fonti'],...s.data.sources.map(x=>[x.id,x.name])],f.source_id)}
      ${select('strategy','Strategia',[['','Tutte le strategie'],...['value_add','core_plus','development','conversion'].map(x=>[x,label(x)])],f.strategy)}
      ${select('missing_field','Dato mancante',[['','Qualsiasi'],...['price','surface','title','description','city','zone','address','property_type','condition','area_basis'].map(key=>[key,label(key)])],f.missing_field)}
      ${select('currency','Valuta',[['','Tutte le valute'],...currencies.map(x=>[x,x])],f.currency)}
      ${['min_price','max_price','min_surface','max_surface'].map((key,i)=>`<label>${['Prezzo minimo','Prezzo massimo','Superficie minima · m²','Superficie massima · m²'][i]}<input type="number" min="0" step="any" id="catalog-${key}" data-range="${key}" aria-label="${['Prezzo minimo','Prezzo massimo','Superficie minima','Superficie massima'][i]}" value="${e(f[key]??'')}" placeholder="Nessun limite"></label>`).join('')}
    </div><p class="small muted">Per il prezzo scegli una valuta. Gli annunci senza prezzo o superficie sono esclusi dai rispettivi intervalli.</p></details>
    <div class="catalog-list-head"><button class="text-button" data-action="select-page" ${c.loading||c.error||!c.items.length?'disabled':''}>Seleziona pagina</button><label class="sort-select">Ordina per <select id="catalog-sort" data-filter="sort" aria-label="Ordinamento">${selectOptions([['score','Priorità'],['price','Prezzo · per valuta'],['newest','Nuovi acquisiti'],['listed','Da più tempo online'],['latest','Ultima rilevazione'],['quality','Completezza'],['due','Scadenza revisione']],f.sort)}</select></label></div>
    <div class="results-container" id="results-body" aria-busy="${c.loading}">${results}</div><div id="catalog-pagination">${pagination(s)}</div></section>
    <div class="selection-bar ${s.selected.size?'visible':''}" id="selection-bar" ${s.selected.size?'':'inert'}><span>Selezione: <strong id="selection-count">${s.selected.size}</strong> <small>· massimo 100</small></span>${editor?action('bulk-review','Aggiorna stato','check','btn primary'):''}${action('compare','Confronta','compare','btn',`aria-describedby="comparison-hint" ${s.selected.size<2||s.selected.size>3?'disabled':''}`)}${action('export','Esporta selezione','download','btn','data-format="xlsx" data-export-scope="selection"')}${action('clear-selection','','close','icon-button','aria-label="Annulla selezione"')}<small id="comparison-hint" ${s.selected.size>=2&&s.selected.size<=3?'hidden':''}>Per confrontare: 2–3 immobili</small></div>`;
}

export function catalogPlaceholder(s){
  if(s.catalog.error)return `<div class="catalog-error" role="alert"><strong>Ricerca non completata</strong><p>${e(s.catalog.error)}</p>${action('catalog-retry','Riprova','refresh','btn')}</div>`;
  if(s.catalog.loading)return `<div class="catalog-loading" role="status"><span class="catalog-loader"></span>Ricerca nell’archivio…</div>`;
  if(!s.catalog.items.length){
    const active=Object.entries(defaultFilters()).some(([key,value])=>s.filters[key]!==value);
    return empty('Nessun annuncio in questa vista',active?'Prova ad allargare la ricerca.':'Gli immobili acquisiti compariranno qui.',active?action('reset-filters','Azzera filtri','refresh'):s.user.role!=='viewer'?action('new-agent','Nuova ricerca','plus'):'');
  }
  return null;
}

export function bulkReviewForm(rows){
  return `<form id="bulk-review-form" class="modal-form"><div class="bulk-summary"><strong>${rows.length} annunci selezionati</strong><p>Verrà modificato soltanto lo stato. Responsabile, scadenza e checklist restano invariati.</p></div><label>Nuovo stato<select name="stage">${selectOptions(STAGES.map(x=>[x,reviewLabel(x)]),'reviewing')}</select></label><label>Nota per il team<textarea name="note" maxlength="2000" rows="3" placeholder="Motivazione o prossimo passo. Obbligatoria quando scarti un deal."></textarea></label><details class="bulk-items"><summary>Rivedi la selezione</summary>${rows.map(p=>`<div><strong>${e(p.title)}</strong><span>${e(p.city)} · ${e(reviewLabel(p.review_status))}</span></div>`).join('')}</details><div id="modal-error" class="form-error" role="alert"></div><button class="btn primary" type="submit">Applica a ${rows.length} annunci</button></form>`;
}

export {historyContent} from './history-ui.js';

export function preflightContent(data,canEdit){
  return `<div class="modal-body"><p class="small muted">${e(data.notice)}</p><div class="preflight-checks">${data.checks.map(check=>`<div class="preflight-check">${icon(check.ok?'check':'info')}<p>${e(check.message)}</p>${badge(check.ok?'OK':check.blocking?'Da configurare':'Attenzione',check.ok?'success':check.blocking?'danger':'warning')}</div>`).join('')}</div><h3>Fonti di questa ricerca</h3>${data.sources.map(src=>`<section class="preflight-source"><strong>${e(src.name)}</strong>${src.blockers.map(x=>`<p class="danger-text">${e(x)}</p>`).join('')}${src.warnings.map(x=>`<p class="small muted">${e(x)}</p>`).join('')}</section>`).join('')||empty('Nessuna fonte','Configura la ricerca.')}${canEdit&&(data.can_enqueue||data.active_run)?action('run-agent',data.active_run?'Mostra esecuzione':'Esegui ora','play','btn primary',`data-id="${e(data.agent_id)}"`):''}</div>`;
}
