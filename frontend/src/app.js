import {createResearchDrafts} from './research-drafts.js';
import {createBenchmarkController} from './benchmark-controller.js';
import {syncImport,setImportBusy,importPayload,importResultDialog} from './import-ui.js';
import {updateRunContent} from './run-ui.js';
import {createRequestGuard} from './request-guard.js';
import {createCatalogController} from './catalog-controller.js';
import {pagination,defaultFilters} from './catalog-ui.js';
import {createInboxController} from './inbox-controller.js';
import {createBrokersController} from './brokers-ui.js';
import {productActions} from './product-actions.js';
import {api,setCsrf,toast} from './api.js';
import {shell,loginView,pages,propertyResults} from './views.js';
import {agentDialog,sourceDialog,sourceProbeDialog,importDialog,propertyDialog,runDialog,compareDialog,userDialog,modalFrame} from './dialogs.js';
import {e,num,activeRun} from './utils.js';

const storage = {
  get(key,fallback){try{return localStorage.getItem(key)||fallback;}catch{return fallback;}},
  set(key,value){try{localStorage.setItem(key,value);}catch{/* Private browsing may deny storage. */}},
};
const s={
  user:null,data:null,ops:null,notifications:[],page:'overview',dataset:'real',insights:null,
  layout:storage.get('vedra.layout','list'), filters:{q:'',city:'',type:'',strategy:'',status:'',agent_id:'',qualified:false,starred:false,sort:'score'},
  selected:new Set(),users:null,busy:false,mobileNav:false,dialogType:null,currentProperty:null,runId:null,
};
document.documentElement.dataset.theme=storage.get('vedra.theme','light');
let eventSource=null, streamTimer=null, runRefreshTimer=null, previousFocus=null, refreshing=false;
const app=document.getElementById('app');
const modalRequests=createRequestGuard();
const researchDrafts=createResearchDrafts();

