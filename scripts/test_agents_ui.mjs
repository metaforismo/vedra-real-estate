import assert from 'node:assert/strict';
import {test} from 'node:test';
import {agentDirectory,readinessContent,frequency,budget,amountValue} from '../frontend/src/agents-ui.js';
import {monogram} from '../frontend/src/sources-ui.js';

const agent=(over={})=>({id:'a1',name:'Milano <Value Add>',city:'Milano',runtime:'scout',active:true,interval_minutes:360,qualified:3,total:9,source_ids:['s1'],
  criteria:{max_price:1500000,min_price:500000,min_surface:100,strategies:['value_add'],property_types:['office'],opportunity_only:true,contact_policy:'prefer_direct',include_auctions:true,location_query:'Porta Romana'},
  last_run:{id:'r1',status:'completed',finished_at:new Date(Date.now()-3600e3).toISOString()},...over});
const state=role=>({user:{role},data:{sources:[{id:'s1',name:'RE/MAX',kind:'html',domain:'www.remax.it'}]}});

test('the page has one filled primary; each card runs, configures and keeps the rest in a menu',()=>{
  const html=agentDirectory(state('analyst'),[agent()]);
  assert.equal(html.split('btn primary').length-1,1); // page heading only: Esegui ora is outlined
  assert.match(html,/class="btn" data-action="run-agent"[^>]*><svg[^]*?<\/svg>Esegui ora/);
  assert.match(html,/aria-label="Configura Milano &lt;Value Add&gt;"/);
  for(const name of ['duplicate-agent','toggle-agent','agent-readiness'])assert.match(html,new RegExp(`class="menu-item" data-action="${name}"`));
  assert.match(html,/500 mila € – 1,5 mln €/);assert.match(html,/Da 100 m²/);assert.match(html,/Porta Romana/);
  assert.match(html,/<strong>Scout \(siti web\)<\/strong> · RE\/MAX/);assert.doesNotMatch(html,/monogram/);assert.match(html,/data-action="run-detail" data-id="r1"/);
});
test('viewers see criteria and readiness but no mutating actions',()=>{
  const html=agentDirectory(state('viewer'),[agent()]);
  assert.doesNotMatch(html,/run-agent|toggle-agent|duplicate-agent|new-agent/);
  assert.match(html,/Vedi criteri/);assert.match(html,/agent-readiness/);
});
test('an unrun search shows a dash, not zero results; online searches come first',()=>{
  const html=agentDirectory(state('analyst'),[agent({id:'local',name:'Archivio',runtime:'local',last_run:null,criteria:{...agent().criteria,online_discovery:false}}),agent()]);
  assert.ok(html.indexOf('Milano &lt;Value Add&gt;')<html.indexOf('Archivio'));
  assert.match(html,/<strong>—<\/strong><span>nei criteri<\/span><small>Nessuna esecuzione/);
  assert.match(html,/Mai eseguita/);
});
test('status lives in the badge only: paused and queued are not repeated in the schedule line',()=>{
  const html=agentDirectory(state('analyst'),[agent({active:false})]);
  assert.match(html,/Ogni 6 ore · /);assert.doesNotMatch(html,/in pausa/);assert.match(html,/In pausa/);assert.match(html,/id="card-menu-a1"/);
  const queued=agentDirectory(state('analyst'),[agent({next_run:new Date(Date.now()-60e3).toISOString()})]);
  assert.match(queued,/>In coda</);assert.doesNotMatch(queued,/in coda|prossima/);
  assert.match(agentDirectory(state('analyst'),[agent({last_run:{id:'r',status:'failed',created_at:new Date().toISOString()}})]),/Ultima ricerca non riuscita/);
});
test('budgets read as spoken and parse back from grouped digits',()=>{
  assert.equal(budget({max_price:3e6}),'Fino a 3 mln €');assert.equal(budget({min_price:1e6,max_price:3e6}),'1–3 mln €');
  assert.equal(budget({min_price:250000,max_price:900000}),'250–900 mila €');
  for(const text of ['1.500.000','1 500 000','1500000','1500000,4'])assert.equal(amountValue(text),1500000);
  assert.ok(Number.isNaN(amountValue('')));assert.ok(Number.isNaN(amountValue('1,5 mln')));
});
test('frequencies read in hours and days',()=>{
  assert.equal(frequency(0),'Avvio manuale');assert.equal(frequency(60),'Ogni ora');assert.equal(frequency(360),'Ogni 6 ore');
  assert.equal(frequency(1440),'Ogni giorno');assert.equal(frequency(10080),'Ogni settimana');assert.equal(frequency(15),'Ogni 15 min');
});
test('readiness ends in a verdict and keeps source diagnosis escaped',()=>{
  const data={agent_id:'a1',can_enqueue:false,active_run:null,notice:'Controllo locale.',checks:[{ok:false,blocking:true,message:'Runtime <assente>'},{ok:false,blocking:false,message:'Worker'}],
    sources:[{name:'RE/MAX',blockers:['Dominio non autorizzato'],warnings:[]}]};
  const html=readinessContent(data,true);
  assert.match(html,/1 problema blocca l’esecuzione/);assert.match(html,/Runtime &lt;assente&gt;/);
  assert.match(html,/class="preflight-source"/);assert.doesNotMatch(html,/run-agent/);
  assert.match(readinessContent({...data,can_enqueue:true,checks:[]},true),/Pronta per l’esecuzione[^]*run-agent/);
});
test('monograms come from words, not domains',()=>{
  assert.match(monogram({name:'RE/MAX'}),/>RM</);assert.match(monogram({name:'Immobiliare.it'}),/>IM</);
  assert.match(monogram({name:'Engel & Völkers'}),/>EV</);assert.match(monogram({name:'Import',kind:'import'}),/monogram +file/);
});
