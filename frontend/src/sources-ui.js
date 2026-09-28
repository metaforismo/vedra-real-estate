import {action,badge,empty,pageHeading} from './ui.js';
import {icon} from './icons.js';
import {cardMenu} from './menu-ui.js';
import {e,num,label,relative,tone} from './utils.js';

// Two letters from the words of a name ("RE/MAX" → RM, "Gabetti" → GA): no remote favicons, no network request.
export function monogram(src,size=''){
  const words=String(src?.name||src?.domain||'?').replace(/\.(it|com|eu|net|org)\b/gi,'').match(/[\p{L}\p{N}]+/gu)||['?'];
  const text=(words.length>1?words[0][0]+words[1][0]:words[0].slice(0,2)).toUpperCase();
  return `<span class="monogram ${size} ${src?.kind==='import'?'file':''}" aria-hidden="true">${e(text)}</span>`;
}
// One quiet glyph says what kind of source a row is (site, file, mailbox), as the engine icon does on Ricerche.
const kind=glyph=>`<span class="source-kind" aria-hidden="true">${icon(glyph)}</span>`;
// Quiet actions: the records link is the everyday one; configuration lives in the row menu.
const recordsLink=src=>action('source-results',`Apri immobili ${icon('arrow')}`,'','text-link source-records',`data-id="${e(src.id)}" ${src.property_count?'':'disabled'}`);
const toggleItem=src=>action('toggle-source',src.enabled?'Sospendi':'Abilita',src.enabled?'pause':'play','menu-item',`data-id="${e(src.id)}" aria-label="${src.enabled?'Sospendi':'Abilita'} ${e(src.name)}"`);
const actions=(src,items)=>`<div class="source-directory-actions">${recordsLink(src)}${cardMenu(e(src.id),e(src.name),items,'source-menu')}</div>`;
// Quality is the share of expected fields found; without acquired records it is unmeasured, not 0%.
const quality=src=>src.property_count?`${num(src.quality)}%`:'—';

function webSource(src,admin){
  const status=src.enabled?badge(label(src.status),tone(src.status)):badge('In pausa','neutral');
  return `<article class="source-card source-row">
    <div class="source-identity">${kind('link')}<div><h3>${e(src.name)}</h3><span>${e(src.domain)}</span></div>${status}</div>
    <dl class="source-metrics">
      <div><dt>Immobili</dt><dd>${num(src.property_count)}</dd></div>
      <div><dt>Campi compilati</dt><dd>${quality(src)}</dd></div>
      <div><dt>Accesso</dt><dd>Pagine pubbliche</dd></div>
      <div><dt>Controllata</dt><dd>${src.last_checked?relative(src.last_checked):'Mai'}</dd></div>
    </dl>
    ${actions(src,admin?[action('edit-source','Configura','edit','menu-item',`data-id="${e(src.id)}"`),action('probe-source','Prova l’accesso','pulse','menu-item',`data-id="${e(src.id)}" ${src.enabled?'':'disabled'}`),toggleItem(src)]:[])}
    ${!src.allowed_on_server?`<p class="source-note">${icon('warning')}Dominio da abilitare sul server prima dell’uso.</p>`:''}
    ${src.last_error?`<details class="source-error"><summary>Accesso non riuscito</summary><p>${e(src.last_error)}</p></details>`:''}
  </article>`;
}
function fileSource(src,admin){
  return `<article class="source-import-row source-row">
    <div class="source-identity">${kind('document')}<div class="source-import-name"><h3>${e(src.name)}</h3><p>${num(src.property_count)} ${src.property_count===1?'immobile':'immobili'}${src.property_count?` · ${num(src.quality)}% campi compilati`:''}</p></div>${!src.enabled?badge('In pausa','neutral'):''}</div>
    ${actions(src,admin?[toggleItem(src)]:[])}
  </article>`;
}

// Each block is a titled section with its own list: further blocks (e.g. portal alerts) slot in as siblings.
const section=(title,count,note,body)=>`<section class="source-directory"><div class="source-directory-heading"><h2>${title} <span>${num(count)}</span></h2>${note?`<p>${note}</p>`:''}</div>${body}</section>`;
export function sourceDirectory(s,sources,between=''){
  const admin=s.user.role==='admin',web=sources.filter(x=>x.kind==='html'),files=sources.filter(x=>x.kind==='import');
  return `${pageHeading('','Fonti e importazioni','',admin?action('import','Importa dati','upload','btn')+action('new-source','Collega fonte','plus','btn primary'):'')}
    ${section('Siti web',web.length,'',`<div class="source-list">${web.map(src=>webSource(src,admin)).join('')||empty('Nessun sito collegato','Collega il sito di un’agenzia: Scout lo navigherà per le tue ricerche.','','search')}</div>`)}${between}
    ${section('File importati',files.length,'Caricati a mano · aggiorna importando un nuovo file',`<div class="source-list source-imports">${files.map(src=>fileSource(src,admin)).join('')||empty('Nessun file importato','Carica immobili o prezzi di zona con il relativo tracciato CSV.','','document')}</div>`)}`;
}

// Source cards in the connect dialog stay native radios; this bridges them to the preset <select> the app listens to.
if(typeof document!=='undefined')document.addEventListener('change',event=>{
  const choice=event.target.closest?.('input[name="source_preset_choice"]');if(!choice)return;
  const select=choice.form?.querySelector('#source-preset');if(!select)return;
  select.value=choice.value;select.dispatchEvent(new Event('change',{bubbles:true}));
});