function render(){
  // A pending toggle event may arrive after a filter causes a full render.
  const advanced=document.getElementById('catalog-advanced');
  if(advanced)s.catalogAdvanced=advanced.open;
  for(const section of document.querySelectorAll('[data-today-section]')){s.todayExpanded??={};s.todayExpanded[section.dataset.todaySection]=section.open;}
  const y=window.scrollY;
  // Any re-render (background refresh included) must not throw keyboard users back to the top:
  // restore focus by id, or by the action/record a button represents.
  const focus=app.contains(document.activeElement)?document.activeElement:null;
  const saved=focus?.id?{id:focus.id,start:focus.selectionStart,end:focus.selectionEnd}
    :focus?.dataset?.action?{selector:`[data-action="${CSS.escape(focus.dataset.action)}"]${focus.dataset.id?`[data-id="${CSS.escape(focus.dataset.id)}"]`:''}`}:null;
  app.innerHTML=s.user&&s.data?shell(s):loginView();
  window.scrollTo({top:y,behavior:'instant'});
  if(saved){const field=saved.id?document.getElementById(saved.id):document.querySelector(saved.selector);field?.focus({preventScroll:true});if(saved.start!=null)try{field?.setSelectionRange(saved.start,saved.end);}catch{/* not a text field */}}
}
async function refresh(quiet=false){
  if(refreshing)return;
  refreshing=true;s.busy=true;
  const user=s.user;
  try{
    const dataset=encodeURIComponent(s.dataset);
    const result=await Promise.all([api(`/workspace?dataset=${dataset}`),api(`/operations?dataset=${dataset}`),api(`/notifications?dataset=${dataset}`),api('/insights')]);
    if(s.user!==user)return;
    [s.data,s.ops,s.notifications,s.insights]=result;
    // Cross-page selections belong to the archive, not the dashboard's bounded sample.
    s.busy=false;render();
    if(s.page==='properties')await explorer.load({reloadFacets:true});
    if(s.page==='inbox'&&(!quiet||!s.inbox.loaded))await inbox.load();
    if(s.page==='market'&&(!quiet||!s.market.loaded))await market.load();
    if(s.page==='brokers')await brokers.load();
    if(s.page==='settings'&&s.user.role==='admin'&&!s.users)loadUsers();
  }catch(error){
    if(s.user!==user)return;
    if(error.status===401){setCsrf('');researchDrafts.reset();s.user=null;closeModal();render();}
    if(!quiet)toast(error.message,true);
    throw error;
  }finally{refreshing=false;s.busy=false;}
}
async function loadUsers(){
  const user=s.user;
  try{const users=await api('/users');if(s.user!==user)return;s.users=users;if(s.page==='settings'&&s.user)render();}catch(err){toast(err.message,true);}
}
function route(){
  inbox.cancel();market.cancel();brokers.cancel();closeModal();
  const name=location.hash.slice(1).split('?')[0] || 'overview';
  s.page=pages[name]?name:'overview';s.mobileNav=false;
  if(s.user&&s.data){render();window.scrollTo(0,0);if(s.page==='settings'&&s.user.role==='admin')loadUsers();if(s.page==='properties')explorer.load();else explorer.cancel();if(s.page==='inbox')inbox.load();if(s.page==='market')market.load();if(s.page==='brokers')brokers.load();}
}
function openModal(html,type){
  modalRequests.invalidate();
  if(!s.dialogType)previousFocus=document.activeElement;
  stopStream();s.dialogType=type;
  document.getElementById('modal-root').innerHTML=html;
  const dialog=document.querySelector('#modal-root dialog');
  dialog.addEventListener('cancel',event=>{event.preventDefault();closeModal();});
  // Reveal a collapsed field before native validation attempts to focus it.
  dialog.addEventListener('invalid',event=>{
    for(let parent=event.target.parentElement;parent&&parent!==dialog;parent=parent.parentElement){
      if(parent.tagName==='DETAILS')parent.open=true;
    }
  },true);
  dialog.addEventListener('click',event=>{
    if(event.target===dialog){const rect=dialog.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeModal();}
  });
  dialog.showModal();document.body.classList.add('modal-open');
  if(type==='agent')researchDrafts.attach(dialog.querySelector('#agent-form'),s.user);
}
function stopStream(){
  eventSource?.close();eventSource=null;
  clearInterval(streamTimer);clearTimeout(runRefreshTimer);
}
function closeModal(){
  if(s.user&&document.querySelector('#import-form[data-busy="true"],#agent-form[data-saving="true"]'))return;
  modalRequests.invalidate();
  stopStream();s.dialogType=null;s.runId=null;
  const dialog=document.querySelector('#modal-root dialog');
  dialog?.close();document.getElementById('modal-root').innerHTML='';document.body.classList.remove('modal-open');
  if(previousFocus?.isConnected)previousFocus.focus();
}
async function loadModal(title,load,view,type,ready=()=>{}){
  openModal(modalFrame(title,'', '<div class="modal-body" role="status" aria-live="polite">Caricamento…</div>'),'loading');
  const current=modalRequests.capture();
  try{
    const result=await load();
    if(!current())return null;
    openModal(view(result),type);ready(result);
    return modalRequests.capture();
  }catch(error){
    if(current())openModal(modalFrame(title,'',`<div class="modal-body"><p role="alert">${e(error.message)}</p></div>`),'error');
    return null;
  }
}
async function showProperty(id){
  return loadModal('Immobile',()=>api(`/properties/${encodeURIComponent(id)}`),p=>propertyDialog(s,p),'property',p=>{s.currentProperty=p;});
}
async function showRun(id){
  let run;
  const current=await loadModal('Ricerca',()=>api(`/runs/${encodeURIComponent(id)}`),value=>runDialog(value,s.user.role!=='viewer'),'run',value=>{run=value;s.runId=id;});
  if(current&&activeRun(run)){
    let updating=false;
    const update=async()=>{
      if(!current()||updating)return;
      updating=true;
      try{
        const next=await api(`/runs/${encodeURIComponent(id)}`);
        if(!current())return;
        const container=document.getElementById('run-content');
        if(container)updateRunContent(container,next,s.user.role!=='viewer');
        if(!activeRun(next)){stopStream();await refresh(true);}
      }catch(error){if(current()){stopStream();toast(error.message,true);}}
      finally{updating=false;}
    };
    eventSource=new EventSource(`/api/runs/${encodeURIComponent(id)}/events`);
    const delayed=()=>{clearTimeout(runRefreshTimer);runRefreshTimer=setTimeout(update,180);};
    eventSource.addEventListener('progress',delayed);
    eventSource.addEventListener('done',update);
    // A status-poll fallback preserves observability through proxies without SSE.
    streamTimer=setInterval(update,5000);
  }
}
function updateResults(){
  const focusedId=document.activeElement?.id;
  const node=document.getElementById('results-body');
  if(node)node.innerHTML=propertyResults(s);
  const count=document.getElementById('filtered-count');if(count)count.textContent=s.catalog.error?'Risultati non disponibili':s.catalog.loading?'Aggiornamento…':`${num(s.catalog.total)} risultati`;
  const pager=document.getElementById('catalog-pagination');if(pager)pager.innerHTML=pagination(s);
  node?.setAttribute('aria-busy',String(s.catalog.loading));
  const selectPage=document.querySelector('[data-action="select-page"]');if(selectPage)selectPage.disabled=s.catalog.loading||Boolean(s.catalog.error)||!s.catalog.items.length;
  const bar=document.getElementById('selection-bar');if(bar){bar.classList.toggle('visible',s.selected.size>0);bar.inert=!s.selected.size;}
  const compare=bar?.querySelector('[data-action="compare"]');if(compare)compare.disabled=s.selected.size<2||s.selected.size>3;
  const hint=document.getElementById('comparison-hint');if(hint)hint.hidden=s.selected.size>=2&&s.selected.size<=3;
  const selected=document.getElementById('selection-count');if(selected)selected.textContent=s.selected.size;
  if(focusedId)document.getElementById(focusedId)?.focus({preventScroll:true});
}
function formError(message){const node=document.getElementById('modal-error');if(node)node.textContent=message;else toast(message,true);}

