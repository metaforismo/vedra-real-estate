import {api} from './api.js';
import {createRequestGuard} from './request-guard.js';
export function createBenchmarkController({s,render:draw,request=api,focus=()=>document.getElementById('benchmark-results')?.focus({preventScroll:true})}){
  const initial=()=>({items:[],q:'',condition:'',currency:'',page:1,loaded:false,loading:false,error:''});
  s.market=initial();
  // Filters apply while typing: a re-render must not steal the field (or the caret) from the user.
  const render=()=>{
    const a=typeof document==='undefined'?null:document.activeElement,id=a?.id,pos=a?.selectionStart;draw();
    const n=id&&document.getElementById(id);if(n&&n!==a){n.focus({preventScroll:true});if(pos!=null&&n.setSelectionRange)try{n.setSelectionRange(pos,pos);}catch{/* not a text field */}}
  };
  const guard=createRequestGuard();let abort,timer;
  function cancel(){clearTimeout(timer);guard.invalidate();abort?.abort();s.market.loading=false;}
  async function load({focusResult=false}={}){
    if(s.page!=='market')return;
    cancel();abort=new AbortController();const current=guard.capture(),user=s.user,m=s.market;
    m.loading=true;m.error='';m.items=[];render();
    try{
      const data=await request('/benchmarks/catalog?'+new URLSearchParams({q:m.q,condition:m.condition,currency:m.currency,page:m.page}),{signal:abort.signal});
      if(!current()||s.user!==user||s.page!=='market')return;
      Object.assign(m,data,{loaded:true,loading:false});
    }catch(error){if(!current()||s.user!==user||s.page!=='market')return;m.loading=false;m.error=error.message;}
    render();if(focusResult)focus();
  }
  return {load,cancel,reset(){cancel();s.market=initial();},edit(form){
    const data=new FormData(form),m=s.market,draft=Object.fromEntries(['q','condition','currency'].map(k=>[k,String(data.get(k)??m[k]??'')]));
    const typed=draft.q.trim()!==m.q;m.draft=draft;
    if(!typed&&draft.condition===m.condition&&draft.currency===m.currency)return;
    Object.assign(m,{q:draft.q.trim(),condition:draft.condition,currency:draft.currency,page:1});
    clearTimeout(timer);timer=setTimeout(()=>load(),typed?250:0);
  },submit(form){clearTimeout(timer);const data=new FormData(form),m=s.market;Object.assign(m,{q:String(data.get('q')||'').trim(),condition:String(data.get('condition')||''),currency:String(data.get('currency')??m.currency??''),page:1,draft:null});return load({focusResult:true});},actions:{
    'benchmark-reset'(){Object.assign(s.market,{q:'',condition:'',currency:'',page:1,draft:null});return load({focusResult:true});},
    'benchmark-retry'(){return load({focusResult:true});},
    'benchmark-next'(){if(!s.market.loading&&s.market.has_next){s.market.page++;return load({focusResult:true});}},
    'benchmark-prev'(){if(!s.market.loading&&s.market.page>1){s.market.page--;return load({focusResult:true});}},
  }};
}
