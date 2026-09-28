import assert from 'node:assert/strict';
import {test} from 'node:test';
import {contactForm,decisionSection} from '../frontend/src/decision-ui.js';

const state={user:{role:'analyst'}};
const property={id:'one',decision:{contact:{organization:'Agenzia <test>'},contact_route:{label:'Mandato dichiarato',quote:'Documento <fonte>'},calls:[]}};

test('contact name falls back to the organization and outcome requires an explicit choice',()=>{
  const html=contactForm(property);
  assert.match(html,/value="Agenzia &lt;test&gt;"/);
  assert.match(html,/name="outcome"[^>]*required><option value="" disabled selected/);
  assert.doesNotMatch(html,/<option value="no_answer" selected/);
});
test('a source declaration stays separate from human mandate verification',()=>{
  const html=decisionSection(state,property);
  assert.match(html,/<summary>Dichiarazione nella fonte<\/summary><blockquote>Documento &lt;fonte&gt;/);
  assert.match(html,/Nessun contatto registrato/);
  assert.doesNotMatch(html,/Mandato verificato dal team/);
});
test('missing follow-up is explicit and notes preserve escaped full content',()=>{
  const p={...property,decision:{...property.decision,calls:[{outcome:'reached',contact_name:'Broker',author:'Ada',mandate_status:'not_checked',note:'Prima riga\n<seconda riga>',created_at:'2026-09-27T10:00:00Z'}]}};
  const html=decisionSection(state,p);
  assert.match(html,/Non programmato/);
  assert.match(html,/Prima riga\n&lt;seconda riga&gt;/);
  assert.match(html,/Mandato da verificare/);
  assert.doesNotMatch(html,/undefined|Invalid Date/);
});
test('viewer can read the contact recap but cannot register an outcome',()=>{
  const html=decisionSection({user:{role:'viewer'}},property);
  assert.match(html,/data-action="contact-log"[^>]* disabled/);
});

test('daily queue keeps every candidate with honest counts and a short first view',async()=>{
  const {todayPanel}=await import('../frontend/src/decision-ui.js');
  const row=n=>({id:`row-${n}`,title:`Immobile ${n}`,price:100,currency:'EUR',discount:10,contact:{},reasons:['Nei criteri di Milano · Value Add','Scarto dal benchmark: -10.0%'],checks:[],url:''});
  const html=todayPanel({...state,ops:{today:{call:Array.from({length:12},(_,n)=>row(n)),verify:Array.from({length:6},(_,n)=>row(n+12))}}});
  assert.match(html,/12 contatti/);assert.match(html,/Mostra altri 7 contatti/);assert.match(html,/Mostra altri 2 da verificare/);
  assert.equal((html.match(/class="today-item[ "]/g)||[]).length,18);
  // Without market signals the benchmark gap still leads the evidence; the matching search is the provenance.
  assert.match(html,/<span class="why-lead below">10% sotto<\/span> il prezzo di zona/);
  assert.match(html,/Ricerca «Milano · Value Add»/);
  assert.doesNotMatch(html,/href=""|href="#"/);
});
test('daily queue preserves disclosure state, missing-contact reasons and explicit sample limits',async()=>{
  const {todayPanel}=await import('../frontend/src/decision-ui.js');
  const row={id:'one',title:'<asset>',contact:null,reasons:[],checks:['Recapito da trovare','Recapito da trovare'],url:'javascript:alert(1)'};
  const html=todayPanel({...state,todayExpanded:{verify:false,verifyMore:true},ops:{today:{call:[],verify:Array(6).fill(row),limited:true}}});
  assert.match(html,/data-today-section="verify" >/);assert.match(html,/data-today-section="verifyMore" open/);
  assert.match(html,/Primi 100 candidati/);assert.match(html,/Apri tutto l’archivio/);
  assert.doesNotMatch(html,/javascript:|undefined|<asset>/);
  assert.equal((html.match(/<li>Recapito da trovare<\/li>/g)||[]).length,6);
});
test('one leftover row reads as singular and a callable row without a name says so',async()=>{
  const {todayPanel}=await import('../frontend/src/decision-ui.js');
  const row=n=>({id:`r${n}`,title:'A',price:1,currency:'EUR',contact:{telephone:'+390200000000'},contact_route:{kind:'unknown',label:'Filiera da verificare'},reasons:[],checks:[]});
  const html=todayPanel({...state,ops:{today:{call:Array.from({length:6},(_,n)=>row(n)),verify:[]}}});
  assert.match(html,/Mostra un altro contatto/);
  assert.match(html,/Nome non indicato/);
  assert.match(html,/href="tel:\+390200000000"/);
  assert.doesNotMatch(html,/Filiera da verificare/);
});