const market=createBenchmarkController({s,render});
const explorer=createCatalogController({s,render,updateResults,openModal,closeModal,loadModal,refresh});

const inbox=createInboxController({s,render,refresh,showProperty,showRun});
const brokers=createBrokersController({s,render});

const actions={
  async logout(){await api('/auth/logout',{method:'POST'});setCsrf('');explorer.cancel();inbox.reset();market.reset();researchDrafts.reset();s.todayExpanded={};s.duplicateBusy=false;s.user=null;s.data=null;s.selected.clear();closeModal();render();},
  'quality-filter'(el){s.filters={...defaultFilters(),availability:'all',missing_field:el.dataset.field||'',focus:el.dataset.focus||'all'};s.catalog.page=1;location.hash='properties';},
  'quality-tab'(el){s.qualityTab=el.dataset.tab;render();document.getElementById('quality-'+s.qualityTab)?.focus({preventScroll:true});},
  'show-password'(el){const input=el.closest('.password-wrap').querySelector('input');input.type=input.type==='password'?'text':'password';el.setAttribute('aria-label',input.type==='password'?'Mostra password':'Nascondi password');},
  async refresh(){await refresh();toast('Workspace aggiornato.');},
  theme(){const value=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=value;storage.set('vedra.theme',value);render();},
  'mobile-menu'(){s.mobileNav=!s.mobileNav;render();},
  'close-modal':closeModal,
  'new-agent'(){openModal(agentDialog(s),'agent');},
  'edit-agent'(el){return loadModal('Configura ricerca',async()=>{
    const agent=(await api('/agents')).find(a=>a.id===el.dataset.id);
    if(!agent)throw new Error('Ricerca non più disponibile. Aggiorna l’elenco.');
    return agent;
  },agent=>agentDialog(s,agent),'agent');},
  'duplicate-agent'(el){return loadModal('Duplica ricerca',async()=>{
    const agent=(await api('/agents')).find(a=>a.id===el.dataset.id);
    if(!agent)throw new Error('Ricerca non più disponibile. Aggiorna l’elenco.');
    return {...agent,name:`${agent.name} · copia`.slice(0,100)};
  },agent=>agentDialog(s,agent,true),'agent');},
  'reload-research'(el){
    const form=el.closest('#agent-form');researchDrafts.retarget(form,el.dataset.id);
    return actions['edit-agent'](el);
  },
  async 'run-agent'(el){
    const agent=s.data.agents.find(a=>a.id===el.dataset.id);
    if(activeRun(agent?.last_run)){await showRun(agent.last_run.id);return;}
    let run;
    const current=await loadModal('Avvio ricerca',async()=>{run=await api(`/agents/${encodeURIComponent(el.dataset.id)}/run`,{method:'POST'});await refresh(true);return run;},runDialog,'run');
    if(current?.())await showRun(run.id);
  },
  async 'toggle-agent'(el){await api(`/agents/${encodeURIComponent(el.dataset.id)}/toggle`,{method:'POST'});await refresh(true);toast('Programmazione aggiornata.');},
  'run-detail'(el){return showRun(el.dataset.id);},
  async 'cancel-run'(el){const current=modalRequests.capture();await api(`/runs/${encodeURIComponent(el.dataset.id)}/cancel`,{method:'POST'});toast('Annullamento richiesto.');if(current())await showRun(el.dataset.id);},
  property(el){return showProperty(el.dataset.id);},
  async star(el){const p=[...s.catalog.items,...s.data.properties].find(x=>x.id===el.dataset.id);if(!p)return;await api(`/properties/${encodeURIComponent(p.id)}`,{method:'PATCH',body:{starred:!p.starred}});p.starred=!p.starred;if(s.page==='properties')await explorer.load();else render();},
  async 'detail-star'(el){const p=s.currentProperty;const current=modalRequests.capture();await api(`/properties/${encodeURIComponent(el.dataset.id)}`,{method:'PATCH',body:{starred:!p.starred}});await refresh(true);if(current())await showProperty(p.id);},
  layout(el){s.layout=el.dataset.layout;storage.set('vedra.layout',s.layout);render();},
  'agent-results'(el){closeModal();s.filters={...defaultFilters(),agent_id:el.dataset.id,qualified:true};location.hash='properties';if(s.page==='properties')explorer.change();},
  'source-results'(el){s.filters={...defaultFilters(),availability:'all',source_id:el.dataset.id};s.catalog.page=1;location.hash='properties';if(s.page==='properties')explorer.change();},
  'new-source'(){return loadModal('Collega fonte',async()=>{s.sourcePresets=await api('/source-presets');return s.sourcePresets;},presets=>sourceDialog(null,presets),'source');},
  'edit-source'(el){openModal(sourceDialog(s.data.sources.find(x=>x.id===el.dataset.id)),'source');},
  async 'toggle-source'(el){await api(`/sources/${encodeURIComponent(el.dataset.id)}/toggle`,{method:'POST'});await refresh(true);toast('Stato della fonte aggiornato.');},
  async 'probe-source'(el){
    await loadModal('Verifica fonte',async()=>{
      const result=await api(`/sources/${encodeURIComponent(el.dataset.id)}/probe`,{method:'POST'});
      await refresh(true);return result;
    },sourceProbeDialog,'probe');
  },
  import(el){openModal(importDialog(s,el?.dataset.kind),'import');syncImport(document.getElementById('import-form'));},
  'import-results'(el){closeModal();if(el.dataset.kind==='benchmarks'){location.hash='market';return;}s.filters={...defaultFilters(),availability:'all',source_id:'imports-real'};s.catalog.page=1;location.hash='properties';if(s.page==='properties')explorer.change();},
  'pipeline-layout'(el){s.pipelineLayout=el.dataset.layout;render();document.getElementById('pipeline-layout-'+s.pipelineLayout)?.focus({preventScroll:true});},
  'pipeline-focus'(el){s.pipelineFocus=el.dataset.focus;render();document.getElementById('pipeline-focus-'+s.pipelineFocus)?.focus({preventScroll:true});},
  'reset-pipeline'(){s.pipelineQuery='';s.pipelineAvailability='all';s.pipelineStage='';s.pipelineOwner='';s.pipelineFocus='all';render();document.getElementById('pipeline-search')?.focus();},
  'new-user'(){openModal(userDialog(),'user');},
  async 'ai-test'(el){
    const node=document.getElementById('runtime-result');el.disabled=true;
    try{const r=await api('/runtime/ai-check',{method:'POST'});if(node)node.innerHTML=`<div class="runtime-result success"><strong>Modello raggiungibile</strong><p class="small">${e(r.model)} · ${num(r.latency_ms)} ms</p></div>`;}
    catch(error){if(node)node.innerHTML=`<div class="runtime-result"><strong>Modello non raggiungibile</strong><p class="small">${e(error.message)}</p></div>`;}
    finally{el.disabled=false;}
  },
  async 'runtime-test'(){
    const result=await api('/runtime');
    const node=document.getElementById('runtime-result');
    if(node)node.innerHTML=`<div class="runtime-result ${result.hermes_reachable?'success':''}"><strong>${result.hermes_reachable?'Gateway raggiungibile':result.hermes_configured?'Gateway non raggiungibile':'Hermes non configurato'}</strong><pre>${e(JSON.stringify(result,null,2))}</pre></div>`;
  },
};

