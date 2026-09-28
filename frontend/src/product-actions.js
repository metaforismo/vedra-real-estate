import {createOmiController} from './omi-controller.js';
import {savedScenarios,scenarioFields,amountFields,scenarioPending,scenarioInputs} from './scenario-ui.js';
import {formatAmount} from './forms.js';
import {contactForm,syncContactForm} from './decision-ui.js';
import {omiForm,quoteTable} from './market-ui.js';
import {api,toast} from './api.js';
import {modalFrame,footer} from './dialogs.js';
import {workForm,scenarioForm,scenarioResult,comparablesContent} from './product-ui.js';
import {e,stamp,amount,num} from './utils.js';
import {mapGroup} from './map.js';

export function productActions(ctx){
  const {s,refresh,render,openModal,closeModal,loadModal,showProperty,showRun}=ctx;
  let scenarioRows=[];
  async function showScenarios(id){
    await loadModal('Scenario economico',()=>Promise.all([api(`/properties/${encodeURIComponent(id)}`),api(`/properties/${encodeURIComponent(id)}/scenarios`)]),
      ([p,rows])=>modalFrame('Scenario economico',p.title,scenarioForm(s,p,rows),'wide-modal scenario-modal'),'scenario',
      ([p,rows])=>{s.currentProperty=p;scenarioRows=rows;});
  }
  function showScenarioResult(form,result){
    const panel=form.closest('dialog').querySelector('#scenario-result');
    panel.innerHTML=scenarioResult(result);
  }
  function loadScenario(form,row){
    form.dataset.revision=String(Number(form.dataset.revision||0)+1);
    form.dataset.calculationRevision=String(Number(form.dataset.calculationRevision||0)+1);
    form.dataset.loadedId=row.id;form.dataset.dirty='false';
    form.elements.name.value=row.name;
    for(const [key] of scenarioFields){const value=(row.result.inputs||row.inputs)[key];form.elements[key].value=amountFields.has(key)?formatAmount(value):value;}
    form.querySelector('#scenario-state').textContent='Salvato';
    const save=form.elements.namedItem('save');if(save)save.textContent='Salva copia';
    form.querySelector('#modal-error').textContent='';
    showScenarioResult(form,row.result);
  }
  async function refreshScenarios(form){
    const rows=await api(`/properties/${encodeURIComponent(form.dataset.id)}/scenarios`);
    if(!form.isConnected)return;
    scenarioRows=rows;form.closest('dialog').querySelector('.saved-scenarios').innerHTML=savedScenarios(s,rows);
  }
  document.addEventListener('input',event=>{
    const contact=event.target.closest('#contact-form');
    if(contact){contact.querySelector('#modal-error').textContent='';return;}
    const form=event.target.closest('#scenario-form');if(!form)return;
    form.dataset.revision=String(Number(form.dataset.revision||0)+1);form.dataset.dirty='true';
    form.querySelector('#scenario-state').textContent='Modifiche non salvate';
    if(event.target.name==='name')return;
    form.dataset.calculationRevision=String(Number(form.dataset.calculationRevision||0)+1);
    const result=form.closest('dialog').querySelector('#scenario-result');
    result.innerHTML=scenarioPending('Ipotesi modificate: ricalcola.');
  });
  const omi=createOmiController({renderQuotes:quoteTable});
  document.addEventListener('change',async event=>{
    const contact=event.target.closest('#contact-form');
    if(contact){syncContactForm(contact);return;}
    const form=event.target.closest('#omi-form');if(form)await omi.change(form,event.target.name);
  });
  const actions={
    'omi-retry'(el){return omi.retry(el.closest('form'));},
    async 'contact-log'(el){await loadModal('Registra contatto',()=>api(`/properties/${encodeURIComponent(el.dataset.id)}`),p=>modalFrame('Registra contatto',p.title,contactForm(p),'contact-modal'),'contact');},
    async 'omi-open'(){await loadModal('Quotazioni OMI',()=>api('/omi/provinces'),rows=>modalFrame('Quotazioni OMI · Italia','Agenzia delle Entrate',omiForm(rows),'wide-modal omi-modal'),'omi');},
    async 'deal-work'(el){await loadModal('Revisione',()=>Promise.all([api(`/properties/${encodeURIComponent(el.dataset.id)}`),api(`/properties/${encodeURIComponent(el.dataset.id)}/work`)]),([p,w])=>modalFrame('Revisione',p.title,workForm(s,p,w)),'work');},
    async 'reload-work'(el){if(confirm('Caricare la versione del team? Le modifiche non salvate in questo modulo verranno sostituite.'))await actions['deal-work'](el);},
    async scenarios(el){await showScenarios(el.dataset.id);},
    async comparables(el){await loadModal('Comparabili',()=>Promise.all([api(`/properties/${encodeURIComponent(el.dataset.id)}`),api(`/properties/${encodeURIComponent(el.dataset.id)}/comparables`)]),([p,res])=>modalFrame('Comparabili',p.title,comparablesContent(p,res),'wide-modal comparable-modal'),'comparables');},
    'load-scenario'(el){
      const row=scenarioRows.find(x=>x.id===el.dataset.id),form=document.getElementById('scenario-form');
      if(!row||!form||form.dataset.busy==='true')return;
      if(form.dataset.dirty==='true'&&!confirm('Aprire lo scenario salvato? Le modifiche non salvate verranno sostituite.'))return;
      loadScenario(form,row);
    },
    async 'delete-scenario'(el){
      const form=document.getElementById('scenario-form');if(!form||form.dataset.busy==='true')return;
      if(!confirm('Eliminare questo scenario salvato?'))return;
      await api(`/scenarios/${encodeURIComponent(el.dataset.id)}`,{method:'DELETE'});
      if(!form.isConnected)return;
      if(form.dataset.loadedId===el.dataset.id){delete form.dataset.loadedId;form.dataset.dirty='true';form.querySelector('#scenario-state').textContent='Bozza';const save=form.elements.namedItem('save');if(save)save.textContent='Salva scenario';}
      await refreshScenarios(form);
    },
    'save-view'(){openModal(modalFrame('Salva questa vista','Filtri e ordinamento personali.',`<form id="save-view-form" class="modal-form"><label>Nome<input name="name" required minlength="1" maxlength="60" placeholder="Milano · uffici da valutare" data-missing="Dai un nome alla vista"></label><div id="modal-error" class="form-error" role="alert"></div>${footer('Salva vista')}</form>`),'save-view');},
    async 'delete-view'(el){await api(`/saved-views/${encodeURIComponent(el.dataset.id)}`,{method:'DELETE'});await refresh(true);},
    async 'duplicate-review'(el){
      if(s.duplicateBusy)return;
      const user=s.user;s.duplicateBusy=true;render();
      try{await api('/duplicates/review',{method:'POST',body:{a:el.dataset.a,b:el.dataset.b,decision:el.dataset.decision}});if(s.user!==user)return;await refresh(true);toast('Decisione salvata. Le fonti restano separate.');}
      finally{if(s.user===user){s.duplicateBusy=false;render();if(s.page==='quality')document.getElementById('quality-'+(s.qualityTab||'pending'))?.focus({preventScroll:true});}}
    },
    async readiness(){const node=document.getElementById('readiness-result');const res=await api('/readiness');if(node?.isConnected)node.innerHTML=`<pre class="json-result">${e(JSON.stringify(res,null,2))}</pre>`;},
    async audit(){await loadModal('Registro modifiche',()=>api('/audit'),rows=>modalFrame('Registro modifiche','',`<div class="modal-body"><div class="audit-list">${rows.map(row=>`<article><strong>${e(row.action)}</strong><span>${e(row.actor||row.user_id||'Sistema')}</span><time>${stamp(row.created_at,true)}</time><small>${e(row.target_id||'')}</small></article>`).join('')||'<p>Nessuna modifica registrata.</p>'}</div></div>`),'audit');},
    password(){openModal(modalFrame('Cambia password','Le altre sessioni vengono revocate.',`<form id="password-form" class="modal-form"><label>Password attuale<input type="password" name="current_password" autocomplete="current-password" required data-missing="Inserisci la password attuale"></label><label>Nuova password<input type="password" name="new_password" autocomplete="new-password" minlength="12" maxlength="128" required data-missing="Scegli una nuova password di almeno 12 caratteri"></label><div id="modal-error" class="form-error" role="alert"></div>${footer('Aggiorna password')}</form>`),'password');},
    'map-mode'(el){s.mapMode=el.dataset.mode;render();},
    'map-group'(el){const rows=mapGroup(s.data.properties,s.mapMode||'italy',el.dataset.index);if(rows.length===1)return showProperty(rows[0].id);openModal(modalFrame('Immobili in questa area',`${rows.length} posizioni dichiarate.`, `<div class="modal-body comparable-list">${rows.map(p=>`<button data-action="property" data-id="${e(p.id)}"><span><strong>${e(p.title)}</strong><small>${e(p.city)} · ${num(p.surface)} m²</small></span><strong>${amount(p.price,p.currency)}</strong></button>`).join('')}</div>`),'map');},
  };
  async function submit(form,event){
    const ids=['contact-form','work-form','scenario-form','save-view-form','password-form','omi-form'];if(!ids.includes(form.id))return false;
    event.preventDefault();if(form.id==='omi-form')return omi.submit(form);if(form.id==='scenario-form'&&form.dataset.busy==='true')return true;const button=event.submitter||form.querySelector('[type=submit]');if(button?.disabled)return true;
    const fd=new FormData(form),v=k=>String(fd.get(k)||'');
    if(button)button.disabled=true;
    const scenarioButtons=form.id==='scenario-form'?[...form.elements].filter(x=>x.type==='submit'):[];
    if(scenarioButtons.length){form.dataset.busy='true';form.setAttribute('aria-busy','true');scenarioButtons.forEach(b=>b.disabled=true);}
    const workFields=form.id==='work-form'?form.querySelector('fieldset'):null;
    if(workFields){workFields.disabled=true;form.setAttribute('aria-busy','true');form.querySelector('#work-conflict').hidden=true;}
    const contactFields=form.id==='contact-form'?form.querySelector('fieldset'):null;
    if(contactFields){contactFields.disabled=true;form.setAttribute('aria-busy','true');form.querySelector('#modal-error').textContent='';}
    try{
      if(form.id==='contact-form'){
        await api(`/properties/${encodeURIComponent(form.dataset.id)}/contacts`,{method:'POST',body:{request_id:form.dataset.request,contact_name:v('contact_name'),outcome:v('outcome'),mandate_status:v('mandate_status'),note:v('note'),next_contact:v('next_contact')||null}});
        toast('Esito registrato.');
        if(form.isConnected)await showProperty(form.dataset.id);
        try{await refresh(true);}catch{toast('Esito registrato. Aggiorna la pagina per ricaricare il riepilogo.',true);}
      }else if(form.id==='work-form'){
        const checklist={};for(const key of ['source_checked','area_checked','occupancy_checked','planning_checked','costs_checked'])checklist[key]=fd.has(key);
        await api(`/properties/${encodeURIComponent(form.dataset.id)}/work`,{method:'PUT',body:{stage:v('stage'),owner_id:v('owner_id')||null,due_date:v('due_date')||null,version:Number(form.dataset.version),checklist}});
        if(form.isConnected)closeModal();await refresh(true);toast('Revisione salvata.');
      }else if(form.id==='scenario-form'){
        const inputs=scenarioInputs(v);
        const body={name:v('name'),inputs},revision=form.dataset.revision||'0',calculationRevision=form.dataset.calculationRevision||'0';
        form.querySelector('#modal-error').textContent='';
        if(event.submitter?.name==='save'){
          const saved=await api(`/properties/${encodeURIComponent(form.dataset.id)}/scenarios`,{method:'POST',body});
          if(form.isConnected){
            if(revision===(form.dataset.revision||'0'))loadScenario(form,{id:saved.id,name:body.name,result:saved.result,inputs});
            toast('Scenario salvato.');
            try{await refreshScenarios(form);}catch{if(form.isConnected)form.querySelector('#modal-error').textContent='Scenario salvato. Riapri la finestra per aggiornare l’elenco.';}
          }
        }else{
          const result=await api('/scenarios/calculate',{method:'POST',body});
          if(form.isConnected&&calculationRevision===(form.dataset.calculationRevision||'0')){
            showScenarioResult(form,result);
            const panel=form.closest('dialog').querySelector('#scenario-result');
            const heading=panel.querySelector('h3');heading?.focus({preventScroll:true});heading?.scrollIntoView({block:'nearest',behavior:'instant'});
          }
        }
      }else if(form.id==='save-view-form'){
        await api('/saved-views',{method:'POST',body:{name:v('name'),filters:s.filters}});if(form.isConnected)closeModal();await refresh(true);
      }else if(form.id==='password-form'){
        await api('/auth/password',{method:'POST',body:{current_password:v('current_password'),new_password:v('new_password')}});if(form.isConnected)closeModal();toast('Password aggiornata; altre sessioni revocate.');
      }
    }catch(err){if(form.isConnected){const node=form.querySelector('#modal-error');if(node){node.textContent=err.message;if(contactFields)node.scrollIntoView({block:'nearest',behavior:'instant'});}else toast(err.message,true);if(workFields&&err.status===409)form.querySelector('#work-conflict').hidden=false;}}
    finally{if(form.isConnected&&scenarioButtons.length){form.dataset.busy='false';form.setAttribute('aria-busy','false');scenarioButtons.forEach(b=>b.disabled=false);}if(button?.isConnected)button.disabled=false;if(workFields?.isConnected){workFields.disabled=s.user.role==='viewer';form.setAttribute('aria-busy','false');}if(contactFields?.isConnected){contactFields.disabled=false;form.setAttribute('aria-busy','false');syncContactForm(form);}}
    return true;
  }
  return {actions,submit,handles:id=>['contact-form','work-form','scenario-form','save-view-form','password-form','omi-form'].includes(id)};
}
