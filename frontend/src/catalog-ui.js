import {action,empty,pageHeading,notice,badge} from './ui.js';
import {icon} from './icons.js';
import {e,label,reviewLabel,num,selectOptions} from './utils.js';

const STAGES=['new','reviewing','shortlisted','due_diligence','negotiation','acquired','discarded'];
export const defaultFilters=()=>({missing_field:'',availability:'open',q:'',city:'',type:'',strategy:'',status:'',agent_id:'',qualified:false,
  starred:false,sort:'score',source_id:'',currency:'',min_price:null,max_price:null,min_surface:null,max_surface:null,focus:'all'});
const FOCUS=[['all','Tutti'],['new','Ultimi 7 giorni'],['reduced','Con ribassi'],['below','Sotto prezzo di zona'],['stale','Da aggiornare'],['unbenchmarked','Senza prezzo di zona'],['overdue','Revisioni scadute'],['unassigned','Senza responsabile']];
const AVAILABILITY=[['open','Non archiviati'],['all','Tutti gli annunci'],['sold','Venduti'],['rented','Affittati'],['withdrawn','Ritirati'],['review','Da verificare']];
const TYPES=['residential','office','commercial','logistics','land','hospitality','unknown'];
const MISSING=['price','surface','title','description','city','zone','address','property_type','condition','area_basis'];
export const SORTS=[['score','Consigliati'],['price','Prezzo crescente'],['newest','Nuovi acquisiti'],['listed','Da più tempo online'],['latest','Ultima rilevazione'],['quality','Completezza'],['due','Scadenza revisione']];
const select=(name,title,options,value,cls='filter-select')=>`<label class="${cls}"><span>${e(title)}</span><select id="catalog-${name}" data-filter="${name}" aria-label="${e(title)}">${selectOptions(options,value)}</select></label>`;
const range=(key,name,placeholder,value)=>`<input type="number" min="0" step="any" inputmode="numeric" id="catalog-${key}" data-range="${key}" aria-label="${name}" value="${e(value??'')}" placeholder="${placeholder}">`;
function span(min,max,unit){
  if(min!=null&&max!=null)return `${num(min)}–${num(max)}${unit}`;
  return min!=null?`da ${num(min)}${unit}`:`fino a ${num(max)}${unit}`;
}

// Filters that live inside the "Filtri" panel, each rendered as a removable chip once active.
// The comune/tipologia selects stay visible in the bar, so they need no chip.
export function activeFilters(s){
  const f=s.filters,d=defaultFilters(),chips=[];
  const chip=(text,act,name,extra='',cls='')=>chips.push(`<span class="filter-chip ${cls}"><span>${text}</span><button type="button" data-action="${act}" ${extra} aria-label="${e(name)}">${icon('close')}</button></span>`);
  const clear=(keys,title)=>['catalog-clear-filter',`Rimuovi filtro ${title}`,`data-keys="${keys}"`];
  const unit=f.currency==='EUR'?' €':f.currency?` ${e(f.currency)}`:'';
  if(f.availability!==d.availability)chip(`Disponibilità: ${e(AVAILABILITY.find(x=>x[0]===f.availability)?.[1]||f.availability)}`,...clear('availability','disponibilità'));
  if(f.agent_id)chip(`Ricerca: ${e(s.data.agents.find(a=>a.id===f.agent_id)?.name||'non disponibile')}`,...clear('agent_id','ricerca'));
  if(f.status)chip(`Stato: ${e(reviewLabel(f.status))}`,...clear('status','stato'));
  if(f.strategy)chip(`Strategia: ${e(label(f.strategy))}`,...clear('strategy','strategia'));
  if(f.source_id)chip(`Fonte: ${e(s.data.sources.find(src=>src.id===f.source_id)?.name||'non disponibile')}`,'clear-source-filter','Rimuovi filtro fonte','','catalog-source-filter');
  if(f.missing_field)chip(`Dato mancante: ${e(label(f.missing_field))}`,'clear-missing-field','Rimuovi filtro','','catalog-missing-filter');
  if(f.currency)chip(`Valuta: ${e(f.currency)}`,...clear('currency','valuta'));
  if(f.min_price!=null||f.max_price!=null)chip(`Prezzo: ${span(f.min_price,f.max_price,unit)}`,...clear('min_price,max_price','prezzo'));
  if(f.min_surface!=null||f.max_surface!=null)chip(`Superficie: ${span(f.min_surface,f.max_surface,' m²')}`,...clear('min_surface,max_surface','superficie'));
  if(f.qualified)chip('Nei criteri',...clear('qualified','nei criteri'));
  if(f.starred)chip('Preferiti',...clear('starred','preferiti'));
  return chips;
}
// Anything the user narrowed, search included. Sort order and the view tabs are not filters.
export const filtered=s=>Object.entries(defaultFilters()).some(([key,value])=>!['sort','focus'].includes(key)&&s.filters[key]!==value);

