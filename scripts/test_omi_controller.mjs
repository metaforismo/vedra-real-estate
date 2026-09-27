import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createOmiController} from '../frontend/src/omi-controller.js';
function form(){
 const nodes=new Map();const node=()=>({innerHTML:'',textContent:'',hidden:false,disabled:false});
 const input=value=>({value,disabled:false,selectedOptions:[{textContent:'Comune QA'}],set innerHTML(v){this.html=v;this.value='';},get innerHTML(){return this.html;}});
 return {isConnected:true,elements:{province:input('MI'),city_code:input('F205'),zone:input('B1'),period:input('20252'),usage:input('R')},querySelector(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},setAttribute(k,v){this[k]=v;}};
}
test('old quote success cannot replace a new selection or unlock its pending request',async()=>{
 const f=form(),pending=[];const c=createOmiController({request:()=>new Promise((resolve,reject)=>pending.push({resolve,reject})),renderQuotes:r=>r.text});
 const old=c.submit(f);f.elements.zone.value='D1';await c.change(f,'zone');const current=c.submit(f);
 pending[0].resolve({text:'OLD B1'});await old;assert.equal(f.querySelector('#omi-result').innerHTML,'');assert.equal(f.querySelector('#omi-submit').disabled,true);
 pending[1].resolve({text:'NEW D1'});await current;assert.match(f.querySelector('#omi-result').innerHTML,/NEW D1/);assert.equal(f.querySelector('#omi-submit').disabled,false);
});
test('late errors are discarded and current failures are retryable',async()=>{
 const f=form(),pending=[];const c=createOmiController({request:()=>new Promise((resolve,reject)=>pending.push({resolve,reject})),renderQuotes:r=>r.text});
 const old=c.submit(f);f.elements.usage.value='C';await c.change(f,'usage');pending[0].reject(Error('Old failure'));await old;assert.equal(f.querySelector('#modal-error').textContent,'');
 const active=c.submit(f);pending[1].reject(Error('Current failure'));await active;assert.equal(f.querySelector('#modal-error').textContent,'Current failure');
 const retry=c.retry(f);pending[2].resolve({text:'Recovered'});await retry;assert.match(f.querySelector('#omi-result').innerHTML,/Recovered/);
});
test('late metadata and closed dialogs cannot receive results',async()=>{
 const f=form(),pending=[];const c=createOmiController({request:()=>new Promise(resolve=>pending.push(resolve)),renderQuotes:r=>r.text});
 const first=c.change(f,'province');f.elements.province.value='RM';const second=c.change(f,'province');pending[0]([{code:'F205',name:'Old city'}]);await first;assert.doesNotMatch(f.elements.city_code.innerHTML,/Old city/);
 pending[1]([{code:'H501',name:'Current city'}]);await second;assert.match(f.elements.city_code.innerHTML,/Current city/);
 f.elements.zone.value='B1';f.elements.period.value='20252';const quote=c.submit(f);f.isConnected=false;pending[2]({text:'Closed'});await quote;assert.equal(f.querySelector('#omi-result').innerHTML,'');
});
