import assert from 'node:assert/strict';
import {test} from 'node:test';
import {scenarioForm,scenarioResult,savedScenarios} from '../frontend/src/scenario-ui.js';

const state={user:{id:'me',role:'analyst'}};
const property={id:'p',city:'Milano',price:100000,currency:'EUR',surface:90};
test('a foreign or unknown currency cannot silently prefill euro purchase assumptions',()=>{
  for(const currency of ['USD','XXX',null]){
    const html=scenarioForm(state,{...property,currency,surface:null},[]);
    assert.match(html,/name="purchase"[^>]*value=""/);
    assert.match(html,/Superficie non indicata/);
  }
  // Euro amounts are formatted as everywhere else in the sheet (and parsed back on submit).
  assert.match(scenarioForm(state,property,[]),/name="purchase"[^>]*value="100.000"/);
});
test('viewer can calculate but not save or delete; analysts cannot delete another author snapshot',()=>{
  const rows=[{id:'s',name:'Base',author:'Ada',author_id:'someone',result:{profit:0}}];
  const viewer={user:{id:'me',role:'viewer'}};
  assert.match(scenarioForm(viewer,property,rows),/>Calcola</);
  assert.doesNotMatch(scenarioForm(viewer,property,rows),/name="save"|data-action="delete-scenario"/);
  assert.doesNotMatch(savedScenarios(state,rows),/data-action="delete-scenario"/);
  rows[0].author_id='me';assert.match(savedScenarios(state,rows),/data-action="delete-scenario"/);
});
test('purchase ceilings keep cents and non-positive ceilings do not suggest an offer',()=>{
  const result={profit:1234.56,roi_pct:1.23,max_purchase:100000.99,target_roi_pct:20,target_met:false,invested:100000,breakeven_sale:123456.78,sensitivity:[]};
  assert.match(scenarioResult(result),/100\.000,99/);
  assert.match(scenarioResult(result),/Acquisto da rinegoziare/);
  assert.match(scenarioResult({...result,max_purchase:0}),/Nessun prezzo positivo/);
  assert.match(scenarioResult({...result,max_purchase:-1}),/Rivedi le ipotesi/);
  assert.match(scenarioResult({...result,target_roi_pct:20.25}),/ROI obiettivo 20,25%/);
});
test('saved names and authors remain plain text in labels and action attributes',()=>{
  const html=savedScenarios(state,[{id:'s',name:'<b>"Example"</b>',author:'<img>',author_id:'me',result:{profit:-1}}]);
  assert.doesNotMatch(html,/<b>|<img>/);
  assert.match(html,/&lt;b&gt;&quot;Example&quot;/);
  assert.match(html,/danger-text/);
});