const product=productActions({s,refresh,render,openModal,closeModal,loadModal,showProperty,showRun});
Object.assign(actions,product.actions,explorer.actions,inbox.actions,market.actions,brokers.actions);

document.addEventListener('click',async event=>{
  const anchor=event.target.closest('a[href^="#"]');
  if(anchor&&!event.ctrlKey&&!event.metaKey){event.preventDefault();if(anchor.hash==='#main'){document.getElementById('main')?.focus();return;}location.hash=anchor.getAttribute('href');return;}
  const el=event.target.closest('[data-action]');
  if(!el||el.disabled)return;
  const fn=actions[el.dataset.action];if(!fn)return;
  event.preventDefault();
  // Async actions are protected against double clicks without obstructing links.
  const isButton=el.tagName==='BUTTON';if(isButton)el.disabled=true;
  try{await fn(el);}catch(error){toast(error.message,true);}
  finally{if(isButton&&el.isConnected)el.disabled=false;}
});

document.addEventListener('toggle',event=>{
  if(event.target.matches?.('.overview-more')&&event.target.isConnected)s.overviewExpanded=event.target.open;
},true);

document.addEventListener('input',event=>{
  if(event.target.closest('#benchmark-filters')){market.edit(event.target.closest('form'));return;}
  if(event.target.closest('#import-form')){const node=document.getElementById('modal-error');if(node)node.textContent='';return;}
  const form=event.target.closest('#agent-form');
  if(form){
    const count=form.querySelectorAll('.research-advanced input[type="checkbox"]:checked').length+(form.elements.max_surface.value.trim()?1:0);
    const indicator=form.querySelector('[data-filter-indicator]');
    indicator.hidden=!count;indicator.textContent=`${count} ${count===1?'selezionato':'selezionati'}`;
    const hasInstructions=[...form.querySelectorAll('.research-settings input,.research-settings textarea')].some(x=>x.value.trim());
    form.querySelector('[data-instruction-indicator]').hidden=!hasInstructions;
  }
  if(event.target.id==='pipeline-search'){s.pipelineQuery=event.target.value;const pos=event.target.selectionStart;render();const field=document.getElementById('pipeline-search');field?.focus();try{field?.setSelectionRange(pos,pos);}catch{}}
  if(event.target.id==='property-search'){s.filters.q=event.target.value;explorer.load({reset:true,delay:220});}
  if(event.target.id==='broker-search')brokers.input(event.target);
});
document.addEventListener('change',async event=>{
  if(['broker-city','broker-price'].includes(event.target.id)){brokers.input(event.target);return;}
  if(event.target.name==='runtime'&&event.target.closest('#agent-form')){
    const hermes=event.target.closest('#agent-form').querySelector('[data-hermes-only]');if(hermes)hermes.hidden=event.target.value!=='hermes';
  }
  if(event.target.id==='source-preset'){
    const preset=s.sourcePresets?.[event.target.value];
    const form=event.target.closest('form');
    if(!preset||!form)return;
    const values={name:preset.name,domain:preset.domain,...preset.config,fields:JSON.stringify(preset.config.fields,null,2),facts_only:!preset.config.retain_raw_html};
    for(const [name,value] of Object.entries(values)){
      const input=form.elements.namedItem(name);
      if(!input)continue;
      if(input.type==='checkbox')input.checked=!!value;else input.value=String(value);
    }
    return;
  }
  const input=event.target;
  if(input.closest('#import-form')){syncImport(input.closest('form'));const error=document.getElementById('modal-error');if(error)error.textContent='';return;}
  if(input.id==='inbox-kind'){await inbox.actions['inbox-kind'](input);return;}
  if(input.id==='pipeline-stage'){s.pipelineStage=input.value;render();return;}
  if(input.id==='pipeline-owner'){s.pipelineOwner=input.value;render();return;}
  if(input.id==='pipeline-availability'){s.pipelineAvailability=input.value;render();return;}
  try{

    if(input.dataset.filter){s.filters[input.dataset.filter]=input.value;explorer.change();}
    if(input.dataset.range){s.filters[input.dataset.range]=input.value===''?null:Number(input.value);explorer.load({reset:true});}
    if(input.hasAttribute('data-page-size')){s.catalog.page_size=Number(input.value);explorer.load({reset:true});}
    if(input.dataset.selectProperty){
      if(input.checked&&s.selected.size>=100){input.checked=false;toast('Seleziona fino a 100 annunci alla volta.');return;}
      if(input.checked){s.selected.add(input.dataset.selectProperty);}else{s.selected.delete(input.dataset.selectProperty);}
      updateResults();
    }
    if(input.dataset.review){
      await api(`/properties/${encodeURIComponent(input.dataset.review)}`,{method:'PATCH',body:{review_status:input.value}});
      const p=s.data.properties.find(p=>p.id===input.dataset.review);if(p)p.review_status=input.value;
      toast('Revisione aggiornata.');await refresh(true);
    }

  }catch(error){toast(error.message,true);}
});

