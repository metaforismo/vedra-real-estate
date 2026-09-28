import assert from 'node:assert/strict';
import {test} from 'node:test';
import {pipelineRows,pipelineView,workForm} from '../frontend/src/pipeline-ui.js';
const state=()=>({user:{role:'admin'},data:{properties:[
  {id:'a',title:'Casa A',city:'Milano',review_status:'new',availability:'listed'},
  {id:'b',title:'Casa B',city:'Milano',review_status:'negotiation',availability:'sold'},
  {id:'c',title:'Casa C',city:'Monza',review_status:'acquired',availability:'listed'},
  {id:'d',title:'Casa D',city:'Milano',review_status:'reviewing',availability:'unknown'},
]},ops:{team:[{id:'u',name:'Ada',role:'analyst'}],work:[
  {property_id:'a',owner_id:'u',due_date:'2026-09-26',checklist:{source_checked:true,not_a_check:true}},
  {property_id:'b',owner_id:'u',due_date:'2026-09-25'},
  {property_id:'c',due_date:'2020-01-01'},
]}});

test('deadlines use calendar dates; completed work is never overdue',()=>{
  const s=state();let rows=pipelineRows(s,'2026-09-26');
  assert.equal(rows.find(r=>r.p.id==='a').late,false);
  assert.equal(rows.find(r=>r.p.id==='c').late,false);
  assert.equal(rows[0].p.id,'b');assert.equal(rows.at(-1).p.id,'c');
  s.pipelineFocus='overdue';assert.deepEqual(pipelineRows(s,'2026-09-26').map(r=>r.p.id),['b']);
  s.pipelineFocus='unassigned';assert.deepEqual(pipelineRows(s).map(r=>r.p.id),['d']);
});
test('stage, owner, availability and trimmed text filters compose',()=>{
  const s=state();s.pipelineQuery=' ada ';s.pipelineOwner='u';s.pipelineStage='negotiation';s.pipelineAvailability='closed';
  assert.deepEqual(pipelineRows(s).map(r=>r.p.id),['b']);
  s.pipelineAvailability='listed';assert.equal(pipelineRows(s).length,0);
});
test('only declared checklist keys count; missing assignees are not silently unassigned',()=>{
  const s=state();assert.equal(pipelineRows(s).find(r=>r.p.id==='a').done,1);
  s.ops.team=[];assert.equal(pipelineRows(s).find(r=>r.p.id==='a').owner,'Responsabile non disponibile');
  s.pipelineFocus='unassigned';assert.deepEqual(pipelineRows(s).map(r=>r.p.id),['d']);
});
test('work form retains unavailable owners and uses the stage from the versioned snapshot',()=>{
  const s=state();const html=workForm(s,s.data.properties[0],{version:4,owner_id:'gone',stage:'negotiation'});
  assert.match(html,/<option value="gone" selected/);
  assert.match(html,/<option value="negotiation" selected/);
  s.user.role='viewer';const read=workForm(s,s.data.properties[0],{version:0});
  assert.match(read,/<fieldset disabled/);assert.doesNotMatch(read,/type="submit"/);assert.match(read,/Torna all’immobile/);
});
test('partial and empty workspaces have honest counts and actionable recovery',()=>{
  const s=state();s.data.has_more=true;
  assert.match(pipelineView(s),/Vista parziale/);
  s.data.properties=[];assert.match(pipelineView(s),/Nessun immobile in lavorazione/);
  s.pipelineStage='negotiation';assert.match(pipelineView(s),/Mostra tutti/);
});
test('titles and owner names are escaped in both list and board views',()=>{
  const s=state();s.data.properties[0].title='<unsafe>';s.ops.team[0].name='<owner>';
  for(const layout of ['list','board']){s.pipelineLayout=layout;const html=pipelineView(s);assert.doesNotMatch(html,/<unsafe>|<owner>/);assert.match(html,/&lt;unsafe&gt;/);}
});
test('team columns empty on every row collapse into one line; partly empty ones keep faint dashes',()=>{
  const s=state();s.pipelineFocus='unassigned';
  const html=pipelineView(s);
  assert.doesNotMatch(html,/>Responsabile<\/th>|>Scadenza<\/th>|>Verifiche<\/th>/);
  assert.match(html,/class="pg-note work-hint">Nessun responsabile · nessuna scadenza · nessuna verifica\. Si assegnano da Gestisci\./);
  const all=pipelineView(state());
  assert.match(all,/>Responsabile<\/th>/);assert.doesNotMatch(all,/work-hint/);assert.match(all,/class="pg-dash"/);
  assert.match(all,/class="text-link work-manage" data-action="deal-work"/);
  s.user.role='viewer';assert.doesNotMatch(pipelineView(s),/Si assegnano/);
});
