import assert from 'node:assert/strict';
import {test} from 'node:test';
import {setTimeout as wait} from 'node:timers/promises';
import {createCatalogController} from '../frontend/src/catalog-controller.js';
import {pagination} from '../frontend/src/catalog-ui.js';
import {loginView} from '../frontend/src/views.js';

function harness(t){
  const state={user:{role:'admin'},page:'properties',filters:{},selected:new Set()};
  const pending=[];
  t.mock.method(globalThis,'fetch',(url,options)=>new Promise(resolve=>pending.push({url,options,resolve})));
  const controller=createCatalogController({s:state,render(){},updateResults(){},openModal(){},closeModal(){},refresh:async()=>{}});
  state.catalog.facets={cities:[],currencies:[]};
  return {state,controller,pending};
}
const response=data=>({ok:true,json:async()=>data});
const page=id=>({items:[{id}],total:1,page:1,page_size:50,pages:1,has_next:false});

test('an older response cannot replace newer search results even when abort is ignored',async t=>{
  const {state,controller,pending}=harness(t);
  state.filters.q='old';const old=controller.load();
  state.filters.q='new';const fresh=controller.load();
  assert.equal(pending[0].options.signal.aborted,true);
  pending[1].resolve(response(page('new')));await fresh;
  pending[0].resolve(response(page('old')));await old;
  assert.equal(state.catalog.items[0].id,'new');
  assert.equal(state.catalog.loading,false);
});

test('navigation cancellation discards in-flight results',async t=>{
  const {state,controller,pending}=harness(t);
  const run=controller.load();state.page='overview';controller.cancel();
  pending[0].resolve(response(page('must-not-appear')));await run;
  assert.equal(state.catalog.items.length,0);
  assert.equal(state.catalog.loading,false);
  assert.equal(pending[0].options.signal.aborted,true);
});

test('a stale failure does not overwrite the last successful query',async t=>{
  const {state,controller,pending}=harness(t);
  const old=controller.load();const fresh=controller.load();
  pending[1].resolve(response(page('current')));await fresh;
  pending[0].resolve({ok:false,status:503,json:async()=>({detail:'Old failure'})});await old;
  assert.equal(state.catalog.error,null);
  assert.equal(state.catalog.items[0].id,'current');
});

test('validation failure clears misleading rows and is recoverable',async t=>{
  const {state,controller,pending}=harness(t);
  state.catalog.items=[{id:'previous-query'}];
  const run=controller.load();
  pending[0].resolve({ok:false,status:422,json:async()=>({detail:[{loc:['query','currency'],msg:'Choose currency'}]})});
  await run;
  assert.equal(state.catalog.items.length,0);
  assert.match(state.catalog.error,/Choose currency/);
  const retry=controller.actions['catalog-retry']();
  pending[1].resolve(response(page('valid')));await retry;
  assert.equal(state.catalog.error,null);
});

test('rapid typing creates a single request and preserves zero-valued filters',async t=>{
  const {state,controller,pending}=harness(t);
  state.catalog.page=9;state.filters.min_surface=0;
  state.filters.q='old';await controller.load({reset:true,delay:15});
  state.filters.q='final';await controller.load({reset:true,delay:15});
  await wait(40);
  assert.equal(pending.length,1);
  assert.match(pending[0].url,/q=final/);
  assert.match(pending[0].url,/min_surface=0/);
  assert.match(pending[0].url,/page=1/);
  pending[0].resolve(response(page('final')));await wait(0);
  assert.equal(state.catalog.items[0].id,'final');
});

test('page selections are capped at 100 and clearing does not change filters',t=>{
  const {state,controller}=harness(t);
  state.filters.city='Milano';
  state.catalog.items=Array.from({length:120},(_,i)=>({id:String(i)}));
  controller.actions['select-page']();
  assert.equal(state.selected.size,100);
  controller.actions['select-page']();
  assert.equal(state.selected.size,100);
  controller.actions['clear-selection']();
  assert.equal(state.selected.size,0);
  assert.equal(state.filters.city,'Milano');
});

test('login renders without authenticated workspace state or a DOM',()=>{
  const html=loginView();
  assert.match(html,/<h2>Accedi<\/h2>/);
  assert.match(html,/id="login-form"/);
  assert.match(html,/Vedra · Workspace privato/);
});


test('failed or pending searches cannot present previous result counts or pagination',()=>{
  const catalog={page:2,page_size:25,pages:4,total:100,has_next:true};
  for(const extra of [{error:'offline'},{loading:true}]){
    const html=pagination({catalog:{...catalog,...extra}});
    assert.doesNotMatch(html,/di 100 annunci|2 \/ 4/);
    assert.match(html,/data-action="catalog-prev" disabled/);
    assert.match(html,/data-action="catalog-next" disabled/);
  }
  assert.match(pagination({catalog}),/26–50 di 100 annunci/);
});

test('selection while a new filter is pending cannot select stale rows',t=>{
  const {state,controller}=harness(t);
  state.catalog.items=[{id:'old-filter'}];state.catalog.loading=true;
  controller.actions['select-page']();assert.equal(state.selected.size,0);
  state.catalog.loading=false;state.catalog.error='offline';
  controller.actions['select-page']();assert.equal(state.selected.size,0);
});
