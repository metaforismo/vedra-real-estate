import {action,badge,empty,pageHeading} from './ui.js';
import {icon} from './icons.js';
import {e,num,label,relative,tone} from './utils.js';

// Two letters from the words of a name ("RE/MAX" → RM, "Gabetti" → GA): no remote favicons, no network request.
export function monogram(src,size=''){
  const words=String(src?.name||src?.domain||'?').replace(/\.(it|com|eu|net|org)\b/gi,'').match(/[\p{L}\p{N}]+/gu)||['?'];
  const text=(words.length>1?words[0][0]+words[1][0]:words[0].slice(0,2)).toUpperCase();
  return `<span class="monogram ${size} ${src?.kind==='import'?'file':''}" aria-hidden="true">${e(text)}</span>`;
}
const recordsButton=src=>action('source-results','Apri immobili','arrow','btn',`data-id="${e(src.id)}" ${src.property_count?'':'disabled'}`);
const toggle=src=>action('toggle-source',src.enabled?'Sospendi':'Abilita',src.enabled?'pause':'play','btn',`data-id="${e(src.id)}" aria-label="${src.enabled?'Sospendi':'Abilita'} ${e(src.name)}"`);
// Quality is the share of expected fields found; without acquired records it is unmeasured, not 0%.
const quality=src=>src.property_count?`${num(src.quality)}%`:'—';
// The value explains itself inline: tooltips are unreachable on touch.
const method=src=>src.config.browser_navigation||src.config.render_js
  ?'<dd>Browser<small>come un visitatore</small></dd>'
  :'<dd>HTML diretto<small>senza JavaScript</small></dd>';

function webSource(src,admin){
  const status=src.enabled?badge(label(src.status),tone(src.status)):badge('In pausa','neutral');
  return `<article class="source-card source-row">
    <div class="source-identity">${monogram(src)}<div><h3>${e(src.name)}</h3><span>${e(src.domain)}</span></div>${status}</div>
    <dl class="source-metrics">
      <div><dt>Immobili</dt><dd>${num(src.property_count)}</dd></div>
      <div><dt>Campi compilati</dt><dd>${quality(src)}</dd></div>
      <div><dt>Lettura</dt>${method(src)}</div>
      <div><dt>Controllata</dt><dd>${src.last_checked?relative(src.last_checked):'Mai'}</dd></div>
    </dl>
    <div class="source-directory-actions">${recordsButton(src)}${admin?action('edit-source','Configura','edit','btn',`data-id="${e(src.id)}"`)+action('probe-source','Verifica accesso','pulse','btn',`data-id="${e(src.id)}" ${src.enabled?'':'disabled'}`)+toggle(src):''}</div>
    ${!src.allowed_on_server?`<p class="source-note">${icon('warning')}Dominio da abilitare sul server prima dell’uso.</p>`:''}
    ${src.last_error?`<details class="source-error"><summary>Accesso non riuscito</summary><p>${e(src.last_error)}</p></details>`:''}
  </article>`;
}
function fileSource(src,admin){
  return `<article class="source-import-row source-row">
    <div class="source-identity">${monogram(src)}<div class="source-import-name"><h3>${e(src.name)}</h3><p>${num(src.property_count)} immobili${src.property_count?` · ${num(src.quality)}% campi compilati`:''}</p></div>${!src.enabled?badge('In pausa','neutral'):''}</div>
    <div class="source-directory-actions">${recordsButton(src)}${admin?toggle(src):''}</div>
  </article>`;
}

export function sourceDirectory(s,sources){
  const admin=s.user.role==='admin',web=sources.filter(x=>x.kind==='html'),files=sources.filter(x=>x.kind==='import');
  return `${pageHeading('','Fonti e importazioni','',admin?action('import','Importa dati','upload','btn')+action('new-source','Collega fonte','plus','btn primary'):'')}
    <section class="source-directory"><div class="source-directory-heading"><h2>Siti web <span>${num(web.length)}</span></h2><p>Cataloghi che Scout può aprire durante le ricerche.</p></div>
    <div class="source-list">${web.map(src=>webSource(src,admin)).join('')||empty('Nessun sito collegato','Collega il sito di un’agenzia: Scout lo navigherà per le tue ricerche.')}</div></section>
    <section class="source-directory"><div class="source-directory-heading"><h2>File importati <span>${num(files.length)}</span></h2><p>Dati caricati a mano. Per aggiornarli importa un nuovo file.</p></div>
    <div class="source-list source-imports">${files.map(src=>fileSource(src,admin)).join('')||empty('Nessun file importato','Carica immobili o prezzi di zona con il relativo tracciato CSV.')}</div></section>`;
}

// Source cards in the connect dialog stay native radios; this bridges them to the preset <select> the app listens to.
if(typeof document!=='undefined')document.addEventListener('change',event=>{
  const choice=event.target.closest?.('input[name="source_preset_choice"]');if(!choice)return;
  const select=choice.form?.querySelector('#source-preset');if(!select)return;
  select.value=choice.value;select.dispatchEvent(new Event('change',{bubbles:true}));
});
