import test from 'node:test';
import assert from 'node:assert/strict';
import {comparisonContent} from '../frontend/src/comparison-ui.js';
import {compareDialog} from '../frontend/src/dialogs.js';
const property=(overrides={})=>({id:'a',title:'Immobile A',city:'Milano',currency:'EUR',transaction_type:'sale',price:520000.75,price_sqm:5200.35,surface:100,priority:{score:null},review_status:'new',availability:'listed',analysis:{strategies:[]},...overrides});
test('comparison keeps price cents and original currency, reads €/m² in whole euros, states benchmark direction',()=>{
  const html=comparisonContent([property({discount:12,benchmark:{min_sqm:4500,max_sqm:6500,currency:'EUR',source_label:'Fonte test',period:'2026-S1'}}),property({id:'b',currency:'USD',discount:-4,benchmark:{currency:'USD'}})]);
  assert.match(html,/€ 520\.000,75/);assert.match(html,/520\.000,75 USD/);
  assert.match(html,/€ 5\.200\/m²/);assert.match(html,/12% sotto il prezzo di zona/);assert.match(html,/4% sopra il prezzo di zona/);
  assert.match(html,/Valute o operazioni diverse/);assert.doesNotMatch(html,/—\/100/);
});
test('missing values remain unknown, zero reductions and zero priority remain meaningful',()=>{
  const html=comparisonContent([property({surface:null,price:null,priority:{score:0},decision:{price_reductions:0}}),property({id:'b'})]);
  assert.match(html,/0 \/ 100/);assert.match(html,/Recapito da trovare/);assert.match(html,/Data non disponibile/);
  assert.doesNotMatch(html,/— m²|NaN|undefined|Invalid Date/);
});
test('four references retain source counts and reject stale OMI',()=>{
  const refs={groups:[{key:'to_renovate',count:2,source_count:1,median_sqm:null,reason:'Servono almeno 3 asset',warnings:[]},{key:'renovated',count:5,source_count:2,median_sqm:6500.25,warnings:['Una sola fonte test']}],omi:{status:'available',stale:true,period:'2020-S1',rows:[{min_sqm:999,max_sqm:1000}]}};
  const html=comparisonContent([property({market_references:refs}),property({id:'b'})]);
  assert.match(html,/2 annunci · 1 fonte/);assert.match(html,/Servono almeno 3 asset/);assert.match(html,/€ 6\.500\/m²/);
  assert.match(html,/Periodo da aggiornare: 2020-S1/);assert.doesNotMatch(html,/999/);
  for(const title of ['Da ristrutturare','Ristrutturato','Nuovo','OMI'])assert.ok(html.includes(title));
});
test('provenance, uncertain area basis and contact evidence are displayed without inventing validation',()=>{
  const html=comparisonContent([property({market_references:{omi:{status:'available',rows:[{min_sqm:2000.5,max_sqm:3000,area_basis:'unknown',type:'Abitazioni',condition:'Normale'}]}},decision:{contact:{name:'Broker',telephone:'+39020000000',email:'broker@example.test'},contact_route:{label:'Mandato dichiarato'}},decision_support:{freshness:{label:'Da ricontrollare',method:'Importazione'},questions:['Verificare il mandato']}})]);
  assert.match(html,/Base superficie non indicata/);assert.match(html,/Mandato dichiarato/);assert.match(html,/Verificare il mandato/);assert.match(html,/href="tel:\+39020000000">.*?<span>\+39 020000000<\/span>/);assert.match(html,/href="mailto:broker%40example.test"/);
});
test('source content and links are escaped; export holds the compared IDs',()=>{
  const html=comparisonContent([property({id:'a"<',title:'<script>bad</script>',url:'javascript:bad',source_name:'<b>Fonte</b>',decision:{contact:{email:'bad"<@x.test',telephone:'bad'}}}),property({id:'b'})]);
  assert.doesNotMatch(html,/<script>|href="javascript:|href="tel:|href="mailto:/);
  assert.match(html,/&lt;script&gt;/);assert.match(html,/data-ids="\[&quot;a/);
});
test('comparison has accessible tabs, real table headers and preserves every original indicator',()=>{
  const html=compareDialog([property(),property({id:'b'})]);
  assert.equal((html.match(/role="tab"/g)||[]).length,3);assert.equal((html.match(/role="tabpanel"/g)||[]).length,3);
  assert.equal((html.match(/aria-selected="true"/g)||[]).length,1);assert.equal((html.match(/tabindex="0" hidden/g)||[]).length,2);
  assert.match(html,/scope="row"/);assert.match(html,/scope="col"/);
  for(const title of ['Prezzo richiesto','Superficie','Priorità di verifica','Scostamento dal prezzo di zona','Tipologia','Stato manutentivo','Strategie','Completezza','Prezzo di zona','Fonte','Ultima acquisizione'])assert.ok(html.includes(title));
});

test('confirmed linked listings are not presented as distinct opportunities',()=>{
  const html=comparisonContent([property({cross_sources:{entries:[{id:'a'},{id:'b'}]}}),property({id:'b'})]);
  assert.match(html,/Annunci dello stesso asset/);
  assert.doesNotMatch(comparisonContent([property(),property({id:'b'})]),/Annunci dello stesso asset/);
});
test('unknown availability means to verify, never unavailable or sold',()=>{
  const html=comparisonContent([property({availability:'unknown'}),property({id:'b',availability:'sold'})]);
  const row=html.match(/<tr><th scope="row">Disponibilità<\/th>(.*?)<\/tr>/)[1];
  assert.match(row,/Da verificare/);assert.match(row,/Venduto/);assert.doesNotMatch(row,/Non disponibile/);
});