document.addEventListener('submit',async event=>{
  const form=event.target;if(!(form instanceof HTMLFormElement))return;
  if(form.id==='benchmark-filters'){event.preventDefault();await market.submit(form);return;}
  if(explorer.handles(form.id)){await explorer.submit(event);return;}
  if(product.handles(form.id)){event.preventDefault();await product.submit(form,event);return;}
  if(!['login-form','agent-form','source-form','import-form','note-form','user-form','global-search'].includes(form.id))return;
  event.preventDefault();
  const submit=form.querySelector('button[type="submit"]');if(submit?.disabled)return;
  const data=new FormData(form);const v=name=>String(data.get(name)||'').trim();
  if(submit){submit.disabled=true;submit.classList.add('loading');}
  const errorNode=document.getElementById(form.id==='login-form'?'login-error':'modal-error');if(errorNode)errorNode.textContent='';
  try{
    if(form.id==='global-search'){s.filters={...defaultFilters(),q:v('q')};location.hash='properties';render();await explorer.load({reset:true});return;}
    if(form.id==='login-form'){
      const auth=await api('/auth/login',{method:'POST',body:{email:v('email'),password:String(data.get('password')||'')}});
      s.user=auth.user;setCsrf(auth.csrf);route();await refresh();return;
    }
    if(form.id==='agent-form'){
      const ids=data.getAll('source_ids');if(!ids.length)throw new Error('Seleziona almeno una fonte.');
      const body={name:v('name'),city:v('city'),source_ids:ids,runtime:v('runtime'),interval_minutes:Number(v('interval_minutes')),active:data.has('active'),criteria:{opportunity_only:data.has('opportunity_only'),contact_policy:v('contact_policy'),research_instructions:v('research_instructions'),source_urls:Object.fromEntries(ids.map(id=>[id,v('source_url_'+id)]).filter(([,url])=>url)),custom_prompt:v('custom_prompt').trim(),location_query:v('location_query').trim(),online_discovery:v('runtime')==='scout'||(v('runtime')==='hermes'&&data.has('online_discovery')),min_price:Number(v('min_price')),max_price:Number(v('max_price')),min_surface:Number(v('min_surface')),max_surface:v('max_surface')?Number(v('max_surface')):null,min_discount:v('min_discount')?Number(v('min_discount')):null,max_listings:Number(v('max_listings')),property_types:data.getAll('property_types'),strategies:data.getAll('strategies'),include_auctions:data.has('include_auctions')}};
      body.request_id=researchDrafts.submission(form);
      if(form.dataset.id)body.expected_revision=form.dataset.revision||null;
      form.querySelector('.research-save-conflict').hidden=true;
      const user=s.user;researchDrafts.capture(form);researchDrafts.busy(form,true);
      try{
        await api(`/agents${form.dataset.id?'/'+encodeURIComponent(form.dataset.id):''}`,{method:form.dataset.id?'PUT':'POST',body});
        if(s.user!==user)return;
        researchDrafts.saved(form);researchDrafts.busy(form,false);
        if(form.isConnected)closeModal();
        try{await refresh(true);toast('Ricerca salvata.');}catch{toast('Ricerca salvata. Aggiorna i dati per ricaricare l’elenco.',true);}
      }catch(error){
        if(form.isConnected&&error.status===409&&error.context?.agent_id){
          form.dataset.saveConflict='true';
          const panel=form.querySelector('.research-save-conflict');panel.hidden=false;
          panel.querySelector('button').dataset.id=error.context.agent_id;
        }
        throw error;
      }finally{if(form.isConnected)researchDrafts.busy(form,false);}
    }
    if(form.id==='source-form'){
      let fields;try{fields=JSON.parse(v('fields')||'{}');}catch{throw new Error('Il JSON dei selettori non è valido.');}
      const body={name:v('name'),domain:v('domain'),permission_note:v('permission_note'),permission_confirmed:data.has('permission_confirmed'),config:{retain_images:data.has('retain_images'),retain_raw_html:!data.has('facts_only'),search_url:v('search_url'),probe_city:v('probe_city'),listing_selector:v('listing_selector'),listing_url_pattern:v('listing_url_pattern'),next_selector:v('next_selector'),max_pages:Number(v('max_pages')),discovery_mode:v('discovery_mode')||'links',detail_refresh_hours:Number(v('detail_refresh_hours')||24),render_js:data.has('render_js'),browser_navigation:data.has('browser_navigation'),fields}};
      await api(`/sources${form.dataset.id?'/'+encodeURIComponent(form.dataset.id):''}`,{method:form.dataset.id?'PUT':'POST',body});
      if(form.isConnected)closeModal();s.dataset='real';storage.set('vedra.dataset','real');await refresh(true);toast('Fonte salvata. Ora verifica l’accesso.');
    }
    if(form.id==='import-form'){
      const user=s.user;
      setImportBusy(form,true);
      try{
        const payload=await importPayload(form);
        const result=await api('/imports',{method:'POST',body:payload});
        if(s.user!==user||!form.isConnected)return;
        setImportBusy(form,false);s.dataset='real';s.market.loaded=false;
        openModal(importResultDialog(result),'import-result');
        try{await refresh(true);}catch{toast('Importazione completata. Aggiorna i dati del workspace.',true);}
      }finally{if(form.isConnected)setImportBusy(form,false);}
    }
    if(form.id==='note-form'){
      await api(`/properties/${encodeURIComponent(form.dataset.id)}/notes`,{method:'POST',body:{body:v('body')}});
      if(form.isConnected)await showProperty(form.dataset.id);toast('Nota aggiunta.');
    }
    if(form.id==='user-form'){
      await api('/users',{method:'POST',body:{name:v('name'),email:v('email'),password:String(data.get('password')),role:v('role')}});
      if(form.isConnected)closeModal();await loadUsers();toast('Account creato. Comunica la password in modo sicuro.');
    }
  }catch(error){
    if(form.id==='login-form'){const node=document.getElementById('login-error');if(node)node.textContent=error.message;}
    else if(form.isConnected){formError(error.message);if(form.id==='import-form'){const node=form.querySelector('#modal-error');node?.focus();node?.scrollIntoView({block:'nearest'});}}
  }finally{if(submit?.isConnected){submit.disabled=form.dataset.saveConflict==='true';submit.classList.remove('loading');}}
});

