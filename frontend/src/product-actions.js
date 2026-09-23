import {omiForm,quoteTable} from './market-ui.js';
import {api,toast} from './api.js';
import {modalFrame} from './dialogs.js';
import {workForm,scenarioForm,scenarioResult,comparablesContent} from './product-ui.js';
import {e,euro,stamp,amount,num} from './utils.js';
import {mapGroup} from './map.js';

export function productActions(ctx){
  const {s,refresh,render,openModal,closeModal,loadModal,showProperty,showRun}=ctx;
  let scenarioRows=[];
  async function showScenarios(id){
    await loadModal('Scenario economico',()=>Promise.all([api(`/properties/${encodeURIComponent(id)}`),api(`/properties/${encodeURIComponent(id)}/scenarios`)]),
      ([p,rows])=>modalFrame('Scenario economico',p.title,scenarioForm(s,p,rows),'wide-modal'),'scenario',
      ([p,rows])=>{s.currentProperty=p;scenarioRows=rows;});
  }
  let omiSequence=0;
  document.addEventListener('change',async event=>{
    if(!['omi-province','omi-city'].includes(event.target.id))return;
    const form=event.target.closest('form'),sequence=++omiSequence;
    const city=form.elements.city_code,zone=form.elements.zone;
    const result=form.querySelector('#omi-result'),status=form.querySelector('#omi-status');
    form.querySelector('#modal-error').textContent='';result.innerHTML='';
    form.querySelector('#omi-submit').disabled=true;zone.disabled=true;zone.innerHTML='<option value="">Seleziona zona</option>';
    status.textContent='Consultazione della fonte ufficiale…';
    try{
      if(event.target.id==='omi-province'){
        city.disabled=true;city.innerHTML='<option value="">Seleziona comune</option>';
        if(!event.target.value){status.textContent='';return;}
        const rows=await api('/omi/cities?province='+encodeURIComponent(event.target.value));
        if(sequence!==omiSequence||!form.isConnected)return;
        city.innerHTML='<option value="">Seleziona comune</option>'+rows.map(x=>`<option value="${e(x.code)}">${e(x.name)}</option>`).join('');city.disabled=false;
      }else{
        if(!city.value){status.textContent='';return;}
        const res=await api('/omi/zones?city_code='+encodeURIComponent(city.value));
        if(sequence!==omiSequence||!form.isConnected)return;
        zone.innerHTML=res.zones.map(x=>`<option value="${e(x.code)}">${e(x.name)}</option>`).join('');zone.disabled=false;
        form.elements.period.value=res.period;form.querySelector('#omi-submit').disabled=!res.zones.length;
      }
      status.textContent='Fonte caricata.';
    }catch(error){if(sequence===omiSequence&&form.isConnected){status.textContent='';form.querySelector('#modal-error').textContent=error.message;}}
  });
  const actions={
    async 'omi-open'(){await loadModal('Quotazioni OMI',()=>api('/omi/provinces'),rows=>modalFrame('Quotazioni OMI · Italia','Agenzia delle Entrate',omiForm(rows),'wide-modal'),'omi');},
    async 'deal-work'(el){await loadModal('Revisione',()=>Promise.all([api(`/properties/${encodeURIComponent(el.dataset.id)}`),api(`/properties/${encodeURIComponent(el.dataset.id)}/work`)]),([p,w])=>modalFrame('Revisione',p.title,workForm(s,p,w)),'work');},
    async scenarios(el){await showScenarios(el.dataset.id);},
    async comparables(el){await loadModal('Comparabili',()=>Promise.all([api(`/properties/${encodeURIComponent(el.dataset.id)}`),api(`/properties/${encodeURIComponent(el.dataset.id)}/comparables`)]),([p,res])=>modalFrame('Comparabili','Prezzi richiesti, non transazioni.',comparablesContent(p,res)),'comparables');},
    'load-scenario'(el){const row=scenarioRows.find(x=>x.id===el.dataset.id),form=document.getElementById('scenario-form');if(!row||!form)return;form.elements.name.value=row.name;for(const [k,v] of Object.entries(row.inputs))if(form.elements[k])form.elements[k].value=v;document.getElementById('scenario-result').innerHTML=scenarioResult(row.result);},
    async 'delete-scenario'(el){if(!confirm('Eliminare questo scenario salvato?'))return;await api(`/scenarios/${encodeURIComponent(el.dataset.id)}`,{method:'DELETE'});if(el.isConnected)await showScenarios(s.currentProperty.id);},
    async 'notification-open'(el){const n=s.notifications.find(x=>x.id===el.dataset.id);if(!n)return;await api(`/notifications/${encodeURIComponent(n.id)}/read`,{method:'POST'});await refresh(true);if(n.property_id)await showProperty(n.property_id);else if(n.run_id)await showRun(n.run_id);},
    async 'notification-read'(el){await api(`/notifications/${encodeURIComponent(el.dataset.id)}/read`,{method:'POST'});await refresh(true);},
    async 'read-all'(){await api('/notifications/read-all',{method:'POST'});await refresh(true);},
    'inbox-filter'(el){s.inboxUnread=el.dataset.unread==='true';render();},
    'save-view'(){openModal(modalFrame('Salva questa vista','Filtri e ordinamento personali.',`<form id="save-view-form" class="modal-form"><label>Nome<input name="name" required minlength="1" maxlength="60" placeholder="Milano · uffici da valutare"></label><div id="modal-error" class="form-error" role="alert"></div><button class="btn primary" type="submit">Salva vista</button></form>`),'save-view');},
    async 'delete-view'(el){await api(`/saved-views/${encodeURIComponent(el.dataset.id)}`,{method:'DELETE'});await refresh(true);},
    async 'duplicate-review'(el){await api('/duplicates/review',{method:'POST',body:{a:el.dataset.a,b:el.dataset.b,decision:el.dataset.decision}});await refresh(true);toast('Decisione salvata. Le fonti rimangono separate.');},
    async readiness(){const node=document.getElementById('readiness-result');const res=await api('/readiness');if(node?.isConnected)node.innerHTML=`<pre class="json-result">${e(JSON.stringify(res,null,2))}</pre>`;},
    async audit(){await loadModal('Registro modifiche',()=>api('/audit'),rows=>modalFrame('Registro modifiche','',`<div class="modal-body"><div class="audit-list">${rows.map(row=>`<article><strong>${e(row.action)}</strong><span>${e(row.actor||row.user_id||'Sistema')}</span><time>${stamp(row.created_at,true)}</time><small>${e(row.target_id||'')}</small></article>`).join('')||'<p>Nessuna modifica registrata.</p>'}</div></div>`),'audit');},
    password(){openModal(modalFrame('Cambia password','Le altre sessioni vengono revocate.',`<form id="password-form" class="modal-form"><label>Password attuale<input type="password" name="current_password" autocomplete="current-password" required></label><label>Nuova password<input type="password" name="new_password" autocomplete="new-password" minlength="12" maxlength="128" required></label><div id="modal-error" class="form-error" role="alert"></div><button type="submit" class="btn primary">Aggiorna password</button></form>`),'password');},
    'map-mode'(el){s.mapMode=el.dataset.mode;render();},
    'map-group'(el){const rows=mapGroup(s.data.properties,s.mapMode||'italy',el.dataset.index);if(rows.length===1)return showProperty(rows[0].id);openModal(modalFrame('Immobili in questa area',`${rows.length} posizioni dichiarate.`, `<div class="modal-body comparable-list">${rows.map(p=>`<button data-action="property" data-id="${e(p.id)}"><span><strong>${e(p.title)}</strong><small>${e(p.city)} · ${num(p.surface)} m²</small></span><strong>${amount(p.price,p.currency)}</strong></button>`).join('')}</div>`),'map');},
  };
  async function submit(form,event){
    const ids=['work-form','scenario-form','save-view-form','password-form','omi-form'];if(!ids.includes(form.id))return false;
    event.preventDefault();const button=event.submitter||form.querySelector('[type=submit]');if(button?.disabled)return true;
    const fd=new FormData(form),v=k=>String(fd.get(k)||'');
    if(button)button.disabled=true;
    try{
      if(form.id==='omi-form'){
        form.querySelector('#modal-error').textContent='';form.querySelector('#omi-result').innerHTML='';
        const sequence=++omiSequence;
        const res=await api('/omi/quotes?'+new URLSearchParams({city_code:v('city_code'),zone:v('zone'),period:v('period'),usage:v('usage')}));
        if(sequence===omiSequence&&form.isConnected)form.querySelector('#omi-result').innerHTML=quoteTable(res);
      }else if(form.id==='work-form'){
        const checklist={};for(const key of ['source_checked','area_checked','occupancy_checked','planning_checked','costs_checked'])checklist[key]=fd.has(key);
        await api(`/properties/${encodeURIComponent(form.dataset.id)}/work`,{method:'PUT',body:{stage:v('stage'),owner_id:v('owner_id')||null,due_date:v('due_date')||null,version:Number(form.dataset.version),checklist}});
        if(form.isConnected)closeModal();await refresh(true);toast('Revisione salvata.');
      }else if(form.id==='scenario-form'){
        const inputs={};for(const key of ['purchase','sale','works','acquisition_costs','contingency_pct','selling_pct','holding_monthly','months'])inputs[key]=Number(v(key));
        const body={name:v('name'),inputs};
        if(event.submitter?.name==='save'){await api(`/properties/${encodeURIComponent(form.dataset.id)}/scenarios`,{method:'POST',body});if(form.isConnected)await showScenarios(form.dataset.id);toast('Scenario salvato.');}
        else{const result=await api('/scenarios/calculate',{method:'POST',body});if(form.isConnected)form.querySelector('#scenario-result').innerHTML=scenarioResult(result);}
      }else if(form.id==='save-view-form'){
        await api('/saved-views',{method:'POST',body:{name:v('name'),filters:s.filters}});if(form.isConnected)closeModal();await refresh(true);
      }else if(form.id==='password-form'){
        await api('/auth/password',{method:'POST',body:{current_password:v('current_password'),new_password:v('new_password')}});if(form.isConnected)closeModal();toast('Password aggiornata; altre sessioni revocate.');
      }
    }catch(err){if(form.isConnected){const node=form.querySelector('#modal-error');if(node)node.textContent=err.message;else toast(err.message,true);}}
    finally{if(button?.isConnected)button.disabled=false;}
    return true;
  }
  return {actions,submit,handles:id=>['work-form','scenario-form','save-view-form','password-form','omi-form'].includes(id)};
}
