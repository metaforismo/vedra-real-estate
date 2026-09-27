import {api} from './api.js';
import {modalFrame} from './dialogs.js';
import {historyContent,historyItems,historyFooter} from './history-ui.js';

export function createHistoryController({loadModal,getProperty=()=>null,request=api,findRoot=()=>document.getElementById('history-content')}){
  let view=null,controller=null;
  async function show(id){
    controller?.abort();view=null;
    const property=getProperty(),title=property?.id===id?property.title:'';
    await loadModal('Cronologia',()=>request(`/properties/${encodeURIComponent(id)}/history`),data=>modalFrame('Cronologia',title,historyContent(data,id),'wide-modal history-modal'),'history',data=>{
      view={id,data,root:findRoot(),busy:false};
    });
  }
  async function more(){
    const current=view;
    if(!current||current.busy||!current.data.next_cursor||!current.root?.isConnected)return;
    const {root,id}=current;
    const footer=root.querySelector('#history-footer');
    current.busy=true;controller=new AbortController();
    footer.innerHTML=historyFooter(current.data,id,{loading:true});
    root.setAttribute('aria-busy','true');
    try{
      const data=await request(`/properties/${encodeURIComponent(id)}/history?before=${encodeURIComponent(current.data.next_cursor)}`,{signal:controller.signal});
      if(view!==current||!root.isConnected)return;
      const seen=new Set(current.data.items.map(row=>row.id)),fresh=data.items.filter(row=>!seen.has(row.id));
      current.data={...data,items:[...current.data.items,...fresh]};
      root.querySelector('.history-events').insertAdjacentHTML('beforeend',historyItems(fresh));
      footer.innerHTML=historyFooter(current.data,id);
    }catch(error){
      if(view!==current||!root.isConnected)return;
      footer.innerHTML=historyFooter(current.data,id,{error:error.message});
    }finally{
      current.busy=false;
      if(view===current&&root.isConnected){root.setAttribute('aria-busy','false');(root.querySelector('#history-more')||root.querySelector('#history-count'))?.focus({preventScroll:true});}
    }
  }
  return {actions:{'property-history':el=>show(el.dataset.id),'history-more':more}};
}