document.addEventListener('error',event=>{if(event.target instanceof HTMLImageElement && event.target.classList.contains('listing-photo'))event.target.remove();},true);
document.addEventListener('toggle',event=>{if(event.target.dataset?.todaySection&&event.target.isConnected){s.todayExpanded??={};s.todayExpanded[event.target.dataset.todaySection]=event.target.open;}if(event.target.id==='catalog-advanced'&&event.target.isConnected)s.catalogAdvanced=event.target.open;},true);
window.addEventListener('hashchange',route);
window.addEventListener('keydown',event=>{
  if(['Enter',' '].includes(event.key)&&event.target.matches('svg [role=button]')){event.preventDefault();event.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));return;}
  if(event.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)&&!s.dialogType){
    if(s.page!=='properties')location.hash='properties';
    setTimeout(()=>document.getElementById('property-search')?.focus(),0);event.preventDefault();
  }
});
window.addEventListener('beforeunload',event=>{if(researchDrafts.hasDrafts()){event.preventDefault();event.returnValue='';}});
window.addEventListener('offline',()=>toast('Connessione interrotta. Le azioni non inviate non vengono accodate.',true));

async function boot(){
  route();
  try{const auth=await api('/auth/me');s.user=auth.user;setCsrf(auth.csrf);await refresh();}
  catch(error){if(error.status!==401)toast('Impossibile aprire il workspace: '+error.message,true);render();}
}
boot();
// Keep background results visible without replacing a user's input.
setInterval(()=>{
  if(s.user&&s.data&&!document.hidden&&!s.dialogType&&!document.activeElement?.closest('.today-panel')&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))refresh(true).catch(()=>{});
},15000);

document.addEventListener("load",event=>{if(event.target instanceof HTMLImageElement&&event.target.classList.contains("listing-photo")){const placeholder=event.target.previousElementSibling;if(placeholder?.classList.contains("photo-placeholder"))placeholder.hidden=true;}},true);
