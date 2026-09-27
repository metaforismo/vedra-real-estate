import assert from 'node:assert/strict';
import {test} from 'node:test';
import {createInboxController} from '../frontend/src/inbox-controller.js';
import {inboxView} from '../frontend/src/inbox-ui.js';
const data=(ids,extra={})=>({items:ids.map(id=>({id})),total:ids.length,unread_total:ids.length,has_more:false,next_cursor:null,...extra});
function harness(){
  const s={page:'inbox',user:{id:'one'},ops:{},notifications:[]},pending=[],opened=[],focused=[];
  const controller=createInboxController({s,render(){},refresh:async()=>{},showProperty:async id=>opened.push(id),showRun:async id=>opened.push(id),notify(){},focus:id=>focused.push(id),request:(url,options)=>new Promise((resolve,reject)=>pending.push({url,options,resolve,reject}))});
  return {s,pending,opened,focused,...controller};
}
test('late filter responses cannot replace the current selection',async()=>{
  const h=harness(),old=h.load(),next=h.actions['inbox-filter']({dataset:{unread:'true'}});
  assert.equal(h.pending[0].options.signal.aborted,true);
  assert.match(h.pending[1].url,/unread=true/);
  h.pending[1].resolve(data(['new']));await next;
  h.pending[0].resolve(data(['old']));await old;
  assert.deepEqual(h.s.inbox.items.map(x=>x.id),['new']);assert.equal(h.focused.at(-1),'inbox-unread');
});
test('pagination uses the cursor, deduplicates and retains rows after failure',async()=>{
  const h=harness(),first=h.load();h.pending[0].resolve(data(['a'],{has_more:true,next_cursor:{id:'a',created_at:'date'}}));await first;
  const failed=h.actions['inbox-more']();assert.match(h.pending[1].url,/before_id=a/);
  h.pending[1].reject(new Error('Offline'));await failed;
  assert.equal(h.s.inbox.moreError,'Offline');assert.equal(h.s.inbox.items.length,1);
  const retry=h.actions['inbox-more']();h.pending[2].resolve(data(['a','b']));await retry;
  assert.deepEqual(h.s.inbox.items.map(x=>x.id),['a','b']);assert.equal(h.s.inbox.moreError,'');
});
test('navigation and logout invalidate pending reads',async()=>{
  const h=harness(),load=h.load();h.s.page='properties';h.cancel();h.pending[0].resolve(data(['old']));await load;
  assert.equal(h.s.inbox.items.length,0);
  h.s.page='inbox';const next=h.load();h.reset();h.pending[1].resolve(data(['private']));await next;
  assert.equal(h.s.inbox.items.length,0);assert.equal(h.s.inbox.loaded,false);
});
test('read requests are single flight and cannot open a target after navigation',async()=>{
  const h=harness();h.s.inbox.items=[{id:'n',property_id:'p'}];
  const mark=h.actions['notification-open']({dataset:{id:'n'}});
  await h.actions['notification-open']({dataset:{id:'n'}});assert.equal(h.pending.length,1);
  h.s.page='properties';h.cancel();h.pending[0].resolve({ok:true});await mark;
  assert.deepEqual(h.opened,[]);assert.equal(h.s.inboxBusy,false);
});
test('acknowledged personal reads reload the feed even if workspace refresh does nothing',async()=>{
  const h=harness();h.s.inbox.items=[{id:'n'}];
  const mark=h.actions['notification-read']({dataset:{id:'n'}});h.pending[0].resolve({ok:true});
  await new Promise(resolve=>setImmediate(resolve));assert.match(h.pending[1].url,/notifications\/feed/);
  h.pending[1].resolve(data([]));await mark;assert.equal(h.s.inboxBusy,false);assert.equal(h.s.ops.unread,0);
});
test('static events have no dead destination and content is escaped',()=>{
  const h=harness();Object.assign(h.s.inbox,data(['n']));h.s.inbox.items=[{id:'n',title:'<private>',body:'<script>',kind:'source_blocked',created_at:'2026-01-01'}];
  const html=inboxView(h.s);assert.doesNotMatch(html,/data-action="notification-open"|<private>|<script>/);assert.match(html,/&lt;private&gt;/);assert.match(html,/Segna come letta/);
  h.s.inbox.items[0].property_id='p';assert.match(inboxView(h.s),/Apri immobile/);
  h.s.inbox.items[0].read_at='date';assert.doesNotMatch(inboxView(h.s),/data-action="notification-read"/);
});
