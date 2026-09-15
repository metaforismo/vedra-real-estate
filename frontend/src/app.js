import {api,setCsrf,toast,downloadExport} from './api.js';
import {shell,loginView,pages,propertyResults,filteredProperties} from './views.js';
import {agentDialog,sourceDialog,importDialog,propertyDialog,runDialog,runContent,compareDialog,userDialog,modalFrame} from './dialogs.js';
import {e,num,activeRun} from './utils.js';

const storage = {
  get(key,fallback){try{return localStorage.getItem(key)||fallback;}catch{return fallback;}},
  set(key,value){try{localStorage.setItem(key,value);}catch{/* Private browsing may deny storage. */}},
};
const initialDataset=storage.get('vedra.dataset','demo');
const s={
  user:null,data:null,page:'overview',dataset:['demo','real','all'].includes(initialDataset)?initialDataset:'demo',
  layout:storage.get('vedra.layout','list'), filters:{q:'',city:'',type:'',strategy:'',status:'',agent_id:'',qualified:false,starred:false,sort:'score'},
  selected:new Set(),users:null,busy:false,mobileNav:false,dialogType:null,currentProperty:null,runId:null,
};
document.documentElement.dataset.theme=storage.get('vedra.theme','light');
let eventSource=null, streamTimer=null, runRefreshTimer=null, previousFocus=null, refreshing=false;
const app=document.getElementById('app');

function render(){
  const y=window.scrollY;
  app.innerHTML=s.user&&s.data?shell(s):loginView();
  window.scrollTo({top:y,behavior:'instant'});
}
async function refresh(quiet=false){
  if(refreshing)return;
  refreshing=true;s.busy=true;
  try{
    s.data=await api(`/workspace?dataset=${encodeURIComponent(s.dataset)}`);
    const valid=new Set(s.data.properties.map(p=>p.id));
    s.selected=new Set([...s.selected].filter(id=>valid.has(id)));
    s.busy=false;render();
    if(s.page==='settings'&&s.user.role==='admin'&&!s.users)loadUsers();
  }catch(error){
    if(error.status===401){setCsrf('');s.user=null;closeModal();render();}
    if(!quiet)toast(error.message,true);
    throw error;
  }finally{refreshing=false;s.busy=false;}
}
async function loadUsers(){
  try{s.users=await api('/users');if(s.page==='settings'&&s.user)render();}catch(err){toast(err.message,true);}
}
function route(){
  const name=location.hash.slice(1).split('?')[0] || 'overview';
  s.page=pages[name]?name:'overview';s.mobileNav=false;
  if(s.user&&s.data){render();window.scrollTo(0,0);if(s.page==='settings'&&s.user.role==='admin')loadUsers();}
}
function openModal(html,type){
  if(!s.dialogType)previousFocus=document.activeElement;
  stopStream();s.dialogType=type;
  document.getElementById('modal-root').innerHTML=html;
  const dialog=document.querySelector('#modal-root dialog');
  dialog.addEventListener('cancel',event=>{event.preventDefault();closeModal();});
  dialog.addEventListener('click',event=>{
    if(event.target===dialog){const rect=dialog.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeModal();}
  });
  dialog.showModal();document.body.classList.add('modal-open');
}
function stopStream(){
  eventSource?.close();eventSource=null;
  clearInterval(streamTimer);clearTimeout(runRefreshTimer);
}
function closeModal(){
  stopStream();s.dialogType=null;s.runId=null;
  const dialog=document.querySelector('#modal-root dialog');
  dialog?.close();document.getElementById('modal-root').innerHTML='';document.body.classList.remove('modal-open');
  if(previousFocus?.isConnected)previousFocus.focus();
}
async function showProperty(id){
  const p=await api(`/properties/${encodeURIComponent(id)}`);s.currentProperty=p;
  openModal(propertyDialog(s,p),'property');
}
async function showRun(id){
  const run=await api(`/runs/${encodeURIComponent(id)}`);
  openModal(runDialog(run),'run');s.runId=id;
  if(activeRun(run)){
    const update=async()=>{
      if(s.runId!==id||s.dialogType!=='run')return;
      try{
        const next=await api(`/runs/${encodeURIComponent(id)}`);
        const container=document.getElementById('run-content');
        if(container)container.innerHTML=runContent(next);
        if(!activeRun(next)){stopStream();await refresh(true);}
      }catch(error){stopStream();toast(error.message,true);}
    };
    eventSource=new EventSource(`/api/runs/${encodeURIComponent(id)}/events`);
    const delayed=()=>{clearTimeout(runRefreshTimer);runRefreshTimer=setTimeout(update,180);};
    eventSource.addEventListener('progress',delayed);
    eventSource.addEventListener('done',update);
    // A small status-poll fallback preserves observability through proxies without SSE.
    streamTimer=setInterval(update,5000);
  }
}
function updateResults(){
  const node=document.getElementById('results-body');
  if(node)node.innerHTML=propertyResults(s);
  const count=document.getElementById('filtered-count');if(count)count.textContent=`${num(filteredProperties(s).length)} risultati`;
  const bar=document.getElementById('selection-bar');if(bar)bar.classList.toggle('visible',s.selected.size>0);
  const selected=document.getElementById('selection-count');if(selected)selected.textContent=s.selected.size;
}
function formError(message){const node=document.getElementById('modal-error');if(node)node.textContent=message;else toast(message,true);}

