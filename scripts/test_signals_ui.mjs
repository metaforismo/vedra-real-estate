import assert from 'node:assert/strict';
import {test} from 'node:test';
import {deltaText,ageText,marketCell,ageCell,signalLine,signalFacts,priceLadder} from '../frontend/src/signals-ui.js';

const ref=(key,label,median,delta,count=3)=>({key,label,median_sqm:median,q1_sqm:median&&median-100,q3_sqm:median&&median+100,count,source_count:2,delta_pct:delta,reason:median?'Prezzi richiesti osservati':'Servono almeno 3 asset confrontabili'});
const full={id:'a',currency:'EUR',discount:12,signals:{days_listed:120,listed_since:'2026-05-30',listed_basis:'published',
  reductions:{count:2,total_pct:-8.3,from_price:320000,last_at:'2026-09-01'},cadastral:'Categoria catastale A/10',change_of_use:'Possibile cambio d’uso <a>',
  contact:{name:'X',has_phone:true,has_email:false,route:'owner_declared',route_label:'Proprietario dichiarato'},
  market:{price_sqm:2900,currency:'EUR',same_condition_key:'to_renovate',refs:[ref('to_renovate','Da ristrutturare',3400,-14.7),ref('renovated','Ristrutturato',4800,-39.6),ref('new','Nuovo',null,null,1)],
    omi:{min_sqm:2800,max_sqm:4000,mid_sqm:3400,delta_pct:-14.7,period:'2026-S1',area_basis:'gross',stale:false}}}};

test('deltas read as words, not signs, and tiny gaps are "in linea"',()=>{
  assert.equal(deltaText(-14.7),'15% sotto');
  assert.equal(deltaText(8.2),'8% sopra');
  assert.equal(deltaText(.3),'in linea');
  assert.equal(deltaText(null),'');
});
test('listing age scales from days to years',()=>{
  assert.equal(ageText(0),'oggi');assert.equal(ageText(1),'1 giorno');assert.equal(ageText(45),'45 giorni');
  assert.equal(ageText(120),'4 mesi');assert.equal(ageText(400),'oltre 1 anno');assert.equal(ageText(null),null);
});
test('table comparison prefers like-for-like, then OMI, then benchmark, else says so',()=>{
  assert.match(marketCell(full),/15% sotto<\/span><small>vs da ristrutturare · 3 annunci/);
  const omiOnly={...full,signals:{...full.signals,market:{...full.signals.market,same_condition_key:'new'}}};
  assert.match(marketCell(omiOnly),/vs OMI medio/);
  const bench={discount:12,signals:{market:{refs:[],omi:null}}};
  assert.match(marketCell(bench),/12% sotto<\/span><small>vs prezzo di zona/);
  assert.match(marketCell({signals:null,discount:null}),/Confronto non disponibile/);
});
test('first-seen age is a lower bound; reductions shown only when observed',()=>{
  assert.match(ageCell(full),/>4 mesi<\/span><small class="signal-reduced">2 ribassi · -8,3%/);
  const seen={signals:{days_listed:9,listed_basis:'first_seen',reductions:{count:0}}};
  assert.match(ageCell(seen),/≥ 9 giorni/);assert.doesNotMatch(ageCell(seen),/ribass/);
  assert.match(ageCell({signals:{days_listed:null}}),/—/);
});
test('Oggi line lists only facts that exist',()=>{
  const line=signalLine(full);
  assert.match(line,/Online da 4 mesi/);assert.match(line,/Cambio d’uso dichiarato/);
  assert.equal(signalLine({signals:{days_listed:null,reductions:{count:0},market:{refs:[]}}}),'');
});
test('facts escape source quotes and extract the cadastral category',()=>{
  const html=signalFacts(full);
  assert.match(html,/<dd>A\/10<\/dd>/);
  assert.match(html,/Possibile cambio d’uso &lt;a&gt;/);
  assert.match(html,/Proprietario dichiarato/);
});
test('ladder keeps missing references visible and places the asking rule inside the scale',()=>{
  const html=priceLadder(full);
  assert.match(html,/1 di 3 annunci necessari/);
  assert.equal((html.match(/class="ladder-dot"/g)||[]).length,2);
  const left=Number(html.match(/class="ladder-ask" style="left:([\d.]+)%/)[1]);
  assert.ok(left>0&&left<100);
  assert.match(html,/2\.800–4\.000/);
});
test('ladder degrades without price or references',()=>{
  const none={signals:{market:{price_sqm:null,refs:[ref('to_renovate','Da ristrutturare',null,null,0)],omi:null}}};
  assert.match(priceLadder(none),/Nessun riferimento di prezzo per questo annuncio/);
  const bench=priceLadder({...none,benchmark:{min_sqm:1000,max_sqm:2000,source_label:'Listino <interno>'}});
  assert.match(bench,/Benchmark/);assert.match(bench,/Listino &lt;interno&gt;/);assert.match(bench,/1\.000–2\.000/);
  const noAsk={signals:{market:{price_sqm:null,refs:[ref('new','Nuovo',5000,null)],omi:null}}};
  const html=priceLadder(noAsk);
  assert.doesNotMatch(html,/ladder-ask/);assert.match(html,/5\.000/);
  assert.equal(priceLadder({}),'');
});
test('headroom to renovated and new values is explicit and scaled by surface',()=>{
  const html=priceLadder({...full,surface:100});
  assert.match(html,/<span>Verso ristrutturato<\/span><strong>\+€ 1\.900\/m²<\/strong><small>€ 190\.000 su 100 m²<\/small>/);
  assert.doesNotMatch(html,/Verso nuovo/);
  assert.doesNotMatch(priceLadder(full),/ladder-headroom/);
});
