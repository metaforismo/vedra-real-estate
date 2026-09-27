import assert from 'node:assert/strict';
import {test} from 'node:test';
import {runContent} from '../frontend/src/run-ui.js';

const base={id:'qa-run',agent_id:'qa-agent',runtime:'hermes',status:'queued',collected:0,
  created_at:'2026-09-26T10:00:00Z',config_snapshot:{criteria:{}},events:[],stats:{},
  analysis_progress:{total:0,accepted:0,pending:0}};

test('queued work has unknown acquisition counts and no made-up AI progress',()=>{
  const html=runContent(base);
  assert.match(html,/<strong>—<\/strong>/);
  assert.match(html,/In attesa della raccolta/);
  assert.doesNotMatch(html,/0 \/ 0|NaN|Infinity/);
});
test('failed collection does not keep suggesting AI is waiting to start',()=>{
  const html=runContent({...base,status:'failed'});
  assert.match(html,/Raccolta non completata/);
  assert.doesNotMatch(html,/In attesa della raccolta|class="spinner"/);
});
test('a run reusing prior analysis has no meaningless zero-of-zero counter',()=>{
  const html=runContent({...base,status:'completed',collected:1});
  assert.equal(html.split('Nessuna nuova analisi richiesta').length-1,1);
  assert.doesNotMatch(html,/0 \/ 0/);
});
test('partial AI work stays pending after a run ends',()=>{
  const html=runContent({...base,status:'partial',collected:1,analysis_progress:{total:3,accepted:1,pending:2}});
  assert.match(html,/1 \/ 3 risposte accettate/);
  assert.match(html,/2 annunci da analizzare/);
  assert.match(html,/non certifica la correttezza del modello/);
});
test('read-only users can inspect results but cannot be offered cancellation',()=>{
  const html=runContent({...base,status:'running'},false);
  assert.doesNotMatch(html,/data-action="cancel-run"/);
  assert.match(html,/data-action="agent-results"/);
});
test('research text is escaped and unsafe or duplicate visit links are excluded',()=>{
  const html=runContent({...base,config_snapshot:{criteria:{custom_prompt:'<b>Requisito</b>'}},events:[
    {step:'browser',data:{url:'javascript:alert(1)'}},
    {step:'browser',data:{url:'https://catalog.example/test'}},
    {step:'browser',data:{url:'https://catalog.example/test'}}]});
  assert.match(html,/&lt;b&gt;Requisito&lt;\/b&gt;/);
  assert.doesNotMatch(html,/href="javascript:/);
  assert.equal(html.split('href="https://catalog.example/test"').length-1,1);
});
test('Scout runs narrate pages read and listings acquired, escaped',()=>{
  const run={id:'r',status:'completed',runtime:'scout',agent_name:'Scout',stats:{processed:1,new:1,changed:0,errors:0,sources_ok:1,sources_total:2,page_requests:3,ai_calls:4,ai_estimated_eur:.021},events:[
    {step:'scout',level:'info',message:'Pagina letta: 3 annunci, 1 sezioni da aprire. <b>Milano</b>',data:{url:'https://agency.example/vendita/milano'},time:'2026-09-27T10:00:00Z'},
    {step:'extract',level:'info',message:'Acquisito: Loft <Brera>',data:{property_id:'p1',new:true},time:'2026-09-27T10:01:00Z'},
    {step:'source',level:'error',message:'Il sito blocca l’accesso automatico (HTTP 403).',time:'2026-09-27T10:02:00Z'}],config_snapshot:{criteria:{}}};
  const html=runContent(run,true);
  assert.match(html,/Cosa ha fatto Scout<span>1 annunci/);
  assert.match(html,/3 annunci, 1 sezioni da aprire. &lt;b&gt;Milano/);
  assert.match(html,/data-id="p1">Loft &lt;Brera&gt;/);
  assert.match(html,/blocca l’accesso automatico/);
  assert.match(html,/3 pagine aperte · 4 letture AI · € 0,021/);
  assert.doesNotMatch(runContent({...run,runtime:'local'},true),/Cosa ha fatto Scout/);
});
