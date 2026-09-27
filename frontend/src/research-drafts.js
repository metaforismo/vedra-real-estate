// Drafts belong to this page session and user; never persist research text to storage.
export function researchSnapshot(form){
  const values={};
  for(const field of form.elements){
    if(!field.name||['submit','button','reset','fieldset'].includes(field.type))continue;
    const checkbox=['checkbox','radio'].includes(field.type);
    const key=checkbox?`${field.name}:${field.value}`:field.name;
    values[key]=checkbox?field.checked:field.value;
  }
  return values;
}
const signature=values=>JSON.stringify(Object.keys(values).sort().map(key=>[key,values[key]]));
export function applyResearchSnapshot(form,values){
  let omitted=0;
  const available=new Set();
  for(const field of form.elements){
    if(!field.name||['submit','button','reset','fieldset'].includes(field.type))continue;
    const checkbox=['checkbox','radio'].includes(field.type),key=checkbox?`${field.name}:${field.value}`:field.name;
    available.add(key);
    if(!(key in values))continue;
    // A disabled source or removed runtime must not be re-enabled by a stale draft.
    if(field.disabled){if(values[key]!== (checkbox?field.checked:field.value))omitted++;continue;}
    if(checkbox)field.checked=values[key];
    else if(field.tagName==='SELECT'&&![...field.options].some(option=>option.value===values[key]&&!option.disabled))omitted++;
    else field.value=values[key];
  }
  for(const key of Object.keys(values))if(!available.has(key)&&values[key])omitted++;
  return omitted;
}
export function createResearchDrafts(){
  const drafts=new Map(),requests=new Map(),forms=new WeakMap();
  function paint(form){
    const state=forms.get(form);if(!state||!form.isConnected)return;
    const draft=state.readonly?null:drafts.get(state.key),busy=form.dataset.saving==='true';
    const bar=form.querySelector('.research-draft-bar');
    bar.hidden=!draft&&!busy&&!state.notice;
    bar.querySelector('[role="status"]').textContent=busy?'Salvataggio…':state.conflict?'Configurazione aggiornata dal team':state.notice||'Bozza non salvata';
    bar.querySelector('.research-draft-help').textContent=busy?'':state.conflict?'La bozza è separata dalla versione attuale.':draft?'Salva per conservarla dopo il ricaricamento.':'';
    const restore=bar.querySelector('[data-research-draft="restore"]');
    restore.hidden=!state.conflict;restore.disabled=busy;
    const discard=bar.querySelector('[data-research-draft="discard"]');
    discard.hidden=!draft;discard.disabled=busy;
    form.setAttribute('aria-busy',String(busy));
  }
  function capture(form){
    const state=forms.get(form);if(!state||state.readonly||form.dataset.saving==='true')return;
    // Resolve a conflicting old draft explicitly before changing the current version.
    if(state.conflict)return;
    const values=researchSnapshot(form);
    if(signature(values)===signature(state.base)){drafts.delete(state.key);state.notice='';}
    else drafts.set(state.key,{base:state.base,values});
    paint(form);
  }
  function restore(form){
    const state=forms.get(form),draft=drafts.get(state?.key);if(!draft||state.readonly)return;
    const omitted=applyResearchSnapshot(form,draft.values);
    state.conflict=false;
    form.querySelector('fieldset').disabled=false;
    capture(form);form.dispatchEvent(new Event('input',{bubbles:true}));
    state.notice=omitted?'Bozza ripresa: controlla fonti e motore':'Bozza ripristinata';
    form.querySelector('[name="name"]')?.focus({preventScroll:true});
    paint(form);
  }
  function discard(form){
    const state=forms.get(form);if(!state)return;
    drafts.delete(state.key);requests.delete(state.key);state.conflict=false;state.notice='';
    form.querySelector('fieldset').disabled=state.readonly;
    applyResearchSnapshot(form,state.base);paint(form);
    form.dispatchEvent(new Event('input',{bubbles:true}));
    form.querySelector('[name="name"]')?.focus({preventScroll:true});
  }
  function attach(form,user){
    if(!form)return;
    const key=JSON.stringify([user.id,form.dataset.id||'new']);
    const readonly=user.role==='viewer',base=researchSnapshot(form);
    const draft=readonly?null:drafts.get(key);
    const state={key,userId:user.id,base,readonly,conflict:Boolean(draft&&signature(draft.base)!==signature(base)),notice:''};forms.set(form,state);
    form.insertAdjacentHTML('afterbegin','<div class="research-draft-bar" hidden><div><p role="status"></p><small class="research-draft-help"></small></div><div class="research-draft-actions"><button type="button" class="btn" data-research-draft="restore" hidden>Riprendi bozza</button><button type="button" class="text-button" data-research-draft="discard" hidden>Scarta bozza</button></div></div>');
    form.addEventListener('input',()=>capture(form));form.addEventListener('change',()=>capture(form));
    form.addEventListener('click',event=>{
      const button=event.target.closest('[data-research-draft]');if(!button||button.disabled)return;
      if(button.dataset.researchDraft==='restore')restore(form);else discard(form);
    });
    if(state.conflict)form.querySelector('fieldset').disabled=true;
    else if(draft)restore(form);
    paint(form);
  }
  function busy(form,value){
    form.dataset.saving=String(value);const state=forms.get(form);
    form.querySelector('fieldset').disabled=value||state?.readonly||state?.conflict||false;
    const close=form.closest?.('dialog')?.querySelector('.modal-close');if(close)close.disabled=value;
    const submit=form.querySelector('button[type="submit"]');
    if(submit&&state){state.submitHTML??=submit.innerHTML;if(value)submit.textContent='Salvataggio…';else submit.innerHTML=state.submitHTML;}
    paint(form);
  }
  function saved(form){const state=forms.get(form);if(!state)return;drafts.delete(state.key);requests.delete(state.key);state.base=researchSnapshot(form);state.notice='';state.conflict=false;paint(form);}
  function submission(form){
    const state=forms.get(form);
    if(!requests.has(state.key))requests.set(state.key,crypto.randomUUID());
    return requests.get(state.key);
  }
  function retarget(form,id){
    capture(form);
    const state=forms.get(form),key=JSON.stringify([state.userId,id]);
    const draft=drafts.get(state.key);
    drafts.delete(state.key);requests.delete(state.key);
    if(draft)drafts.set(key,draft);
    state.key=key;form.dataset.id=id;
  }
  return {attach,capture,busy,saved,submission,retarget,reset(){drafts.clear();requests.clear();},hasDrafts:()=>drafts.size>0};
}
