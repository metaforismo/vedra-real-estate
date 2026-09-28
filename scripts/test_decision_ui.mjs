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
  assert.match(html,/nessun richiamo programmato/);
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
  assert.match(html,/<span class="why-lead below">10% sotto<\/span> zona/);
  assert.match(html,/<p class="today-provenance"><span>Milano · Value Add<\/span><\/p>/);
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
  assert.match(html,/href="tel:\+390200000000"><svg[^]*?<span>\+39 0200000000<\/span>/);
  // Recapiti and the outcome button share one line: the shared contact helper, never a bespoke link.
  assert.match(html,/<div class="contact-actions"><a class="contact-action" href="tel:/);
  assert.match(html,/Registra esito<\/button><\/div>/);
  assert.doesNotMatch(html,/Filiera da verificare/);
});
test('one contact helper: formatted phone, encoded e-mail, nothing for missing or invalid recapiti',async()=>{
  const {contactActions,phoneText}=await import('../frontend/src/ui.js');
  assert.equal(phoneText('+390276543210'),'+39 0276543210');
  const html=contactActions({telephone:'+39 02 7654 3210',email:'a<b>@x.it'},{size:'sm'});
  assert.match(html,/class="contact-action small" href="tel:\+390276543210"/);assert.match(html,/<span>\+39 0276543210<\/span>/);
  assert.doesNotMatch(html,/mailto:/);
  assert.equal(contactActions(null),'');assert.equal(contactActions({telephone:'n.d.'}),'');
  assert.match(contactActions({phone:'0289919105',email:'x@y.it'}),/mailto:x%40y.it/);
});
test('portal cards to open get one calm group, only when there are some',async()=>{
  const {todayPanel}=await import('../frontend/src/decision-ui.js');
  const none=todayPanel({...state,ops:{today:{call:[],verify:[],portals:{items:[],total:0}}}});
  assert.doesNotMatch(none,/Dai portali/);
  const item={id:'p1',title:'Bilocale <corso Lodi>',price:435000,currency:'EUR',city:'Milano',zone:'Lodi',portal:'immobiliare.it',url:'https://www.immobiliare.it/annunci/1/',drop_pct:-5.4};
  const html=todayPanel({...state,ops:{today:{call:[],verify:[],portals:{items:[item,{...item,id:'p2',price:null,drop_pct:null,url:'javascript:alert(1)'}],total:9}}}});
  assert.match(html,/Dai portali <span class="quiet-pill">9<\/span>/);
  assert.match(html,/Bilocale &lt;corso Lodi&gt;/);assert.match(html,/−5% ribasso/);assert.match(html,/Prezzo non indicato/);
  assert.equal((html.match(/Apri su immobiliare\.it/g)||[]).length,1);assert.doesNotMatch(html,/javascript:/);
  assert.match(html,/data-action="open-focus" data-focus="portal">Mostra tutti · 9/);
});
