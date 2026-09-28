import {setupComparison} from './comparison-ui.js';
import {createHistoryController} from './history-controller.js';
import {api,toast,downloadExport,downloadCatalog} from './api.js';
import {modalFrame,compareDialog} from './dialogs.js';
import {defaultFilters,activeFilters,filtered,bulkReviewForm,preflightContent} from './catalog-ui.js';
import {readinessContent} from './agents-ui.js';
import {num} from './utils.js';

export function createCatalogController({s,render,updateResults,openModal,closeModal,loadModal,refresh}){
  let controller=null,generation=0,timer=null,reviewRows=[];
  s.catalog={items:[],total:0,page:1,page_size:50,pages:1,has_next:false,loading:false,error:null,facets:null};
  s.filters={...defaultFilters(),...s.filters};
  // Range inputs reload without a full render (it would steal focus mid-typing): keep chips, count and reset in step.
  function syncFilterChrome(){
    if(typeof document==='undefined')return;
    const chips=activeFilters(s);
    const list=document.getElementById('catalog-active');if(list)list.innerHTML=chips.join('');
    const count=document.querySelector('.catalog-filters-btn .filters-count');if(count){count.textContent=chips.length;count.hidden=!chips.length;}
    const reset=document.getElementById('catalog-reset');if(reset)reset.hidden=!filtered(s);
  }
  function cancel(){clearTimeout(timer);controller?.abort();generation++;s.catalog.loading=false;}
  function load({reset=false,delay=0,reloadFacets=false}={}){
    cancel();if(reset)s.catalog.page=1;
    if(!s.user||s.page!=='properties')return Promise.resolve();
    const ticket=++generation;
    syncFilterChrome();
    s.catalog.loading=true;s.catalog.error=null;updateResults();
    const execute=async()=>{
      controller=new AbortController();
      const params=new URLSearchParams();
      for(const [key,value] of Object.entries({...s.filters,page:s.catalog.page,page_size:s.catalog.page_size})){
        if(value!==null&&value!==undefined&&value!=='')params.set(key,String(value));
      }
      try{
        const needsFacets=reloadFacets||!s.catalog.facets;
        const [data,facets]=await Promise.all([api('/catalog?'+params,{signal:controller.signal}),needsFacets?api('/catalog/facets',{signal:controller.signal}):Promise.resolve(s.catalog.facets)]);
        if(ticket!==generation||s.page!=='properties')return;
        Object.assign(s.catalog,data,{facets,loading:false,error:null});
        if(needsFacets)render();else updateResults();
      }catch(error){
        if(ticket!==generation||error.name==='AbortError')return;
        s.catalog.loading=false;s.catalog.error=error.message;s.catalog.items=[];
        updateResults();
      }
    };
    if(delay){timer=setTimeout(execute,delay);return Promise.resolve();}
    return execute();
  }
  function change(reset=true){render();return load({reset});}
  async function selection(){
    if(!s.selected.size)throw new Error('Seleziona almeno un annuncio.');
    return (await api('/catalog/selection',{method:'POST',body:{ids:[...s.selected]}})).items;
  }
  const actions={
    'catalog-retry':()=>load(),
    'clear-source-filter'(){s.filters.source_id='';return change();},
    'clear-missing-field'(){s.filters.missing_field='';return change();},
    'catalog-next'(){if(s.catalog.has_next){s.catalog.page++;return load();}},
    'catalog-prev'(){s.catalog.page=Math.max(1,s.catalog.page-1);return load();},
    // The panel is a <details> row (its state survives re-renders through app.js); this button in the bar drives it.
    'catalog-filters-toggle'(el){const panel=document.getElementById('catalog-advanced');if(!panel)return;panel.open=!panel.open;s.catalogAdvanced=panel.open;el.setAttribute('aria-expanded',String(panel.open));},
    'catalog-focus'(el){s.filters.focus=el.dataset.focus;return change();},
    'filter-qualified'(){s.filters.qualified=!s.filters.qualified;return change();},
    'filter-star'(){s.filters.starred=!s.filters.starred;return change();},
    'reset-filters'(){s.filters=defaultFilters();return change();},
    'catalog-clear-filter'(el){const d=defaultFilters();for(const key of el.dataset.keys.split(','))s.filters[key]=d[key];return change();},
    // Column headers sort in the server's single direction for that key; a second click returns to the default order.
    'catalog-sort'(el){s.filters.sort=s.filters.sort===el.dataset.sort?'score':el.dataset.sort;return change();},
    'apply-view'(el){const view=s.ops.saved_views.find(x=>x.id===el.dataset.id);if(view){s.filters={...defaultFilters(),...view.filters};return change();}},
    // Header checkbox: a fully selected page is cleared, otherwise the page is added up to the 100-item limit.
    'select-page'(){
      if(s.catalog.loading||s.catalog.error)return;
      const items=s.catalog.items;
      if(items.length&&items.every(p=>s.selected.has(p.id)))for(const p of items)s.selected.delete(p.id);
      else for(const p of items){if(s.selected.size>=100)break;s.selected.add(p.id);}
      updateResults();
      // Pages are the fast way to approach the limit, so the bar names it only then.
      if(typeof document!=='undefined'){const limit=document.getElementById('selection-limit');if(limit)limit.hidden=s.selected.size<90;}
    },
    'clear-selection'(){s.selected.clear();updateResults();},
    async compare(){if(s.selected.size<2||s.selected.size>3)throw new Error('Per il confronto seleziona due o tre annunci.');const ids=[...s.selected];await loadModal('Confronto',()=>Promise.all(ids.map(id=>api(`/properties/${encodeURIComponent(id)}`))),compareDialog,'compare',()=>setupComparison(document.querySelector('.comparison-modal')));},
    async 'comparison-export'(el){await downloadExport('xlsx',JSON.parse(el.dataset.ids));toast('Esportazione completata.');},
    async export(el){
      if(el.dataset.exportScope==='selection'){
        if(!s.selected.size)throw new Error('Seleziona almeno un annuncio da esportare.');
        await downloadExport(el.dataset.format||'xlsx',[...s.selected]);
      }
      else await downloadCatalog(el.dataset.format||'xlsx',s.filters);
      toast('Esportazione completata.');
    },
    async 'bulk-review'(){await loadModal('Revisione multipla',selection,rows=>modalFrame('Revisione multipla','',bulkReviewForm(rows)),'bulk-review',rows=>{reviewRows=rows;});},
    async 'agent-readiness'(el){await loadModal('Controlla i requisiti',()=>api(`/agents/${encodeURIComponent(el.dataset.id)}/preflight`),data=>modalFrame('Controlla i requisiti','',readinessContent(data,s.user.role!=='viewer'),'medium-modal readiness-modal'),'preflight');},
  };
  Object.assign(actions,createHistoryController({loadModal,getProperty:()=>s.currentProperty}).actions);
  async function submit(event){
    const form=event.target;if(form.id!=='bulk-review-form')return false;
    event.preventDefault();const button=event.submitter;if(button?.disabled)return true;if(button)button.disabled=true;
    const fields=new FormData(form);
    try{
      const result=await api('/catalog/review',{method:'POST',body:{items:reviewRows.map(p=>({id:p.id,version:p.work_version})),stage:fields.get('stage'),note:fields.get('note')}});
      if(form.isConnected)closeModal();s.selected.clear();await refresh(true);toast(result.count===1?'1 revisione aggiornata.':`${num(result.count)} revisioni aggiornate.`);
    }catch(error){if(form.isConnected)form.querySelector('#modal-error').textContent=error.message;}
    finally{if(button?.isConnected)button.disabled=false;}
    return true;
  }
  return {actions,load,cancel,change,submit,handles:id=>id==='bulk-review-form'};
}
