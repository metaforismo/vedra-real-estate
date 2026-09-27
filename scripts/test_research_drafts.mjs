import test from 'node:test';
import assert from 'node:assert/strict';
import {researchSnapshot,applyResearchSnapshot,createResearchDrafts} from '../frontend/src/research-drafts.js';
const field=(name,value,type='text',more={})=>({name,value,type,tagName:'INPUT',disabled:false,focus(){},...more});
function form(id='',name='Ricerca salvata'){
  const fields=[field('name',name),field('custom_prompt',''),field('min_price','0','number'),field('source_ids','a','checkbox',{checked:true}),field('source_ids','b','checkbox',{checked:false}),field('runtime','local','select-one',{tagName:'SELECT',options:[{value:'local'},{value:'hermes'}]}),field('','Salva','submit')];
  const ui={status:{textContent:''},help:{textContent:''},restore:{hidden:true,disabled:false},discard:{hidden:true,disabled:false}};
  const bar={hidden:true,querySelector(selector){return selector==='[role="status"]'?ui.status:selector==='.research-draft-help'?ui.help:selector.includes('restore')?ui.restore:ui.discard;}};
  const fieldset={disabled:false},events={};
  return {elements:fields,dataset:{id},isConnected:true,ui,fieldset,events,bar,
    insertAdjacentHTML(){},addEventListener(name,fn){events[name]=fn;},setAttribute(){},
    dispatchEvent(event){events[event.type]?.(event);},
    querySelector(selector){if(selector==='fieldset')return fieldset;if(selector==='.research-draft-bar')return bar;return fields.find(f=>f.name==='name');},
    set(name,value){fields.find(f=>f.name===name).value=value;this.dispatchEvent(new Event('input'));},
    click(which){events.click({target:{closest:()=>({dataset:{researchDraft:which},disabled:false})}});},
  };
}
const user={id:'user-a',role:'analyst'};
test('closing and reopening restores exact research text, zeros and individual source choices',()=>{
  const drafts=createResearchDrafts(),first=form('agent');drafts.attach(first,user);
  first.set('custom_prompt','Solo cambio d’uso\nVisita il broker.');first.elements[4].checked=true;drafts.capture(first);
  first.isConnected=false;const next=form('agent');drafts.attach(next,user);
  assert.equal(next.elements[1].value,'Solo cambio d’uso\nVisita il broker.');assert.equal(next.elements[2].value,'0');assert.equal(next.elements[4].checked,true);
  assert.equal(next.ui.status.textContent,'Bozza ripristinata');assert.equal(drafts.hasDrafts(),true);
});
test('reverting edits to original values removes the draft; unrelated UI fields are ignored',()=>{
  const drafts=createResearchDrafts(),f=form();drafts.attach(f,user);f.set('name','Modificata');assert.ok(drafts.hasDrafts());f.set('name','Ricerca salvata');
  assert.equal(drafts.hasDrafts(),false);assert.equal(f.bar.hidden,true);assert.equal(Object.keys(researchSnapshot(f)).includes(''),false);
});
test('changed server configuration is not silently replaced and can keep the current version',()=>{
  const drafts=createResearchDrafts(),old=form('agent');drafts.attach(old,user);old.set('name','Mia bozza');old.isConnected=false;
  const next=form('agent','Nuova versione del team');drafts.attach(next,user);
  assert.equal(next.elements[0].value,'Nuova versione del team');assert.equal(next.fieldset.disabled,true);assert.equal(next.ui.restore.hidden,false);
  next.click('discard');assert.equal(next.elements[0].value,'Nuova versione del team');assert.equal(next.fieldset.disabled,false);assert.equal(drafts.hasDrafts(),false);
});
test('conflicting draft is restored only after an explicit choice',()=>{
  const drafts=createResearchDrafts(),old=form('agent');drafts.attach(old,user);old.set('name','Mia bozza');
  const next=form('agent','Versione del team');drafts.attach(next,user);next.click('restore');
  assert.equal(next.elements[0].value,'Mia bozza');assert.equal(next.fieldset.disabled,false);assert.ok(drafts.hasDrafts());
});
test('pending save locks fields; success clears draft and reset prevents cross-session recovery',()=>{
  const drafts=createResearchDrafts(),f=form('agent');drafts.attach(f,user);f.set('name','Nuova');drafts.busy(f,true);
  assert.equal(f.fieldset.disabled,true);assert.equal(f.ui.status.textContent,'Salvataggio…');assert.equal(f.ui.help.textContent,'');assert.equal(f.ui.discard.disabled,true);
  drafts.saved(f);drafts.busy(f,false);assert.equal(f.fieldset.disabled,false);assert.equal(drafts.hasDrafts(),false);
  f.set('name','Altra');drafts.reset();const reopened=form('agent');drafts.attach(reopened,user);assert.equal(reopened.elements[0].value,'Ricerca salvata');
});
test('drafts are isolated by user and agent; viewers never restore or create one',()=>{
  const drafts=createResearchDrafts(),f=form('agent');drafts.attach(f,user);f.set('name','Riservata');
  for(const [id,actor] of [['agent',{id:'user-b',role:'analyst'}],['other',user],['agent',{...user,role:'viewer'}]]){
    const next=form(id);drafts.attach(next,actor);assert.equal(next.elements[0].value,'Ricerca salvata');assert.equal(next.bar.hidden,true);
  }
});
test('unavailable source and runtime are not restored or enabled',()=>{
  const f=form(),values=researchSnapshot(f);values['source_ids:b']=true;values.runtime='removed';values['source_ids:removed']=true;
  f.elements[4].disabled=true;
  assert.equal(applyResearchSnapshot(f,values),3);assert.equal(f.elements[4].checked,false);assert.equal(f.elements[4].disabled,true);assert.equal(f.elements[5].value,'local');
});
test('retry and reopen keep one submission identity even after edits; success renews it',()=>{
  const drafts=createResearchDrafts(),f=form();drafts.attach(f,user);f.set('name','New research');
  const key=drafts.submission(f);assert.equal(drafts.submission(f),key);f.set('name','Edited');assert.equal(drafts.submission(f),key);
  const next=form();drafts.attach(next,user);assert.equal(drafts.submission(next),key);
  drafts.saved(next);assert.notEqual(drafts.submission(next),key);
});
test('a lost create response can move its draft to the saved research before a fresh read',()=>{
  const drafts=createResearchDrafts(),f=form();drafts.attach(f,user);f.set('name','Local after lost response');
  const old=drafts.submission(f);drafts.retarget(f,'saved-id');
  const next=form('saved-id','Actually committed');drafts.attach(next,user);
  assert.equal(next.fieldset.disabled,true);assert.notEqual(drafts.submission(next),old);
  next.click('restore');assert.equal(next.elements[0].value,'Local after lost response');
  const empty=form();drafts.attach(empty,user);assert.equal(empty.elements[0].value,'Ricerca salvata');
});
