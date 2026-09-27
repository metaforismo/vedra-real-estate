import {test} from 'node:test';
import assert from 'node:assert/strict';
import {importDialog,importPayload,importResultDialog} from '../frontend/src/import-ui.js';
import {sourceDirectory} from '../frontend/src/sources-ui.js';
const form=(overrides={})=>({elements:{kind:{value:'csv'},input_mode:{value:'paste'},content:{value:'title,price\nCasa,100000'},file:{files:[]},source_url:{value:'https://example.com/stale'},permission_confirmed:{checked:true},...overrides}});
test('import modes choose one input and irrelevant URL is not transmitted',async()=>{
  const payload=await importPayload(form({file:{files:[{name:'old.html'}]}}));assert.equal(payload.source_url,'');assert.equal(payload.kind,'csv');assert.match(payload.content,/Casa/);
});
test('file import refuses wrong format, invalid UTF-8 and oversized bytes',async()=>{
  const make=file=>form({input_mode:{value:'file'},file:{files:[file]}});
  await assert.rejects(importPayload(make({name:'old.html',size:10})),/CSV/);
  await assert.rejects(importPayload(make({name:'large.csv',size:4000001})),/4 MB/);
  await assert.rejects(importPayload(make({name:'invalid.csv',size:1,arrayBuffer:async()=>new Uint8Array([255]).buffer})),/UTF-8/);
  await assert.rejects(importPayload(form({content:{value:'é'.repeat(2000001)}})),/4 MB/);
});
test('empty content and missing files produce specific errors',async()=>{
  await assert.rejects(importPayload(form({content:{value:' \n'}})),/Incolla/);
  await assert.rejects(importPayload(form({input_mode:{value:'file'}})),/Seleziona/);
});
test('selected files provide exact content and HTML original URL',async()=>{
  const content='<html>à</html>',file={name:'listing.html',size:20,arrayBuffer:async()=>new TextEncoder().encode(content).buffer};
  const payload=await importPayload(form({kind:{value:'html'},input_mode:{value:'file'},file:{files:[file]}}));
  assert.equal(payload.content,content);assert.equal(payload.source_url,'https://example.com/stale');
});
test('results expose readable counts and retain technical details under disclosure',()=>{
  const html=importResultDialog({kind:'csv',imported:10,new:3,changed:2});
  for(const text of ['Nuovi','Aggiornati','Invariati','>5</strong>','Apri immobili importati','<details>'])assert.ok(html.includes(text));
  assert.match(importResultDialog({kind:'benchmarks',imported:2}),/Apri benchmark/);
  assert.match(importDialog({},'benchmarks'),/<option value="benchmarks" selected/);
});
test('manual imports have no web verification controls and empty quality is unmeasured',()=>{
  const s={user:{role:'admin'}};
  const html=sourceDirectory(s,[{id:'f',kind:'import',name:'<File>',enabled:true,property_count:0,quality:0,config:{}}]);
  assert.match(html,/&lt;File&gt;/);assert.doesNotMatch(html,/probe-source|0%|verificate/);assert.match(html,/File importati/);
  const web=sourceDirectory({user:{role:'viewer'}},[{id:'a',kind:'html',name:'Web',domain:'example.com',enabled:true,property_count:0,quality:0,config:{},status:'unverified'}]);
  assert.doesNotMatch(web,/edit-source|toggle-source|probe-source/);assert.match(web,/>—</);
});

test('source context stays visible outside advanced filters',async()=>{
  const {catalogView,defaultFilters}=await import('../frontend/src/catalog-ui.js');
  const s={selected:new Set(),user:{role:'admin'},filters:{...defaultFilters(),source_id:'f'},catalog:{items:[],total:0,facets:{cities:[],currencies:[]}},data:{sources:[{id:'f',name:'File <cliente>'}],agents:[]}};
  const html=catalogView(s,'','');assert.match(html,/Fonte: File &lt;cliente&gt;/);assert.match(html,/clear-source-filter/);
});
