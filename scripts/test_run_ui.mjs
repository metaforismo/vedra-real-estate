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