const actions={
  async logout(){await api('/auth/logout',{method:'POST'});setCsrf('');s.user=null;s.data=null;closeModal();render();},
  'show-password'(el){const input=el.closest('.password-wrap').querySelector('input');input.type=input.type==='password'?'text':'password';el.setAttribute('aria-label',input.type==='password'?'Mostra password':'Nascondi password');},
  async refresh(){await refresh();toast('Workspace aggiornato.');},
  theme(){const value=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=value;storage.set('vedra.theme',value);render();},
  'mobile-menu'(){s.mobileNav=!s.mobileNav;render();},
  'close-modal':closeModal,
  'new-agent'(){openModal(agentDialog(s),'agent');},
  'edit-agent'(el){const agent=s.data.agents.find(a=>a.id===el.dataset.id);if(agent)openModal(agentDialog(s,agent),'agent');},
  async 'run-agent'(el){
    const agent=s.data.agents.find(a=>a.id===el.dataset.id);
    if(activeRun(agent?.last_run)){await showRun(agent.last_run.id);return;}
    const run=await api(`/agents/${encodeURIComponent(el.dataset.id)}/run`,{method:'POST'});
    await refresh(true);await showRun(run.id);
  },
  async 'toggle-agent'(el){await api(`/agents/${encodeURIComponent(el.dataset.id)}/toggle`,{method:'POST'});await refresh(true);toast('Programmazione aggiornata. Una run in corso non viene interrotta.');},
  'run-detail'(el){return showRun(el.dataset.id);},
  async 'cancel-run'(el){await api(`/runs/${encodeURIComponent(el.dataset.id)}/cancel`,{method:'POST'});toast('Annullamento richiesto.');await showRun(el.dataset.id);},
  property(el){return showProperty(el.dataset.id);},
  async star(el){const p=s.data.properties.find(x=>x.id===el.dataset.id);if(!p)return;await api(`/properties/${encodeURIComponent(p.id)}`,{method:'PATCH',body:{starred:!p.starred}});p.starred=!p.starred;if(s.page==='properties')updateResults();else render();},
  async 'detail-star'(el){const p=s.currentProperty;await api(`/properties/${encodeURIComponent(el.dataset.id)}`,{method:'PATCH',body:{starred:!p.starred}});await refresh(true);await showProperty(p.id);},
  layout(el){s.layout=el.dataset.layout;storage.set('vedra.layout',s.layout);render();},
  'agent-results'(el){s.filters.agent_id=el.dataset.id;s.filters.qualified=true;s.filters.city='';s.filters.q='';location.hash='properties';if(s.page==='properties')render();},
  'filter-qualified'(){s.filters.qualified=!s.filters.qualified;render();},
  'filter-star'(){s.filters.starred=!s.filters.starred;render();},
  'reset-filters'(){s.filters={q:'',city:'',type:'',strategy:'',status:'',agent_id:'',qualified:false,starred:false,sort:'score'};render();},
  'clear-selection'(){s.selected.clear();updateResults();},
  compare(){const rows=s.data.properties.filter(p=>s.selected.has(p.id));if(rows.length<2)throw new Error('Seleziona almeno due immobili per confrontarli.');openModal(compareDialog(rows),'compare');},
  async export(el){const rows=s.selected.size?s.data.properties.filter(p=>s.selected.has(p.id)):filteredProperties(s);if(!rows.length)throw new Error('Non ci sono immobili da esportare.');await downloadExport(el.dataset.format||'xlsx',s.dataset,rows.map(p=>p.id));toast(`Esportazione di ${rows.length} immobili pronta.`);},
  'new-source'(){openModal(sourceDialog(),'source');},
  'edit-source'(el){openModal(sourceDialog(s.data.sources.find(x=>x.id===el.dataset.id)),'source');},
  async 'toggle-source'(el){await api(`/sources/${encodeURIComponent(el.dataset.id)}/toggle`,{method:'POST'});await refresh(true);toast('Stato della fonte aggiornato.');},
  async 'probe-source'(el){
    toast('Verifica della fonte avviata. Può richiedere alcuni secondi.');
    const result=await api(`/sources/${encodeURIComponent(el.dataset.id)}/probe`,{method:'POST'});
    await refresh(true);
    openModal(modalFrame(result.ok?'Fonte verificata':'La fonte richiede attenzione',result.notice||'Campione di una ricerca e un annuncio.',`<div class="modal-body"><pre class="json-result">${e(JSON.stringify(result,null,2))}</pre></div>`,'medium-modal'),'probe');
  },
  import(){openModal(importDialog(s),'import');},
  'new-user'(){openModal(userDialog(),'user');},
  async 'runtime-test'(){
    const result=await api('/runtime');
    const node=document.getElementById('runtime-result');
    if(node)node.innerHTML=`<div class="runtime-result ${result.hermes_reachable?'success':''}"><strong>${result.hermes_reachable?'Gateway raggiungibile':result.hermes_configured?'Gateway non raggiungibile':'Hermes non configurato'}</strong><pre>${e(JSON.stringify(result,null,2))}</pre></div>`;
  },
};

