import {action,empty,pageHeading} from './ui.js';
import {icon} from './icons.js';
import {e,num,label,amount,availabilityTag} from './utils.js';
import {duplicateControls} from './product-ui.js';
import {grouped,plural,statStrip} from './table-ui.js';
function candidate(p,id){
  return `<div class="quality-candidate"><span>${e(p?.source_name||'Fonte non disponibile')}</span>${action('property',e(p?.title||'Apri annuncio'),'','quality-property',`data-id="${e(id)}"`)}<p>${e(p?.city||'Comune non indicato')}${p?.address?` · ${e(p.address)}`:''}</p><div class="quality-candidate-facts"><strong>${amount(p?.price,p?.currency)}</strong><span>${p?.surface==null?'Superficie non indicata':num(p.surface)+' m²'}</span>${p?availabilityTag(p):''}</div></div>`;
}
export function qualityView(s){
  const d=s.data,q=d.quality,tab=s.qualityTab||'pending';
  if(!q)return `${pageHeading('','Qualità dei dati','')}${empty('Dati non disponibili','Aggiorna il workspace.',action('refresh','Aggiorna','refresh','btn'))}`;
  const pairs=d.duplicates.map(pair=>{
    const [a,b]=[pair.a,pair.b].sort(),review=s.ops?.duplicate_reviews?.find(r=>r.a===a&&r.b===b);
    return {...pair,review};
  });
  const pending=pairs.filter(pair=>!pair.review),reviewed=pairs.filter(pair=>pair.review),shown=tab==='reviewed'?reviewed:pending;
  const coverage=[...q.coverage].sort((a,b)=>b.missing-a.missing);
  const complete=coverage.filter(c=>!c.missing).length;
  const fieldRow=c=>{
    const name=label(c.field);
    return `<tr class="quality-field ${c.missing?'is-link':''}"><th scope="row">${e(name)}</th><td class="quality-meter"><meter min="0" max="100" value="${c.percent}" aria-label="${e(name)}: ${num(c.percent,1)}% presente"></meter></td><td class="num">${num(c.percent,1)}%</td><td class="num quality-missing">${c.missing?`<strong>${grouped(c.missing)}</strong>`:'<span class="pg-muted">Completo</span>'}</td><td class="quality-drill">${c.missing?action('quality-filter',icon('arrow'),'','btn pg-ghost pg-row-action',`data-field="${e(c.field)}" aria-label="Vedi annunci senza ${e(name.toLowerCase())}"`):''}</td></tr>`;
  };
  return `${pageHeading('','Qualità dei dati','',action('quality-filter','Apri archivio','arrow','btn'))}
    ${statStrip([
      {label:'Annunci in archivio',value:grouped(q.total),detail:'tutte le disponibilità'},
      {label:'Campi presenti',value:q.completeness==null?'—':num(q.completeness,1)+'%',detail:`media su ${q.coverage.length} campi`},
      {label:'Senza prezzo di zona',value:grouped(q.unbenchmarked),detail:q.unbenchmarked?action('quality-filter','Vedi annunci','','text-button','data-focus="unbenchmarked"'):''},
    ])}
    <section class="pg-surface quality-coverage"><div class="pg-head"><div><h2>Dati da completare</h2><p>La presenza di un dato non ne certifica l’accuratezza.</p></div></div>
      ${!q.total?empty('Archivio vuoto','I controlli compariranno dopo la prima acquisizione.'):`<div class="pg-scroll"><table class="pg-table quality-table"><thead><tr><th scope="col">Campo</th><th scope="col"><span class="sr-only">Presenza</span></th><th scope="col" class="num">Presente</th><th scope="col" class="num">Mancanti</th><th scope="col"><span class="sr-only">Annunci</span></th></tr></thead><tbody>${coverage.map(fieldRow).join('')}</tbody></table></div>${complete&&complete<coverage.length?`<p class="pg-note">${plural(complete,'campo completo','campi completi')} in tutti gli annunci.</p>`:''}`}
    </section>
    <section class="pg-surface quality-duplicates"><div class="pg-head"><div><h2>Possibili duplicati</h2><p>Confronta le fonti prima di collegare due annunci.</p></div>
      <div class="pg-segmented quality-tabs" role="group" aria-label="Revisione duplicati">${action('quality-tab',`Da verificare <span class="pg-count">${num(pending.length)}</span>`,'',tab==='pending'?'active':'',`id="quality-pending" data-tab="pending" aria-pressed="${tab==='pending'}"`)}${action('quality-tab',`Già valutati <span class="pg-count">${num(reviewed.length)}</span>`,'',tab==='reviewed'?'active':'',`id="quality-reviewed" data-tab="reviewed" aria-pressed="${tab==='reviewed'}"`)}</div></div>
      ${d.has_more?`<p class="pg-note quality-sample">Confronto limitato ai ${num(d.properties.length)} annunci caricati su ${num(q.total)}.</p>`:''}
      ${shown.length?`<div class="quality-pairs">${shown.map(pair=>`<article class="quality-pair"><div class="quality-pair-properties">${candidate(d.properties.find(p=>p.id===pair.a),pair.a)}${candidate(d.properties.find(p=>p.id===pair.b),pair.b)}</div><div class="quality-pair-footer"><details><summary>Perché questa coppia</summary><p>${e(pair.reason||'Indirizzo e superficie simili.')}</p></details><div class="quality-pair-actions">${duplicateControls(s,pair)}</div></div></article>`).join('')}</div>`:empty(tab==='reviewed'?'Nessuna coppia valutata':'Nessuna coppia da verificare',d.has_more?'Nel campione esaminato.':tab==='reviewed'?'Le decisioni sulle coppie attuali compariranno qui.':'Negli annunci esaminati.')}
    </section>
    <details class="pg-method quality-method"><summary>Metodo e limiti</summary><dl><div><dt>Campi mancanti</dt><dd>Restano non disponibili; il modello non li completa.</dd></div><div><dt>Benchmark</dt><dd>Richiede zona, tipologia, stato e base di superficie compatibili.</dd></div><div><dt>Evidenze AI</dt><dd>Le citazioni devono comparire nella descrizione acquisita.</dd></div><div><dt>Storico</dt><dd>La prima rilevazione non è la data di pubblicazione.</dd></div><div><dt>Duplicati</dt><dd>Il confronto usa indirizzo, comune, tipo e superficie tra fonti diverse. Le immagini non determinano il risultato; gli annunci restano separati.</dd></div></dl></details>`;
}
