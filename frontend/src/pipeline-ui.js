import {icon} from './icons.js';
import {e,reviewLabel,strategyTags,selectOptions,availabilityTag} from './utils.js';
import {action,empty,pageHeading} from './ui.js';
import {grouped,money,plural} from './table-ui.js';

export const stages=['new','reviewing','shortlisted','due_diligence','negotiation','acquired','discarded'];
export const checks=[
  ['source_checked','Annuncio e fonte verificati'],
  ['area_checked','Superficie e stato confrontabili'],
  ['occupancy_checked','Occupazione e disponibilità verificate'],
  ['planning_checked','Verifica urbanistica professionale'],
  ['costs_checked','Costi e ipotesi economiche verificati'],
];
const closed=stage=>['acquired','discarded'].includes(stage);
const todayKey=()=>{const date=new Date();return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;};
const dateLabel=value=>new Date(value+'T12:00:00').toLocaleDateString('it-IT',{day:'numeric',month:'short',year:'numeric'});

export function pipelineRows(s,today=todayKey()){
  const work=new Map((s.ops?.work||[]).map(w=>[w.property_id,w]));
  const team=new Map((s.ops?.team||[]).map(u=>[u.id,u.name]));
  const query=(s.pipelineQuery||'').trim().toLocaleLowerCase();
  return s.data.properties.map(p=>{
    const w=work.get(p.id)||{};
    const owner=w.owner_id?(team.get(w.owner_id)||'Responsabile non disponibile'):'';
    const done=checks.filter(([key])=>w.checklist?.[key]===true).length;
    return {p,w,owner,done,late:!closed(p.review_status)&&Boolean(w.due_date&&w.due_date<today)};
  }).filter(({p,w,owner,late})=>{
    const availability=s.pipelineAvailability||'all',focus=s.pipelineFocus||'all';
    return (availability==='all'||(availability==='closed'?['sold','rented','withdrawn'].includes(p.availability):availability==='review'?['review','unknown',undefined,null].includes(p.availability):p.availability==='listed'))
      && (!s.pipelineStage||p.review_status===s.pipelineStage)
      && (!s.pipelineOwner||w.owner_id===s.pipelineOwner)
      && (focus==='all'||(focus==='overdue'?late:!closed(p.review_status)&&!w.owner_id))
      && `${p.title} ${p.city} ${owner}`.toLocaleLowerCase().includes(query);
  }).sort((a,b)=>Number(closed(a.p.review_status))-Number(closed(b.p.review_status))
    ||Number(b.late)-Number(a.late)||(a.w.due_date||'9999').localeCompare(b.w.due_date||'9999')
    ||(b.p.priority_score??-1)-(a.p.priority_score??-1)||a.p.id.localeCompare(b.p.id));
}
const dash='<span class="pg-dash" aria-label="Non indicato">—</span>';
function due(row){
  if(!row.w.due_date)return dash;
  return `<span class="${row.late?'danger-text':''}">${dateLabel(row.w.due_date)}${row.late?'<small>Scaduta</small>':''}</span>`;
}
const manage=(s,row,cls='btn')=>action('deal-work',s.user.role==='viewer'?'Dettagli':'Gestisci','',cls,`data-id="${e(row.p.id)}" aria-label="${s.user.role==='viewer'?'Dettagli':'Gestisci'} revisione: ${e(row.p.title)}"`);
const stagePill=stage=>`<span class="work-stage pg-stage stage-${e(stage)}"><i aria-hidden="true"></i>${e(reviewLabel(stage))}</span>`;
// Team columns that are empty on every row collapse into one line above the table: no wall of dashes.
const teamColumns=[
  ['owner','Responsabile','nessun responsabile',row=>row.owner,row=>row.owner?e(row.owner):dash,''],
  ['due','Scadenza','nessuna scadenza',row=>row.w.due_date,due,''],
  ['checks','Verifiche','nessuna verifica',row=>row.done,row=>row.done?`${row.done} / ${checks.length}`:dash,'num'],
];
export function workColumns(rows,viewer=false){
  const shown=teamColumns.filter(([,,,has])=>rows.some(has));
  const empty=teamColumns.filter(column=>!shown.includes(column)).map(([,,text])=>text);
  const hint=empty.length?`${empty.join(' · ').replace(/^n/,'N')}.${viewer?'':' Si assegnano da Gestisci.'}`:'';
  return {shown,hint};
}
function listView(s,rows){
  const {shown,hint}=workColumns(rows,s.user.role==='viewer');
  return `${hint?`<p class="pg-note work-hint">${hint}</p>`:''}<div class="pg-scroll"><table class="pg-table work-list" data-columns="${3+shown.length}"><thead><tr><th scope="col">Immobile</th><th scope="col" class="num">Prezzo</th><th scope="col">Fase</th>${shown.map(([key,title,,,,cls])=>`<th scope="col" class="work-${key}-head ${cls}">${title}</th>`).join('')}<th scope="col"><span class="sr-only">Azioni</span></th></tr></thead><tbody>${rows.map(row=>{
    const {p}=row;
    return `<tr class="is-link work-row" data-work-id="${e(p.id)}"><td class="work-asset"><button class="pg-link" data-action="property" data-id="${e(p.id)}">${e(p.title)}</button><small>${e(p.city||'Comune non indicato')}${p.zone?` · ${e(p.zone)}`:''}${availabilityTag(p,true)?' · ':''}${availabilityTag(p,true)}</small></td><td class="num work-price">${money(p.price,p.currency)}</td><td>${stagePill(p.review_status)}</td>${shown.map(([key,,,,cell,cls])=>`<td class="work-${key} ${cls}">${cell(row)}</td>`).join('')}<td class="work-actions">${manage(s,row,'text-link work-manage')}</td></tr>`;
  }).join('')}</tbody></table></div>`;
}
function boardView(s,rows){
  return `<div class="pipeline-board" tabindex="0" role="region" aria-label="Bacheca delle fasi, scorrimento orizzontale">${stages.map(stage=>{
    const group=rows.filter(row=>row.p.review_status===stage);
    return `<section class="pipeline-column stage-${stage}"><header>${stagePill(stage)}<strong>${group.length}</strong></header><div tabindex="${group.length?0:-1}" role="region" aria-label="Immobili ${e(reviewLabel(stage))}">${group.map(row=>{
      const {p,owner,done}=row;
      return `<article class="deal-card"><button class="deal-card-title" data-action="property" data-id="${e(p.id)}">${e(p.title)}</button><span class="deal-card-meta">${e(p.city||'Comune non indicato')}${p.surface==null?'':` · ${grouped(p.surface)} m²`}</span>${p.price!=null?`<strong class="deal-card-price">${money(p.price,p.currency)}</strong>`:''}${availabilityTag(p,true)||strategyTags(p,1)?`<div class="strategy-group">${availabilityTag(p,true)}${strategyTags(p,1)}</div>`:''}${owner||row.w.due_date||done?`<div class="deal-card-work">${owner?`<span>${icon('user')}${e(owner)}</span>`:''}${row.w.due_date?`<span>${icon('calendar')}${due(row)}</span>`:''}${done?`<span>${icon('check')}${done} / ${checks.length}</span>`:''}</div>`:''}${manage(s,row,'btn pg-ghost deal-card-manage')}</article>`;
    }).join('')||'<div class="column-empty">Nessun immobile</div>'}</div></section>`;
  }).join('')}</div>`;
}
export function pipelineView(s){
  const rows=pipelineRows(s),board=s.pipelineLayout==='board',focus=s.pipelineFocus||'all';
  const select=(name,title,options,value)=>`<select id="pipeline-${name}" aria-label="${title}">${selectOptions(options,value)}</select>`;
  const filtered=Boolean(s.pipelineQuery?.trim()||s.pipelineStage||s.pipelineOwner||focus!=='all'||(s.pipelineAvailability&&s.pipelineAvailability!=='all'));
  // Each quick view shows how many rows it would hold with the other filters kept.
  const counts=Object.fromEntries(['all','overdue','unassigned'].map(key=>[key,key===focus?rows.length:pipelineRows({...s,pipelineFocus:key}).length]));
  return `${pageHeading('','Lavorazione','')}
    <section class="pg-surface work-surface">
    <div class="pg-toolbar work-views"><div class="work-quick" role="group" aria-label="Priorità di lavorazione">${[['all','Tutti'],['overdue','Scaduti'],['unassigned','Da assegnare']].map(([key,text])=>`<button id="pipeline-focus-${key}" class="catalog-chip ${focus===key?'active':''}" data-action="pipeline-focus" data-focus="${key}" aria-pressed="${focus===key}">${text}<span class="pg-count" aria-hidden="true">${grouped(counts[key])}</span></button>`).join('')}</div>
      <div class="pg-end"><div class="pg-segmented" role="group" aria-label="Vista lavorazione"><button id="pipeline-layout-list" data-action="pipeline-layout" data-layout="list" class="${!board?'active':''}" aria-pressed="${!board}">${icon('list')}Elenco</button><button id="pipeline-layout-board" data-action="pipeline-layout" data-layout="board" class="${board?'active':''}" aria-pressed="${board}">${icon('grid')}Bacheca</button></div></div></div>
    <div class="pg-toolbar work-filterbar"><div class="pg-search">${icon('search')}<input id="pipeline-search" type="search" value="${e(s.pipelineQuery||'')}" placeholder="Immobile, comune o responsabile" aria-label="Cerca nella pipeline"></div>${select('stage','Fase',[['','Tutte le fasi'],...stages.map(x=>[x,reviewLabel(x)])],s.pipelineStage||'')}${select('owner','Responsabile',[['','Tutto il team'],...(s.ops?.team||[]).map(u=>[u.id,u.name])],s.pipelineOwner||'')}${select('availability','Disponibilità',[['all','Tutti gli annunci'],['listed','Pubblicati'],['review','Da verificare'],['closed','Venduti, affittati o ritirati']],s.pipelineAvailability||'all')}
      <div class="pg-end"><span class="work-total" role="status">${plural(rows.length,'immobile','immobili')}</span><button class="text-button" data-action="reset-pipeline" ${filtered?'':'disabled'}>Azzera filtri</button></div></div>
    ${s.data.has_more?'<p class="pg-note work-limit">Vista parziale: consulta l’<a href="#properties">archivio completo</a> per gli altri immobili.</p>':''}
    ${rows.length?(board?boardView(s,rows):listView(s,rows)):empty(filtered?'Nessun immobile corrisponde':'Nessun immobile in lavorazione',filtered?'Modifica i filtri.':'Gli immobili acquisiti compariranno qui.',filtered?action('reset-pipeline','Mostra tutti','refresh'):'<a href="#agents" class="btn">Gestisci ricerche</a>',filtered?'search':'document')}</section>`;
}
export function workForm(s,p,w){
  const readonly=s.user.role==='viewer';
  const team=(s.ops?.team||[]).filter(u=>u.role!=='viewer').map(u=>[u.id,u.name]);
  // Retain unavailable owners instead of silently selecting “Non assegnato”.
  if(w.owner_id&&!team.some(([id])=>id===w.owner_id))team.push([w.owner_id,'Assegnatario non disponibile']);
  return `<form id="work-form" class="modal-form work-form" data-id="${e(p.id)}" data-version="${w.version}"><fieldset ${readonly?'disabled':''}><div class="form-grid"><label>Fase<select name="stage" aria-label="Fase">${selectOptions(stages.map(x=>[x,reviewLabel(x)]),w.stage??p.review_status)}</select></label><label>Responsabile<select name="owner_id" aria-label="Responsabile">${selectOptions([['','Non assegnato'],...team],w.owner_id||'')}</select></label><label>Scadenza revisione<input type="date" name="due_date" aria-label="Scadenza revisione" aria-describedby="work-due-help" value="${e(w.due_date||'')}"><small id="work-due-help">Promemoria interno al team.</small></label></div><div class="review-checklist"><h3>Verifiche del team</h3>${checks.map(([key,text])=>`<label><input type="checkbox" name="${key}" ${w.checklist?.[key]?'checked':''}>${text}</label>`).join('')}</div></fieldset><div class="form-error" id="modal-error" role="alert"></div><div id="work-conflict" hidden><p>Le tue modifiche non sono state salvate.</p>${action('reload-work','Carica versione del team','refresh','btn',`data-id="${e(p.id)}"`)}</div><div class="modal-form-footer"><button class="btn footer-back" type="button" data-action="property" data-id="${e(p.id)}">Torna all’immobile</button>${readonly?'':'<button type="submit" class="btn primary">Salva revisione</button>'}</div></form>`;
}
