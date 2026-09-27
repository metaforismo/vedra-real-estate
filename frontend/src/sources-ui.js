import {action,badge,empty,pageHeading} from './ui.js';
import {icon} from './icons.js';
import {e,num,label,relative,tone} from './utils.js';
const recordsButton=src=>action('source-results','Apri immobili','arrow','btn',`data-id="${e(src.id)}" ${src.property_count?'':'disabled'}`);
const toggle=src=>action('toggle-source',src.enabled?'Sospendi':'Abilita',src.enabled?'pause':'play','btn',`data-id="${e(src.id)}" aria-label="${src.enabled?'Sospendi':'Abilita'} ${e(src.name)}"`);
export function sourceDirectory(s,sources){
  const admin=s.user.role==='admin',web=sources.filter(x=>x.kind==='html'),files=sources.filter(x=>x.kind==='import');
  return `${pageHeading('','Fonti e importazioni','',admin?action('import','Importa dati','upload','btn')+action('new-source','Collega fonte','plus','btn primary'):'')}
    <section class="source-directory"><div class="source-directory-heading"><h2>Cataloghi web <span>${num(web.length)}</span></h2><p>Siti collegati alle ricerche automatiche.</p></div>
    <div class="source-grid">${web.map(src=>`<article class="panel source-card"><div class="source-top"><span class="source-symbol">${icon('link')}</span><div><h3>${e(src.name)}</h3><span class="muted small">${e(src.domain)}</span></div>${badge(src.enabled?label(src.status):'In pausa',src.enabled?tone(src.status):'neutral')}</div>
    <div class="source-method"><span>${src.config.browser_navigation?'Hermes · browser':src.config.render_js?'Browser':'HTTP'}</span>${!src.allowed_on_server?'<span class="badge warning">Da abilitare sul server</span>':''}</div>
    <div class="source-metrics"><div><strong>${num(src.property_count)}</strong><span>Immobili acquisiti</span></div><div><strong>${src.property_count?num(src.quality)+'<small>%</small>':'—'}</strong><span>Campi presenti</span></div></div>
    ${src.last_error?`<details class="source-error"><summary>Accesso non riuscito</summary><p>${e(src.last_error)}</p></details>`:''}
    <div class="source-check-date">${src.last_checked?`Ultima verifica ${relative(src.last_checked)}`:'Accesso non ancora verificato'}</div>
    <div class="source-directory-actions">${recordsButton(src)}${admin?action('edit-source','Configura','edit','btn',`data-id="${e(src.id)}"`)+action('probe-source','Verifica accesso','pulse','btn',`data-id="${e(src.id)}" ${src.enabled?'':'disabled'}`)+toggle(src):''}</div></article>`).join('')||empty('Nessun catalogo web','Collega il sito di un’agenzia o un portale.')}</div></section>
    <section class="source-directory"><div class="source-directory-heading"><h2>File importati <span>${num(files.length)}</span></h2><p>Dati caricati manualmente; per aggiornarli importa un nuovo file.</p></div>
    <div class="source-imports panel">${files.map(src=>`<article class="source-import-row"><span class="source-symbol">${icon('upload')}</span><div class="source-import-name"><h3>${e(src.name)}</h3><p>${num(src.property_count)} immobili${src.property_count?` · ${num(src.quality)}% campi presenti`:''}</p></div>${!src.enabled?badge('In pausa','neutral'):''}<div class="source-directory-actions">${recordsButton(src)}${admin?toggle(src):''}</div></article>`).join('')||empty('Nessun file importato','Carica immobili o benchmark con il relativo tracciato CSV.')}</div></section>`;
}
