import {test} from 'node:test';
import assert from 'node:assert/strict';
import {qualityView} from '../frontend/src/quality-ui.js';
import {catalogView,defaultFilters} from '../frontend/src/catalog-ui.js';
const make=()=>({selected:new Set(),user:{role:'admin'},data:{quality:{total:5,completeness:90,unbenchmarked:2,coverage:[{field:'price',missing:2,total:5,present:3,percent:60},{field:'surface',missing:0,total:5,present:5,percent:100}]},properties:[],duplicates:[],has_more:false},ops:{duplicate_reviews:[]}});
test('missing fields have explicit destinations and complete fields do not',()=>{
  const html=qualityView(make());assert.match(html,/data-field="price"/);assert.doesNotMatch(html,/data-field="surface"/);assert.match(html,/Vedi annunci senza prezzo/);assert.match(html,/Metodo e limiti/);
});
test('empty quality never presents zero percent as a measured result',()=>{
  const s=make();Object.assign(s.data.quality,{total:0,completeness:null});
  const html=qualityView(s);assert.match(html,/Archivio vuoto/);assert.doesNotMatch(html,/<meter|>0%</);
});
test('reviewed candidate pairs move out of the pending list and retain both sources',()=>{
  const s=make();s.data.properties=[{id:'a',title:'<Uno>',source_name:'Fonte A',price:100000,surface:100,currency:'EUR'},{id:'b',title:'Due',source_name:'Fonte B',price:110000,surface:100,currency:'EUR'}];
  s.data.duplicates=[{a:'b',b:'a'}];s.ops.duplicate_reviews=[{a:'a',b:'b',decision:'same_asset'}];
  assert.doesNotMatch(qualityView(s),/class="quality-pair"/);
  s.qualityTab='reviewed';const html=qualityView(s);assert.match(html,/Fonte A/);assert.match(html,/Fonte B/);assert.match(html,/&lt;Uno&gt;/);assert.match(html,/Stesso asset confermato/);
  s.user.role='viewer';assert.doesNotMatch(qualityView(s),/data-action="duplicate-review"/);
});
test('duplicate sample limits stay visible while coverage uses the full archive',()=>{
  const s=make();s.data.has_more=true;s.data.quality.total=2006;s.data.properties=Array.from({length:2},()=>({}));
  assert.match(qualityView(s),/Confronto limitato ai 2 annunci caricati su 2006/);
});
test('the catalog exposes the missing-field constraint outside collapsed filters',()=>{
  const s=make();s.filters={...defaultFilters(),missing_field:'price'};s.catalog={items:[],total:0,facets:{cities:[],currencies:[]}};s.data.agents=[];s.data.sources=[];
  const html=catalogView(s,'','');assert.match(html,/Dato mancante: Prezzo/);assert.match(html,/data-action="clear-missing-field"/);assert.match(html,/id="catalog-missing_field"/);
});
