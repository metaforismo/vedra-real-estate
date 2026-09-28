import {action,empty,pageHeading} from './ui.js';
import {icon} from './icons.js';
import {e,label,safeUrl,selectOptions} from './utils.js';
import {grouped,plural} from './table-ui.js';

const period=value=>{const m=/^(\d{4})-S([12])$/.exec(value||'');return m?`${m[2]}° sem. ${m[1]}`:e(value||'—');};
const basis=b=>`Superficie ${b.area_basis==='commercial'?'commerciale':label(b.area_basis).toLowerCase()} · ${label(b.transaction_type).toLowerCase()}`;
const source=b=>{const url=safeUrl(b.source_url);return url?`<a href="${url}" target="_blank" rel="noopener noreferrer">${e(b.source_label)} ↗</a>`:e(b.source_label);};
const uniform=(rows,key)=>new Set(rows.map(key)).size===1;

// A page usually shares basis, operation and source: say them once above the table instead of on every row.
function inventory(m,rows){
  const oneBasis=uniform(rows,basis),oneSource=uniform(rows,b=>`${b.source_label}|${b.source_url}`),eur=rows.every(b=>b.currency==='EUR');
  const context=[oneBasis?basis(rows[0]):'',oneSource?`Fonte: ${source(rows[0])}`:''].filter(Boolean).join(' · ');
  return `${context?`<p class="pg-note benchmark-context">${context}</p>`:''}<div class="pg-scroll"><table class="pg-table benchmark-table-v2"><thead><tr><th scope="col">Comune</th><th scope="col">Zona</th><th scope="col">Tipologia</th><th scope="col">Stato</th><th scope="col" class="num">${eur?'€/m²':'Prezzo/m²'}</th><th scope="col" class="num">Periodo</th>${oneBasis?'':'<th scope="col">Base</th>'}${oneSource?'':'<th scope="col">Fonte</th>'}</tr></thead><tbody>${rows.map((b,i)=>{
    // Rows come grouped by place: a comune or zona repeated from the row above steps back to muted.
    const sameCity=i>0&&rows[i-1].city===b.city,sameZone=sameCity&&rows[i-1].zone===b.zone;
    return `<tr class="benchmark-item"><td class="benchmark-city ${sameCity?'is-repeat':''}">${e(b.city)}</td><td class="${sameZone?'is-repeat':''}">${e(b.zone)}</td><td>${e(label(b.property_type))}</td><td>${e(label(b.condition))}</td><td class="num benchmark-range">${grouped(b.min_sqm,2)} – ${grouped(b.max_sqm,2)}${b.currency==='EUR'?'':` <small>${e(b.currency)} / m²</small>`}</td><td class="num pg-muted">${period(b.period)}</td>${oneBasis?'':`<td class="pg-muted">${basis(b)}</td>`}${oneSource?'':`<td class="benchmark-provenance">${source(b)}</td>`}</tr>`;}).join('')}</tbody></table></div>`;
}

export function benchmarkView(s){
  const m=s.market||{},draft=m.draft||m,q=s.data.quality,disabled=m.loading||m.error,rows=m.items||[];
  const filtered=Boolean((draft.q||'').trim()||draft.condition||draft.currency);
  const summary=[m.archive_total==null?'':plural(m.archive_total,'riferimento','riferimenti')+' in archivio',q?`${grouped(q.total-q.unbenchmarked)} di ${plural(q.total,'immobile','immobili')} con prezzo di zona`:''].filter(Boolean).join(' · ');
  const first=((m.page||1)-1)*20+1;
  return `${pageHeading('','Prezzi di zona','',action('omi-open','Consulta OMI','','text-link')+(s.user.role==='admin'?action('import','Importa prezzi di zona','upload','btn','data-kind="benchmarks"'):''))}
    <p class="page-summary">${summary||'&nbsp;'}</p>
    <section class="pg-surface benchmark-inventory"><form id="benchmark-filters" class="pg-toolbar" role="search">
      <div class="pg-search">${icon('search')}<input id="benchmark-query" name="q" type="search" maxlength="200" value="${e(draft.q||'')}" placeholder="Comune, zona o fonte" aria-label="Cerca un riferimento"></div>
      <select id="benchmark-condition" name="condition" aria-label="Stato immobile">${selectOptions([['','Tutti gli stati'],...(m.conditions||[]).map(x=>[x,label(x)])],draft.condition||'')}</select>
      ${(m.currencies||[]).length>1||draft.currency?`<select id="benchmark-currency" name="currency" aria-label="Valuta benchmark">${selectOptions([['','Tutte le valute'],...(m.currencies||[]).map(x=>[x,x])],draft.currency||'')}</select>`:''}
      <div class="pg-end">${action('benchmark-reset','Azzera filtri','','text-button',`type="button" ${filtered?'':'disabled'}`)}</div></form>
    <div id="benchmark-results" tabindex="-1" aria-busy="${!!m.loading}">${m.loading?'<p role="status" class="benchmark-feedback">Caricamento riferimenti…</p>':m.error?empty('Riferimenti non disponibili',m.error,action('benchmark-retry','Riprova','refresh','btn'),'document'):rows.length?inventory(m,rows):empty(m.archive_total?'Nessun riferimento trovato':'Nessun prezzo di zona importato',m.archive_total?'Modifica o azzera i filtri.':'Importa un tracciato o consulta OMI.','',m.archive_total?'search':'document')}</div>
    <div class="pg-foot benchmark-pagination"><span>${disabled?'—':rows.length&&(m.pages||1)<=1?plural(m.total??rows.length,'riferimento','riferimenti'):rows.length?`${grouped(first)}–${grouped(first+rows.length-1)} di ${grouped(m.total)} · Pagina ${m.page||1} di ${m.pages||1}`:`Pagina ${m.page||1} di ${m.pages||1}`}</span><div>${action('benchmark-prev','Indietro','','btn',`type="button" ${disabled||!(m.page>1)?'disabled':''}`)}${action('benchmark-next','Avanti','','btn',`type="button" ${disabled||!m.has_next?'disabled':''}`)}</div></div></section>
    <details class="pg-method benchmark-method"><summary>Come usare questi riferimenti</summary><p>Il prezzo di zona si applica a un immobile solo con zona, tipologia, stato, superficie, valuta e operazione compatibili. La presenza del riferimento non ne certifica l’attualità.</p><p>Per gli annunci simili apri un immobile e scegli Comparabili: almeno tre asset osservati negli ultimi 90 giorni, superficie entro ±30%. Sono prezzi richiesti, non di compravendita.</p><p>OMI riporta fasce per zona e semestre, non una perizia del singolo immobile.</p></details>`;
}
