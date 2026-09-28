import {test} from 'node:test';
import assert from 'node:assert/strict';
import {benchmarkView} from '../frontend/src/benchmark-ui.js';
import {createBenchmarkController} from '../frontend/src/benchmark-controller.js';
import {quoteTable} from '../frontend/src/market-ui.js';
const row={id:'b',city:'<Milano>',zone:'Centro',property_type:'office',condition:'good',currency:'USD',area_basis:'commercial',transaction_type:'sale',min_sqm:1200.55,max_sqm:1500,period:'2025-S2',source_label:'Fonte',source_url:'https://example.com/range'};
const state=()=>({user:{role:'admin'},page:'market',data:{quality:{total:3000,unbenchmarked:2000}},market:{items:[row],archive_total:1,total:1,page:1,pages:1,currencies:['USD'],conditions:['good']}});
test('benchmark inventory preserves original currency and safe source links',()=>{
 const html=benchmarkView(state());assert.match(html,/USD \/ m²/);assert.match(html,/1\.200,55/);assert.doesNotMatch(html,/€/);assert.match(html,/href="https:\/\/example.com\/range"/);assert.match(html,/&lt;Milano&gt;/);
 const s=state();s.market.items=[{...row,source_url:'javascript:alert(1)'}];assert.doesNotMatch(benchmarkView(s),/href="javascript/);
});
test('failed and pending inventory never shows stale benchmark rows',()=>{
 const s=state();s.market.loading=true;assert.doesNotMatch(benchmarkView(s),/benchmark-item/);
 s.market.loading=false;s.market.error='Connessione';assert.match(benchmarkView(s),/Riprova/);assert.doesNotMatch(benchmarkView(s),/benchmark-item/);
});
test('OMI never assigns a net area basis to an unknown row or creates unsafe source links',()=>{
 const html=quoteTable({source_label:'OMI',source_url:'javascript:bad',period:'2025-S2',zone_code:'B1',rows:[{type:'Casa',condition:'Normale',area_basis:'unknown',min_sqm:1000,max_sqm:2000}]});
 assert.match(html,/Non indicata/);assert.doesNotMatch(html,/href="javascript|>Netta</);
});
test('inventory ignores late responses after filtering or navigation',async()=>{
 const s=state(),pending=[];const c=createBenchmarkController({s,render(){},focus(){},request:()=>new Promise(resolve=>pending.push(resolve))});
 const a=c.load();s.market.q='Nuovo';const b=c.load();pending[1]({items:[{id:'new'}],total:1});await b;pending[0]({items:[{id:'old'}],total:1});await a;
 assert.equal(s.market.items[0].id,'new');const last=c.load();s.page='sources';c.cancel();pending[2]({items:[{id:'late'}]});await last;assert.notEqual(s.market.items[0]?.id,'late');
});
test('inventory errors can be retried without changing filters',async()=>{
 const s=state();let fail=true;const c=createBenchmarkController({s,render(){},focus(){},request:async()=>{if(fail)throw Error('Offline');return {items:[row],page:1,total:1};}});
 s.market.currency='USD';await c.load();assert.equal(s.market.error,'Offline');fail=false;await c.actions['benchmark-retry']();assert.equal(s.market.items.length,1);assert.equal(s.market.currency,'USD');
});

test('logout clears benchmark data and draft filters',()=>{
 const s=state();const c=createBenchmarkController({s,render(){}});Object.assign(s.market,{items:[row],q:'private search',draft:{q:'draft'}});c.reset();assert.equal(s.market.q,'');assert.deepEqual(s.market.items,[]);assert.equal(s.market.draft,undefined);
});