document.addEventListener('click',async event=>{
  const anchor=event.target.closest('a[href^="#"]');
  if(anchor&&!event.ctrlKey&&!event.metaKey){event.preventDefault();location.hash=anchor.getAttribute('href');return;}
  const el=event.target.closest('[data-action]');
  if(!el||el.disabled)return;
  const fn=actions[el.dataset.action];if(!fn)return;
  event.preventDefault();
  // Async actions are protected against double clicks without obstructing links.
  const isButton=el.tagName==='BUTTON';if(isButton)el.disabled=true;
  try{await fn(el);}catch(error){toast(error.message,true);}
  finally{if(isButton&&el.isConnected)el.disabled=false;}
});

document.addEventListener('input',event=>{
  if(event.target.id==='property-search'){s.filters.q=event.target.value;updateResults();}
});
document.addEventListener('change',async event=>{
  const input=event.target;
  try{
    if(input.id==='dataset-select'){
      s.dataset=input.value;storage.set('vedra.dataset',s.dataset);s.selected.clear();s.filters.city='';await refresh();
    }
    if(input.dataset.filter){s.filters[input.dataset.filter]=input.value;updateResults();}
    if(input.dataset.selectProperty){
      if(input.checked&&s.selected.size>=3){input.checked=false;toast('Confronta fino a tre immobili alla volta.');return;}
      if(input.checked)s.selected.add(input.dataset.selectProperty);else s.selected.delete(input.dataset.selectProperty);
      updateResults();
    }
    if(input.dataset.review){
      await api(`/properties/${encodeURIComponent(input.dataset.review)}`,{method:'PATCH',body:{review_status:input.value}});
      const p=s.data.properties.find(p=>p.id===input.dataset.review);if(p)p.review_status=input.value;
      toast('Revisione aggiornata.');await refresh(true);
    }
    if(input.id==='import-file'){
      const file=input.files[0];document.getElementById('file-name').textContent=file?`${file.name} · ${Math.ceil(file.size/1024)} KB`:'';
      if(file?.size>4_000_000)throw new Error('Il file supera il limite di 4 MB.');
      if(file&&/\.html?$/i.test(file.name))document.getElementById('import-kind').value='html';
    }
  }catch(error){toast(error.message,true);}
});

