import assert from 'node:assert/strict';
import {test} from 'node:test';
import {historicalPrice,historyItems,historyPreview,historyContent,priceMovement} from '../frontend/src/history-ui.js';
const context={currency:'EUR',transaction_type:'sale',area_basis:'commercial',surface:100};
const item={id:'one',observed_at:'2025-01-01',parser_version:'test',has_evidence:true,comparable:true,baseline:false,price_change_pct:-5,price_context:context,previous_price_context:context,changes:[{field:'price',before:100000,after:95000}]};
test('historical currencies and missing prices remain explicit, including cents',()=>{
  assert.equal(historicalPrice(null,'EUR'),'Non disponibile');
  assert.match(historicalPrice(90000.25,'USD'),/90.000,25 USD/);
  assert.match(historicalPrice(500,null),/valuta non registrata/);
  const html=historyPreview({id:'p',currency:'EUR',first_seen:'2025-01-01',observations:[{price:1,currency:'USD',observed_at:'2025-01-01'},{price:2,currency:null,observed_at:'2025-01-02'}]});
  assert.match(html,/1 USD/);assert.match(html,/valuta non registrata/);assert.doesNotMatch(html,/€/);
});
test('the UI uses the shared calculation without reconstructing missing percentages',()=>{
  assert.equal(priceMovement(item),'Ribasso 5%');
  assert.equal(priceMovement({...item,price_change_pct:10}),'Aumento 10%');
  for(const value of [null,undefined,NaN,0])assert.equal(priceMovement({...item,price_change_pct:value}),'');
});
test('full historical descriptions are available, escaped and not truncated',()=>{
  const tail='FINE <script>test</script>',text='Dettaglio '.repeat(100)+tail;
  const html=historyItems([{...item,changes:[{field:'description',before:text,after:'Nuovo testo'}]}]);
  assert.match(html,/Leggi il confronto completo/);assert.match(html,/FINE &lt;script&gt;test&lt;\/script&gt;/);assert.doesNotMatch(html,/<script>/);
  assert.match(html,/Prima/);assert.match(html,/Dopo/);
});
test('legacy evidence and baseline are distinct and original snapshots stay visible',()=>{
  assert.match(historyItems([{...item,baseline:true,comparable:false,changes:[],snapshot:{price:80000,currency:'USD',availability:'listed'}}]),/Prima rilevazione/);
  assert.match(historyItems([{...item,baseline:false,has_evidence:false,comparable:false,changes:[]}]),/Campi originali non conservati/);
  assert.match(historyItems([{...item,baseline:false,has_evidence:true,comparable:false,changes:[],snapshot:{price:80000,currency:'USD'}}]),/Manca una copia/);
});
test('preview stays bounded and full timeline keeps an explicit return action',()=>{
  const html=historyPreview({id:'p',first_seen:'2025-01-01',observations:Array.from({length:20},(_,n)=>({price:n,observed_at:'2025-01-01'}))});
  assert.equal((html.match(/<li>/g)||[]).length,3);assert.match(html,/20 rilevazioni/);assert.match(html,/tutte nella cronologia/);
  const empty=historyContent({items:[],total:0,with_fields:0,next_cursor:null},'p');
  assert.match(empty,/Nessuna rilevazione disponibile/);assert.match(empty,/Torna all’immobile/);assert.doesNotMatch(empty,/data-action="history-more"/);
});
test('unknown availability never implies that a listing has left the market',()=>{
  const html=historyItems([{...item,price_change_pct:null,changes:[{field:'availability',before:'listed',after:'unknown'}]}]);
  assert.match(html,/>Disponibilità</);assert.match(html,/Da verificare/);assert.doesNotMatch(html,/>availability<|Non disponibile/);
  assert.match(historyItems([{...item,changes:[],snapshot:{price:null,availability:null}}]),/Non registrata/);
});
