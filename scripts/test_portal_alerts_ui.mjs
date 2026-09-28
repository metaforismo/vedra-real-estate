import assert from 'node:assert/strict';
import {test} from 'node:test';
import {alertsSection,createPortalAlertsController,originNote,originTag,portalOrigin,uploadSummary} from '../frontend/src/portal-alerts-ui.js';

const card=(extra={})=>({url:'https://www.immobiliare.it/annunci/1/',evidence:{portal_card:{portal:'immobiliare.it',origin:'alert',
  seen_at:'2026-09-28T05:12:00+00:00',source_url:'https://www.immobiliare.it/annunci/1/',incomplete:true,price_drop:true,old_price:460000,...extra}}});
const status={imap:{configured:true,host:'imap.example',user:'avvisi@studio.example',folder:'INBOX',poll_minutes:15},checked_at:null,error:'Casella imap.example non raggiungibile.',
  totals:{read:3,ignored:1,rejected:0,created:7,updated:2},recent:[{portal:'idealista',subject:'Nuovi <b>annunci</b>',sent_at:'2026-09-27T17:40:00+00:00',status:'processed',cards:2,created:2,updated:0}],max_mb:2};

test('origin is shown only for portal cards, briefly and escaped',()=>{
  assert.equal(portalOrigin({evidence:{}}),null);
  assert.equal(originTag({evidence:{}}),'');assert.equal(originNote({}),'');
  assert.match(originTag(card()),/Da avviso immobiliare\.it · 28 set · da completare/);
  assert.equal(originTag(card({incomplete:false})),'');
  const note=originNote(card());
  assert.match(note,/ribasso dichiarato da € 460\.000</);assert.match(note,/Da completare: apri l’annuncio e invia con Vedra Capture/);
  assert.match(note,/href="https:\/\/www\.immobiliare\.it\/annunci\/1\/"/);
  assert.doesNotMatch(originNote(card({incomplete:false})),/Da completare/);
  assert.match(originNote(card({origin:'results_page',price_drop:false})),/Dai risultati di immobiliare\.it/);
  const hostile=originNote(card({portal:'<img src=x onerror=alert(1)>',source_url:'javascript:alert(1)'}));
  assert.doesNotMatch(hostile,/<img|javascript:/);
});

test('summaries list only non-zero counts',()=>{
  assert.equal(uploadSummary({files:2,cards:14,created:9,updated:5,no_price:2}),'2 email · 14 annunci · 9 nuovi · 5 aggiornati · 2 senza prezzo');
  assert.equal(uploadSummary({files:1,duplicates:1}),'1 email · 1 già letta');
  assert.equal(uploadSummary({files:1,cards:1,created:1,ignored:1}),'1 email · 1 annuncio · 1 nuovo · 1 non dai portali');
});

test('the Fonti block shows the mailbox without secrets and hides from viewers',()=>{
  assert.equal(alertsSection({user:{role:'viewer'},portalAlerts:{data:status}}),'');
  const html=alertsSection({user:{role:'analyst'},portalAlerts:{data:status}});
  assert.match(html,/avvisi@studio\.example/);assert.match(html,/imap\.example · ogni 15 min/);
  assert.match(html,/Casella imap\.example non raggiungibile\./);assert.match(html,/Controlla ora/);
  assert.match(html,/Nuovi &lt;b&gt;annunci&lt;\/b&gt;/);assert.doesNotMatch(html,/password/i);
  const manual=alertsSection({user:{role:'admin'},portalAlerts:{data:{...status,imap:{configured:false},error:null}}});
  assert.match(manual,/Casella non collegata/);assert.doesNotMatch(manual,/Controlla ora/);assert.match(manual,/Carica email/);
});

function harness(responses){
  const s={page:'sources',user:{role:'analyst'}},calls=[];let refreshed=0;
  const controller=createPortalAlertsController({s,render(){},refresh:async()=>{refreshed++;},read:async f=>'QUJD'+f.name,
    request:async(url,options)=>{calls.push({url,options});const next=responses.shift();if(next instanceof Error)throw next;return typeof next==='function'?next():next;}});
  return {s,calls,controller,refreshed:()=>refreshed};
}

test('uploads go one file per request and add up the outcomes',async()=>{
  const h=harness([{status:'processed',cards:3,created:2,updated:1,no_price:1},{status:'duplicate'},new Error('Email oltre il limite di 2 MB: non letta.'),status]);
  await h.controller.upload([{name:'a.eml',size:10},{name:'b.eml',size:10},{name:'c.eml',size:10}]);
  const posts=h.calls.filter(c=>c.url==='/portal-alerts/upload');
  assert.equal(posts.length,3);assert.equal(posts[0].options.body.eml_base64,'QUJDa.eml');
  assert.equal(h.s.portalAlerts.result.text,'2 email · 3 annunci · 2 nuovi · 1 aggiornato · 1 senza prezzo · 1 già letta · Email oltre il limite di 2 MB: non letta.');
  assert.equal(h.s.portalAlerts.result.failed,true);assert.equal(h.refreshed(),1);assert.equal(h.s.portalAlerts.busy,false);
});

test('files over the limit are not sent',async()=>{
  const h=harness([status]);h.s.portalAlerts={data:status,busy:false};
  await h.controller.upload([{name:'big.eml',size:3_000_000}]);
  assert.equal(h.calls.filter(c=>c.url==='/portal-alerts/upload').length,0);
  assert.match(h.s.portalAlerts.result.text,/big\.eml: oltre 2 MB/);
});

test('a late status response after navigation or logout is discarded',async()=>{
  let resolve;const h=harness([()=>new Promise(r=>{resolve=r;})]);
  const pending=h.controller.load();h.controller.reset();resolve(status);await pending;
  assert.equal(h.s.portalAlerts,null);
});

test('a mailbox error stays on the mailbox row, not as a second message',async()=>{
  const h=harness([{read:0,ignored:0,created:0,updated:0,error:'Casella imap.example non raggiungibile.'},status]);
  await h.controller.actions['alerts-check']();
  assert.equal(h.s.portalAlerts.result,null);assert.equal(h.s.portalAlerts.data.error,'Casella imap.example non raggiungibile.');
  const ok=harness([{read:0,ignored:0,created:0,updated:0,error:null},status]);
  await ok.controller.actions['alerts-check']();assert.equal(ok.s.portalAlerts.result.text,'Nessuna nuova email.');
});

test('Vedra Capture summarises a results page precisely',async()=>{
  const {resultsSummary}=await import('../extension/capture.js');
  assert.equal(resultsSummary({cards:14,created:9,updated:5,unchanged:0,no_price:2}),'14 annunci · 9 nuovi · 5 aggiornati · 2 senza prezzo');
  assert.equal(resultsSummary({cards:1,created:0,updated:0,unchanged:1,no_price:0}),'1 annuncio · 1 già presente');
});

test('a row first read from its detail page was only seen again in an alert',()=>{
  const seen=portalOrigin(card({from_card:false,incomplete:false,first_seen_at:'2026-09-20T08:00:00+00:00'}));
  assert.equal(seen.text,'Visto anche in un avviso immobiliare.it · 28 set');
  assert.match(originNote(card({from_card:false,incomplete:false,origin:'results_page'})),/Visto anche nei risultati di immobiliare\.it/);
  assert.equal(portalOrigin(card({from_card:true})).text,'Da avviso immobiliare.it · 28 set');
});