document.addEventListener('submit',async event=>{
  const form=event.target;if(!(form instanceof HTMLFormElement))return;
  if(!['login-form','agent-form','source-form','import-form','note-form','user-form'].includes(form.id))return;
  event.preventDefault();
  const submit=form.querySelector('button[type="submit"]');if(submit?.disabled)return;
  const data=new FormData(form);const v=name=>String(data.get(name)||'').trim();
  if(submit){submit.disabled=true;submit.classList.add('loading');}
  const errorNode=document.getElementById(form.id==='login-form'?'login-error':'modal-error');if(errorNode)errorNode.textContent='';
  try{
    if(form.id==='login-form'){
      const auth=await api('/auth/login',{method:'POST',body:{email:v('email'),password:String(data.get('password')||'')}});
      s.user=auth.user;setCsrf(auth.csrf);route();await refresh();return;
    }
    if(form.id==='agent-form'){
      const ids=data.getAll('source_ids');if(!ids.length)throw new Error('Seleziona almeno una fonte.');
      const body={name:v('name'),city:v('city'),source_ids:ids,runtime:v('runtime'),interval_minutes:Number(v('interval_minutes')),active:data.has('active'),criteria:{max_price:Number(v('max_price')),min_surface:Number(v('min_surface')),max_surface:v('max_surface')?Number(v('max_surface')):null,min_discount:v('min_discount')?Number(v('min_discount')):null,max_listings:Number(v('max_listings')),property_types:data.getAll('property_types'),strategies:data.getAll('strategies'),include_auctions:data.has('include_auctions')}};
      await api(`/agents${form.dataset.id?'/'+encodeURIComponent(form.dataset.id):''}`,{method:form.dataset.id?'PUT':'POST',body});
      closeModal();await refresh(true);toast('Agente salvato. Premi Esegui ora per avviare la raccolta.');
    }
    if(form.id==='source-form'){
      let fields;try{fields=JSON.parse(v('fields')||'{}');}catch{throw new Error('Il JSON dei selettori non è valido.');}
      const body={name:v('name'),domain:v('domain'),permission_note:v('permission_note'),permission_confirmed:data.has('permission_confirmed'),config:{search_url:v('search_url'),listing_selector:v('listing_selector'),listing_url_pattern:v('listing_url_pattern'),next_selector:v('next_selector'),max_pages:Number(v('max_pages')),render_js:data.has('render_js'),fields}};
      await api(`/sources${form.dataset.id?'/'+encodeURIComponent(form.dataset.id):''}`,{method:form.dataset.id?'PUT':'POST',body});
      closeModal();s.dataset='real';storage.set('vedra.dataset','real');await refresh(true);toast('Fonte salvata. Verifica il dominio sul server e premi Test.');
    }
    if(form.id==='import-form'){
      const file=form.querySelector('#import-file').files[0];
      if(file?.size>4_000_000)throw new Error('Il file supera 4 MB.');
      const content=v('content')||(file?await file.text():'');if(!content)throw new Error('Seleziona un file oppure incolla il contenuto.');
      const kind=v('kind');if(kind==='html'&&!v('source_url'))throw new Error('Per l’HTML inserisci l’URL originale.');
      const result=await api('/imports',{method:'POST',body:{kind,content,source_url:v('source_url'),is_demo:v('dataset')==='demo',permission_confirmed:data.has('permission_confirmed')}});
      s.dataset=v('dataset');storage.set('vedra.dataset',s.dataset);closeModal();await refresh(true);
      openModal(modalFrame('Importazione completata.','I dati sono stati validati prima della normalizzazione.',`<div class="modal-body"><pre class="json-result">${e(JSON.stringify(result,null,2))}</pre><button class="btn primary full" data-action="close-modal">Torna al workspace</button></div>`),'import-result');
    }
    if(form.id==='note-form'){
      await api(`/properties/${encodeURIComponent(form.dataset.id)}/notes`,{method:'POST',body:{body:v('body')}});
      await showProperty(form.dataset.id);toast('Nota aggiunta.');
    }
    if(form.id==='user-form'){
      await api('/users',{method:'POST',body:{name:v('name'),email:v('email'),password:String(data.get('password')),role:v('role')}});
      closeModal();await loadUsers();toast('Account creato. Comunica la password in modo sicuro.');
    }
  }catch(error){
    if(form.id==='login-form'){const node=document.getElementById('login-error');if(node)node.textContent=error.message;}
    else formError(error.message);
  }finally{if(submit?.isConnected){submit.disabled=false;submit.classList.remove('loading');}}
});

window.addEventListener('hashchange',route);
window.addEventListener('keydown',event=>{
  if(event.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)&&!s.dialogType){
    if(s.page!=='properties')location.hash='properties';
    setTimeout(()=>document.getElementById('property-search')?.focus(),0);event.preventDefault();
  }
});
window.addEventListener('offline',()=>toast('Connessione interrotta. Le azioni non inviate non vengono accodate.',true));

async function boot(){
  route();
  try{const auth=await api('/auth/me');s.user=auth.user;setCsrf(auth.csrf);await refresh();}
  catch(error){if(error.status!==401)toast('Impossibile aprire il workspace: '+error.message,true);render();}
}
boot();
// Refresh the workspace only while jobs are active and do not replace a user's input.
setInterval(()=>{
  if(s.user&&s.data&&!document.hidden&&!s.dialogType&&s.data.runs.some(activeRun)&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))refresh(true).catch(()=>{});
},5000);
