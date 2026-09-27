import {api} from './api.js';
import {e} from './utils.js';
export function createOmiController({request=api,renderQuotes}){
  const states=new WeakMap();
  function state(form){if(!states.has(form))states.set(form,{metadata:0,quote:0,busy:false});return states.get(form);}
  function ready(form,s){form.querySelector('#omi-submit').disabled=s.busy||!form.elements.zone.value||!form.elements.period.value;}
  function clear(form,s){s.quote++;s.quoteAbort?.abort();s.busy=false;form.querySelector('#omi-result').innerHTML='';form.querySelector('#modal-error').textContent='';form.querySelector('#omi-retry').hidden=true;form.setAttribute('aria-busy','false');}
  function failure(form,s,error,retry){form.querySelector('#omi-status').textContent='';form.querySelector('#modal-error').textContent=error.message;s.retry=retry;form.querySelector('#omi-retry').hidden=false;}
  async function change(form,field){
    const s=state(form);clear(form,s);const status=form.querySelector('#omi-status');status.textContent='';
    if(!['province','city_code'].includes(field)){ready(form,s);return;}
    const sequence=++s.metadata;s.metaAbort?.abort();s.metaAbort=new AbortController();
    const city=form.elements.city_code,zone=form.elements.zone;
    zone.disabled=true;zone.innerHTML='<option value="">Seleziona prima il comune</option>';form.elements.period.value='';
    if(field==='province'){city.disabled=true;city.innerHTML='<option value="">Seleziona prima la provincia</option>';}
    ready(form,s);
    const value=form.elements[field].value;if(!value)return;
    status.textContent=field==='province'?'Caricamento comuni…':'Caricamento zone…';
    try{
      const data=await request(field==='province'?'/omi/cities?province='+encodeURIComponent(value):'/omi/zones?city_code='+encodeURIComponent(value),{signal:s.metaAbort.signal});
      if(!form.isConnected||s.metadata!==sequence)return;
      if(field==='province'){
        city.innerHTML='<option value="">Seleziona comune</option>'+data.map(x=>`<option value="${e(x.code)}">${e(x.name)}</option>`).join('');city.disabled=!data.length;
        status.textContent=data.length?'':'Nessun comune disponibile.';
      }else{
        zone.innerHTML='<option value="">Seleziona zona</option>'+data.zones.map(x=>`<option value="${e(x.code)}">${e(x.code)} · ${e(x.name)}</option>`).join('');zone.disabled=!data.zones.length;form.elements.period.value=data.period;
        status.textContent=data.zones.length?`Periodo disponibile: ${data.period.slice(0,4)} · ${data.period.slice(-1)}° semestre`:'Nessuna zona disponibile.';
      }
      ready(form,s);
    }catch(error){if(form.isConnected&&s.metadata===sequence){failure(form,s,error,()=>change(form,field));ready(form,s);}}
  }
  async function submit(form){
    const s=state(form);if(s.busy)return true;clear(form,s);const sequence=s.quote;
    if(!form.elements.zone.value||!form.elements.period.value){ready(form,s);return true;}
    s.busy=true;s.quoteAbort=new AbortController();ready(form,s);form.setAttribute('aria-busy','true');
    const values=Object.fromEntries(['city_code','zone','period','usage'].map(k=>[k,form.elements[k].value]));
    const selectedCity=form.elements.city_code.selectedOptions[0]?.textContent||values.city_code;
    form.querySelector('#omi-status').textContent='Consultazione quotazioni…';
    try{
      const result=await request('/omi/quotes?'+new URLSearchParams(values),{signal:s.quoteAbort.signal});
      if(!form.isConnected||s.quote!==sequence)return true;
      form.querySelector('#omi-result').innerHTML=`<h3>${e(selectedCity)} · ${e(values.zone)}</h3>`+renderQuotes(result);
      form.querySelector('#omi-status').textContent='';
    }catch(error){if(form.isConnected&&s.quote===sequence)failure(form,s,error,()=>submit(form));}
    finally{if(form.isConnected&&s.quote===sequence){s.busy=false;form.setAttribute('aria-busy','false');ready(form,s);}}
    return true;
  }
  return {change,submit,retry(form){return state(form).retry?.();}};
}
