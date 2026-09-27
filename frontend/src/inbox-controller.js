import {api,toast} from './api.js';
import {createRequestGuard} from './request-guard.js';
export const inboxState=()=>({items:[],unread:false,kind:'all',loading:false,loaded:false,error:'',moreError:'',has_more:false,next_cursor:null,total:0,unread_total:0});
export function createInboxController({s,render,refresh,showProperty,showRun,request=api,notify=toast,focus=id=>{const target=document.getElementById(id);(target&&!target.disabled?target:document.getElementById('inbox-results'))?.focus({preventScroll:true});}}){
  s.inbox=inboxState();
  const guard=createRequestGuard();let abort=null,intent=0;
  function cancel(){intent++;guard.invalidate();abort?.abort();s.inbox.loading=false;}
  function reset(){cancel();s.inbox=inboxState();s.inboxBusy=false;}
  async function load({more=false,focusId=''}={}){
    if(s.page!=='inbox')return;
    if(more&&(!s.inbox.has_more||s.inbox.loading))return;
    guard.invalidate();abort?.abort();abort=new AbortController();const current=guard.capture(),user=s.user;
    const box=s.inbox;box.loading=true;box.error='';box.moreError='';
    if(!more){box.items=[];box.loaded=false;box.has_more=false;box.next_cursor=null;}
    const query=new URLSearchParams({unread:String(box.unread),kind:box.kind});
    if(more&&box.next_cursor){query.set('before_created_at',box.next_cursor.created_at);query.set('before_id',box.next_cursor.id);}
    render();if(focusId)focus(focusId);
    try{
      const data=await request('/notifications/feed?'+query,{signal:abort.signal});
      if(!current()||s.user!==user||s.page!=='inbox')return;
      const items=more?[...box.items,...data.items]:data.items;
      Object.assign(box,data,{items:[...new Map(items.map(row=>[row.id,row])).values()],loaded:true,loading:false});
      if(s.ops)s.ops.unread=data.unread_total;
    }catch(error){
      if(!current()||s.user!==user||s.page!=='inbox')return;
      box.loading=false;
      if(error.name!=='AbortError')box[more?'moreError':'error']=error.message;
    }
    if(current()&&s.user===user&&s.page==='inbox'){render();if(focusId)focus(focusId);}
  }
  async function mark(el,open=false,all=false){
    if(s.inboxBusy)return;
    const item=all?null:[...s.inbox.items,...(s.notifications||[])].find(row=>row.id===el.dataset.id);
    if(!all&&!item)return;
    s.inboxBusy=true;const page=s.page,user=s.user,version=++intent;
    render();
    try{
      if(all||!item.read_at)await request(all?'/notifications/read-all':`/notifications/${encodeURIComponent(item.id)}/read`,{method:'POST'});
      await refresh(true);
      if(s.user===user&&s.page==='inbox')await load();
      if(s.user===user&&page===s.page&&version===intent){
        if(open&&item?.property_id)await showProperty(item.property_id);
        else if(open&&item?.run_id)await showRun(item.run_id);
      }
    }catch(error){notify(error.message,true);}
    finally{if(s.user===user){s.inboxBusy=false;render();if(!open&&s.page==='inbox'&&version===intent)focus('inbox-all');}}
  }
  return {load,cancel,reset,actions:{
    'inbox-filter'(el){intent++;s.inbox.unread=el.dataset.unread==='true';return load({focusId:s.inbox.unread?'inbox-unread':'inbox-all'});},
    'inbox-kind'(el){intent++;s.inbox.kind=el.value;return load({focusId:'inbox-kind'});},
    'inbox-more'(){return load({more:true,focusId:'inbox-more'});},
    'inbox-retry'(){return load({focusId:'inbox-all'});},
    'notification-open'(el){return mark(el,true);},
    'notification-read'(el){return mark(el);},
    'read-all'(el){return mark(el,false,true);},
  }};
}
