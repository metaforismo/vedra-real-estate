import {api} from './api.js';
import {createRequestGuard} from './request-guard.js';
export function createBenchmarkController({s,render,request=api,focus=()=>document.getElementById('benchmark-results')?.focus({preventScroll:true})}){
  const initial=()=>({items:[],q:'',condition:'',currency:'',page:1,loaded:false,loading:false,error:''});
  s.market=initial();
  const guard=createRequestGuard();let abort;
  function cancel(){guard.invalidate();abort?.abort();s.market.loading=false;}
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
  return {load,cancel,reset(){cancel();s.market=initial();},edit(form){const data=new FormData(form);s.market.draft=Object.fromEntries(['q','condition','currency'].map(k=>[k,String(data.get(k)||'')]));},submit(form){const data=new FormData(form);Object.assign(s.market,{q:String(data.get('q')||'').trim(),condition:String(data.get('condition')||''),currency:String(data.get('currency')||''),page:1,draft:null});return load({focusResult:true});},actions:{
    'benchmark-reset'(){Object.assign(s.market,{q:'',condition:'',currency:'',page:1,draft:null});return load({focusResult:true});},
    'benchmark-retry'(){return load({focusResult:true});},
    'benchmark-next'(){if(!s.market.loading&&s.market.has_next){s.market.page++;return load({focusResult:true});}},
    'benchmark-prev'(){if(!s.market.loading&&s.market.page>1){s.market.page--;return load({focusResult:true});}},
  }};
}
