import assert from 'node:assert/strict';
import {test} from 'node:test';
import {comparablesContent} from '../frontend/src/comparables-ui.js';
const p={id:'one',city:'Milano',zone:'Z1',property_type:'office',condition:'good',currency:'EUR',price:100000,price_sqm:1000,surface:100,area_basis:'commercial'};
const empty={items:[],count:0,median_sqm:null,source_count:0,reason:'Dati mancanti: zona',method:'Metodo'};
test('missing evidence does not become a zero median or a discount',()=>{
  const html=comparablesContent(p,empty);
  assert.match(html,/Non disponibile/);assert.match(html,/Dati mancanti: zona/);
  assert.doesNotMatch(html,/class="comp-comparison"|€ 0/);
  assert.match(html,/m² commerciali/);
  assert.match(comparablesContent({...p,price_sqm:1000.25},empty),/1000,25/);
});
test('the displayed row cap is distinguished from the statistical sample',()=>{
  const html=comparablesContent(p,{...empty,count:18,source_count:3,median_sqm:2000,asking_delta_pct:-50,sample_limited:true,items:[{id:'b',title:'Casa',price:200000,price_sqm:2000,surface:100,source:'Fonte',url:'https://example.test/casa'}]});
  assert.match(html,/18 annunci · 3 fonti/);assert.match(html,/1 di 18 asset/);
  assert.match(html,/50% sotto la mediana/);assert.match(html,/1.000 annunci/);
  assert.doesNotMatch(html,/margine del 50/);
});
test('zero and positive differences use the correct comparison direction',()=>{
  assert.match(comparablesContent(p,{...empty,median_sqm:1000,asking_delta_pct:0}),/in linea con la mediana/);
  assert.match(comparablesContent(p,{...empty,median_sqm:900,asking_delta_pct:11.1}),/11,1% sopra la mediana/);
});
test('unavailable external URLs stay unlinked and titles and sources are escaped',()=>{
  const html=comparablesContent(p,{...empty,items:[{id:'two',title:'<titolo>',source:'<fonte>',url:'import://private/id',price:100000,price_sqm:1000,surface:100}]});
  assert.doesNotMatch(html,/<titolo>|<fonte>|href="import:/);
  assert.match(html,/&lt;titolo&gt;/);assert.match(html,/&lt;fonte&gt;/);
  assert.match(html,/\/api\/properties\/one\/memo.xlsx/);
});