export function pagination(s){
  const c=s.catalog;
  const unavailable=c.loading||Boolean(c.error);
  // An empty result already says so in the bar and the empty state: no footer to repeat it.
  if(!c.total&&!unavailable)return '';
  const summary=c.error?'Risultati non disponibili':c.loading?'':null;
  const start=c.total?(c.page-1)*c.page_size+1:0;
  return `<div class="catalog-pagination"><span class="catalog-range">${summary??`${num(start)}–${num(Math.min(c.page*c.page_size,c.total))} di ${num(c.total)} annunci`}</span><div class="catalog-pager"><label class="catalog-page-size">Per pagina <select id="catalog-page-size" data-page-size aria-label="Annunci per pagina">${selectOptions([['25','25'],['50','50'],['100','100']],String(c.page_size))}</select></label><span class="catalog-page">${unavailable?'—':`${c.page} di ${c.pages||1}`}</span><button class="icon-button pager-prev" data-action="catalog-prev" ${c.page<=1||unavailable?'disabled':''} aria-label="Pagina precedente">${icon('chevron')}</button><button class="icon-button" data-action="catalog-next" ${!c.has_next||unavailable?'disabled':''} aria-label="Pagina successiva">${icon('chevron')}</button></div></div>`;
}

export function catalogView(s,results,savedViews){
  const c=s.catalog,f=s.filters,facets=c.facets||{cities:[],currencies:[]};
  const currencies=[...new Set(['EUR',...facets.currencies])];
  const editor=s.user.role!=='viewer';
  const chips=activeFilters(s);
  const hint=s.selected.size>=2&&s.selected.size<=3;
  return `<div class="catalog">${pageHeading('','Immobili','',`<div class="catalog-export" role="group" aria-label="Esporta i risultati filtrati"><button class="btn" data-action="export" data-export-scope="catalog" data-format="xlsx" title="Esporta i risultati filtrati">${icon('download')}Excel</button><button class="btn" data-action="export" data-export-scope="catalog" data-format="csv" title="Esporta i risultati filtrati">CSV</button></div>`)}
    <nav class="catalog-views" aria-label="Viste">${FOCUS.map(([key,name])=>`<button class="catalog-chip ${f.focus===key?'active':''}" data-action="catalog-focus" data-focus="${key}" aria-pressed="${f.focus===key}">${e(name)}</button>`).join('')}${savedViews}</nav>
    <section class="catalog-surface">
    <div class="catalog-bar">
      <div class="search-input catalog-search">${icon('search')}<input id="property-search" type="search" value="${e(f.q)}" maxlength="200" placeholder="Cerca per titolo, zona o indirizzo" aria-label="Cerca immobili" autocomplete="off"><kbd aria-hidden="true">/</kbd></div>
      <div class="catalog-keys">${select('city','Comune',[['','Tutti i comuni'],...facets.cities.map(x=>[x,x])],f.city,`catalog-key ${f.city?'set':''}`)}${select('type','Tipologia',[['','Tutte le tipologie'],...TYPES.map(x=>[x,label(x)])],f.type,`catalog-key ${f.type?'set':''}`)}</div>
      <button class="catalog-filters-btn" data-action="catalog-filters-toggle" aria-expanded="${Boolean(s.catalogAdvanced)}" aria-controls="catalog-advanced">${icon('filter')}<span>Filtri</span><span class="filters-count" ${chips.length?'':'hidden'}>${chips.length}</span></button>
      <button class="text-button catalog-reset" id="catalog-reset" data-action="reset-filters" ${filtered(s)?'':'hidden'}>Azzera</button>
      <div class="catalog-bar-end"><span id="filtered-count" role="status" aria-live="polite">${c.error?'Risultati non disponibili':c.loading?'Aggiornamento…':`${num(c.total)} risultati`}</span><label class="sort-select"><span>Ordina</span><select id="catalog-sort" data-filter="sort" aria-label="Ordinamento">${selectOptions(SORTS,f.sort)}</select></label><div class="segmented" role="group" aria-label="Visualizzazione"><button data-action="layout" data-layout="list" class="${s.layout==='list'?'active':''}" aria-pressed="${s.layout==='list'}" aria-label="Vista tabella">${icon('list')}</button><button data-action="layout" data-layout="grid" class="${s.layout==='grid'?'active':''}" aria-pressed="${s.layout==='grid'}" aria-label="Vista schede">${icon('grid')}</button></div></div>
      <details id="catalog-advanced" class="catalog-advanced" ${s.catalogAdvanced?'open':''}><summary>Filtri</summary>
        <div class="catalog-panel">
          <div class="catalog-filter-grid">
            ${select('availability','Disponibilità',AVAILABILITY,f.availability)}
            ${select('agent_id','Ricerca',[['','Tutte le ricerche'],...s.data.agents.map(a=>[a.id,a.name])],f.agent_id)}
            ${select('status','Stato revisione',[['','Tutti gli stati'],...STAGES.map(x=>[x,reviewLabel(x)])],f.status)}
            ${select('strategy','Strategia',[['','Tutte le strategie'],...['value_add','core_plus','development','conversion'].map(x=>[x,label(x)])],f.strategy)}
            ${select('source_id','Fonte',[['','Tutte le fonti'],...s.data.sources.map(x=>[x.id,x.name])],f.source_id)}
            ${select('missing_field','Dato mancante',[['','Qualsiasi'],...MISSING.map(key=>[key,label(key)])],f.missing_field)}
            ${select('currency','Valuta',[['','Tutte le valute'],...currencies.map(x=>[x,x])],f.currency)}
            <div class="range-field" role="group" aria-label="Prezzo"><span>Prezzo</span><div>${range('min_price','Prezzo minimo','Minimo',f.min_price)}<span aria-hidden="true">–</span>${range('max_price','Prezzo massimo','Massimo',f.max_price)}</div></div>
            <div class="range-field" role="group" aria-label="Superficie"><span>Superficie · m²</span><div>${range('min_surface','Superficie minima','Minima',f.min_surface)}<span aria-hidden="true">–</span>${range('max_surface','Superficie massima','Massima',f.max_surface)}</div></div>
          </div>
          <div class="catalog-panel-foot"><div class="catalog-toggles"><button class="filter-button ${f.qualified?'active':''}" data-action="filter-qualified" aria-pressed="${f.qualified}">${icon('check')} Nei criteri</button><button class="filter-button ${f.starred?'active':''}" data-action="filter-star" aria-pressed="${f.starred}">${icon('star')} Preferiti</button></div><p>Per filtrare il prezzo scegli una valuta. Gli annunci senza prezzo o superficie restano fuori dagli intervalli.</p></div>
        </div>
      </details>
    </div>
    <div class="catalog-active" id="catalog-active" aria-label="Filtri attivi">${chips.join('')}</div>
    <div class="results-container" id="results-body" aria-busy="${c.loading}">${results}</div><div id="catalog-pagination">${pagination(s)}</div></section>
    <div class="selection-bar ${s.selected.size?'visible':''}" id="selection-bar" role="region" aria-label="Annunci selezionati" ${s.selected.size?'':'inert'}><span class="selection-count" title="Fino a 100 annunci">Selezione <strong id="selection-count">${s.selected.size}</strong><small id="selection-limit" ${s.selected.size>=90?'':'hidden'}>max 100</small></span><span class="selection-actions">${editor?action('bulk-review','Aggiorna stato','check','btn'):''}${action('compare','Confronta','compare','btn',`aria-describedby="comparison-hint" ${hint?'':'disabled'}`)}${action('export','Esporta selezione','download','btn','data-format="xlsx" data-export-scope="selection"')}</span><small id="comparison-hint" ${hint?'hidden':''}>Confronto: 2–3 annunci</small>${action('clear-selection','','close','icon-button','aria-label="Annulla selezione" title="Annulla selezione"')}</div></div>`;
}

export function catalogPlaceholder(s){
  if(s.catalog.error)return `<div class="catalog-error" role="alert"><strong>Ricerca non completata</strong><p>${e(s.catalog.error)}</p>${action('catalog-retry','Riprova','refresh','btn')}</div>`;
  // A refresh keeps the previous rows dimmed (aria-busy) instead of collapsing the table on every keystroke.
  if(s.catalog.loading&&!s.catalog.items.length)return `<div class="catalog-loading" role="status"><span class="catalog-loader"></span>Ricerca nell’archivio…</div>`;
  if(!s.catalog.items.length){
    const active=filtered(s)||s.filters.focus!=='all';
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
