import test from 'node:test';
import assert from 'node:assert/strict';
import {api} from '../frontend/src/api.js';

test('API preserves actionable save-conflict context without rendering an object as text',async()=>{
  const original=globalThis.fetch;
  try{
    globalThis.fetch=async()=>new Response(JSON.stringify({detail:{message:'Rileggi la ricerca.',agent_id:'research-1'}}),{status:409});
    await assert.rejects(api('/agents/research-1'),e=>e.status===409&&e.message==='Rileggi la ricerca.'&&e.context.agent_id==='research-1');
  }finally{globalThis.fetch=original;}
});
test('API retains validation, plain-text and network error messages',async()=>{
  const original=globalThis.fetch;
  try{
    for(const [detail,expected] of [['Fonte non trovata.','Fonte non trovata.'],[[{loc:['body','city'],msg:'Value error, Comune richiesto'}],'city: Comune richiesto']]){
      globalThis.fetch=async()=>new Response(JSON.stringify({detail}),{status:422});
      await assert.rejects(api('/agents'),e=>e.message===expected&&e.context===null);
    }
    globalThis.fetch=async()=>{throw new TypeError('Network error');};
    await assert.rejects(api('/agents'),{message:'Connessione non disponibile.'});
  }finally{globalThis.fetch=original;}
});
test('a truncated success response cannot be accepted as a completed save',async()=>{
  const original=globalThis.fetch;
  try{
    globalThis.fetch=async()=>new Response('{"id":',{status:201});
    await assert.rejects(api('/agents',{method:'POST',body:{name:'QA'}}),{message:'Risposta incompleta. Riprova.'});
    globalThis.fetch=async()=>new Response('Unavailable',{status:503});
    await assert.rejects(api('/agents'),e=>e.status===503&&e.message==='Errore HTTP 503');
  }finally{globalThis.fetch=original;}
});
