import {api,toast,downloadExport,downloadCatalog} from './api.js';
import {modalFrame,compareDialog} from './dialogs.js';
import {defaultFilters,bulkReviewForm,historyContent,preflightContent} from './catalog-ui.js';

export function createCatalogController({s,render,updateResults,openModal,closeModal,refresh}){
  let controller=null,generation=0,timer=null,reviewRows=[];
  s.catalog={items:[],total:0,page:1,page_size:50,pages:1,has_next:false,loading:false,error:null,facets:null};
  s.filters={...defaultFilters(),...s.filters};
  function cancel(){clearTimeout(timer);controller?.abort();generation++;s.catalog.loading=false;}
  function load({reset=false,delay=0,reloadFacets=false}={}){
    cancel();if(reset)s.catalog.page=1;
    if(!s.user||s.page!=='properties')return Promise.resolve();
    const ticket=++generation;
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
  async function showHistory(id,before){
    const data=await api(`/properties/${encodeURIComponent(id)}/history${before?'?before='+encodeURIComponent(before):''}`);
    openModal(modalFrame('Cronologia delle evidenze','Variazioni osservate, non uno storico ricostruito.',historyContent(data,id),'wide-modal'),'history');
  }
  const actions={
    'catalog-retry':()=>load(),
    'catalog-next'(){if(s.catalog.has_next){s.catalog.page++;return load();}},
    'catalog-prev'(){s.catalog.page=Math.max(1,s.catalog.page-1);return load();},
    'catalog-focus'(el){s.filters.focus=el.dataset.focus;return change();},
    'filter-qualified'(){s.filters.qualified=!s.filters.qualified;return change();},
    'filter-star'(){s.filters.starred=!s.filters.starred;return change();},
    'reset-filters'(){s.filters=defaultFilters();return change();},
    'apply-view'(el){const view=s.ops.saved_views.find(x=>x.id===el.dataset.id);if(view){s.filters={...defaultFilters(),...view.filters};return change();}},
    'select-page'(){for(const p of s.catalog.items){if(s.selected.size>=100)break;s.selected.add(p.id);}updateResults();},
    'clear-selection'(){s.selected.clear();updateResults();},
    async compare(){if(s.selected.size<2||s.selected.size>3)throw new Error('Per il confronto seleziona due o tre annunci.');openModal(compareDialog(await selection()),'compare');},
    async export(el){
      if(s.selected.size)await downloadExport(el.dataset.format||'xlsx','real',[...s.selected]);
      else await downloadCatalog(el.dataset.format||'xlsx',s.filters);
      toast('Esportazione completata.');
    },
    async 'bulk-review'(){reviewRows=await selection();openModal(modalFrame('Revisione multipla','Conferma una decisione per il team.',bulkReviewForm(reviewRows)),'bulk-review');},
    async 'property-history'(el){await showHistory(el.dataset.id);},
    async 'history-more'(el){await showHistory(el.dataset.id,el.dataset.before);},
    async 'agent-readiness'(el){const data=await api(`/agents/${encodeURIComponent(el.dataset.id)}/preflight`);openModal(modalFrame('Diagnostica agente','Configurazione, fonti e worker.',preflightContent(data,s.user.role!=='viewer'),'wide-modal'),'preflight');},
  };
  async function submit(event){
    const form=event.target;if(form.id!=='bulk-review-form')return false;
    event.preventDefault();const button=event.submitter;if(button)button.disabled=true;
    const fields=new FormData(form);
    try{
      const result=await api('/catalog/review',{method:'POST',body:{items:reviewRows.map(p=>({id:p.id,version:p.work_version})),stage:fields.get('stage'),note:fields.get('note')}});
      closeModal();s.selected.clear();await refresh(true);toast(`${result.count} revisioni aggiornate.`);
    }catch(error){document.getElementById('modal-error').textContent=error.message;}
    finally{if(button?.isConnected)button.disabled=false;}
    return true;
  }
  return {actions,load,cancel,change,submit,handles:id=>id==='bulk-review-form'};
}
