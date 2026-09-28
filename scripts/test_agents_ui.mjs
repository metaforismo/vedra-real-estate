import assert from 'node:assert/strict';
import {test} from 'node:test';
import {agentDirectory,readinessContent,frequency} from '../frontend/src/agents-ui.js';
import {monogram} from '../frontend/src/sources-ui.js';

const agent=(over={})=>({id:'a1',name:'Milano <Value Add>',city:'Milano',runtime:'scout',active:true,interval_minutes:360,qualified:3,total:9,source_ids:['s1'],
  criteria:{max_price:1500000,min_price:500000,min_surface:100,strategies:['value_add'],property_types:['office'],opportunity_only:true,contact_policy:'prefer_direct',include_auctions:true,location_query:'Porta Romana'},
  last_run:{id:'r1',status:'completed',finished_at:new Date(Date.now()-3600e3).toISOString()},...over});
const state=role=>({user:{role},data:{sources:[{id:'s1',name:'RE/MAX',kind:'html',domain:'www.remax.it'}]}});

test('a search card has one primary action, Configura and a menu for the rest',()=>{
  const html=agentDirectory(state('analyst'),[agent()]);
  assert.equal(html.split('btn primary').length-1,2); // page heading + Esegui ora
  assert.match(html,/data-action="run-agent"[^>]*><svg[^]*?<\/svg>Esegui ora/);
  assert.match(html,/aria-label="Configura Milano &lt;Value Add&gt;"/);
  for(const name of ['duplicate-agent','toggle-agent','agent-readiness'])assert.match(html,new RegExp(`class="menu-item" data-action="${name}"`));
  assert.match(html,/€ 500k – € 1,5 M/);assert.match(html,/Da 100 m²/);assert.match(html,/Porta Romana/);
  assert.match(html,/Scout cerca online/);assert.match(html,/RE\/MAX/);assert.match(html,/data-action="run-detail" data-id="r1"/);
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
