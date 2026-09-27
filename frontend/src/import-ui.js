import {modalFrame} from './dialogs.js';
import {icon} from './icons.js';
import {e,num,selectOptions} from './utils.js';

const formats={
  csv:{name:'CSV immobili',accept:'.csv,.txt,text/csv',hint:'CSV UTF-8 · massimo 4 MB · fino a 2.000 righe',placeholder:'title,price,surface,city,…',template:'properties'},
  html:{name:'HTML singolo annuncio',accept:'.html,.htm,.txt,text/html',hint:'HTML UTF-8 · massimo 4 MB · un annuncio',placeholder:'Incolla il documento HTML originale',template:null},
  benchmarks:{name:'CSV prezzi di zona',accept:'.csv,.txt,text/csv',hint:'CSV UTF-8 · massimo 4 MB · fino a 2.000 righe',placeholder:'city,zone,property_type,condition,…',template:'benchmarks'},
};
export function importDialog(s,kind='csv'){
  if(!formats[kind])kind='csv';
  return modalFrame('Importa dati','',`<form id="import-form" class="modal-form"><fieldset class="import-fields">
    <label>Tipo di importazione<select name="kind" id="import-kind" aria-label="Tipo di importazione">${selectOptions(Object.entries(formats).map(([k,v])=>[k,v.name]),kind)}</select></label>
    <fieldset class="import-mode"><legend>Contenuto da importare</legend><label><input type="radio" name="input_mode" value="file" checked>Carica file</label><label><input type="radio" name="input_mode" value="paste">Incolla testo</label></fieldset>
    <div data-import-file class="import-file-panel"><label for="import-file">File da importare</label><input id="import-file" name="file" type="file" accept="${formats[kind].accept}" aria-describedby="import-format-hint"><p id="file-name" role="status"></p></div>
    <label data-import-paste hidden>Contenuto da importare<textarea name="content" rows="7" class="code-input" spellcheck="false" disabled></textarea></label>
    <div class="import-format-row"><p id="import-format-hint">${formats[kind].hint}</p><a id="import-template" href="/public/examples/${formats[kind].template||'properties'}.csv" download ${formats[kind].template?'':'hidden'}>${icon('download')} Scarica tracciato</a></div>
    <label data-import-url ${kind==='html'?'':'hidden'}>URL originale<input name="source_url" type="url" ${kind==='html'?'required':'disabled'} placeholder="https://agenzia.it/immobile/123"></label>
    <p class="import-benchmark-note" ${kind==='benchmarks'?'':'hidden'}>Per le quotazioni OMI usa la sezione Prezzi di zona.</p>
    <label class="checkbox-label"><input type="checkbox" name="permission_confirmed" required> Confermo provenienza e diritto di utilizzo dei dati.</label>
    <div class="form-error" id="modal-error" role="alert" tabindex="-1"></div>
    <div class="modal-form-footer"><button type="button" class="btn" data-action="close-modal">Annulla</button><button type="submit" class="btn primary">${icon('upload')} Importa</button></div>
    </fieldset></form>`,'medium-modal import-modal');
}
export function syncImport(form){
  const kind=form.elements.kind.value,format=formats[kind],fileMode=form.elements.input_mode.value==='file';
  form.querySelector('[data-import-file]').hidden=!fileMode;
  form.querySelector('[data-import-paste]').hidden=fileMode;
  form.elements.file.disabled=!fileMode;form.elements.content.disabled=fileMode;
  form.elements.file.accept=format.accept;form.elements.content.placeholder=format.placeholder;
  form.querySelector('[data-import-url]').hidden=kind!=='html';
  form.elements.source_url.disabled=kind!=='html';form.elements.source_url.required=kind==='html';
  form.querySelector('.import-benchmark-note').hidden=kind!=='benchmarks';
  form.querySelector('#import-format-hint').textContent=format.hint;
  const link=form.querySelector('#import-template');link.hidden=!format.template;link.href=`/public/examples/${format.template||'properties'}.csv`;
  const file=form.elements.file.files[0];
  form.querySelector('#file-name').textContent=file?`${file.name} · ${num(Math.ceil(file.size/1024))} KB`:'';
}
export function setImportBusy(form,busy){
  form.dataset.busy=String(busy);form.setAttribute('aria-busy',String(busy));
  form.querySelector('.import-fields').disabled=busy;
  const dialog=form.closest('dialog');dialog?.querySelector('.modal-close')?.toggleAttribute('disabled',busy);
  form.querySelector('[type="submit"]').innerHTML=busy?'Importazione…':`${icon('upload')} Importa`;
  if(!busy)syncImport(form);
}
export async function importPayload(form){
  const kind=form.elements.kind.value,mode=form.elements.input_mode.value;
  let content='';
  if(mode==='paste')content=form.elements.content.value;
  else{
    const file=form.elements.file.files[0];
    if(!file)throw new Error('Seleziona un file.');
    if(file.size>4_000_000)throw new Error('Il file supera 4 MB.');
    if(kind==='html'?!/\.(html?|txt)$/i.test(file.name):!/\.(csv|txt)$/i.test(file.name))throw new Error(kind==='html'?'Seleziona un file HTML.':'Seleziona un file CSV.');
    try{content=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());}
    catch{throw new Error('Il file non è leggibile in UTF-8. Salvalo in UTF-8 e riprova.');}
  }
  if(!content.trim())throw new Error(mode==='paste'?'Incolla il contenuto da importare.':'Il file è vuoto.');
  if(new TextEncoder().encode(content).length>4_000_000)throw new Error('Il contenuto supera 4 MB.');
  return {kind,content,source_url:kind==='html'?form.elements.source_url.value.trim():'',permission_confirmed:form.elements.permission_confirmed.checked};
}
export function importResultDialog(result){
  const benchmark=result.kind==='benchmarks';
  const stats=benchmark?[['Righe importate',result.imported]]:[['Nuovi',result.new],['Aggiornati',result.changed],['Invariati',Math.max(0,result.imported-result.new-result.changed)]];
  return modalFrame('Importazione completata','',`<div class="modal-body import-result"><p>${num(result.imported)} ${result.imported===1?'riga elaborata':'righe elaborate'}</p><div class="import-result-stats">${stats.map(([name,value])=>`<div><strong>${num(value)}</strong><span>${e(name)}</span></div>`).join('')}</div>${benchmark?'<p>Le righe della stessa serie e periodo sostituiscono quelle già presenti.</p>':''}<details><summary>Dettagli importazione</summary><pre class="json-result">${e(JSON.stringify(result,null,2))}</pre></details><div class="modal-form-footer"><button class="btn" data-action="close-modal">Chiudi</button><button class="btn primary" data-action="import-results" data-kind="${e(result.kind)}">${benchmark?'Apri benchmark':'Apri immobili importati'} ${icon('arrow')}</button></div></div>`,'medium-modal import-modal');
}
