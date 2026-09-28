import {icon} from './icons.js';
let csrf = '';
async function request(url,options){
  try{return await fetch(url,options);}
  catch(error){
    if(error.name==='AbortError')throw error;
    throw new Error('Connessione non disponibile.');
  }
}
export function setCsrf(value) { csrf = value || ''; }
export async function api(path, options = {}) {
  const {method = 'GET', body, signal} = options;
  const headers = {Accept:'application/json'};
  if (body !== undefined) headers['Content-Type']='application/json';
  if (!['GET','HEAD'].includes(method)) headers['X-CSRF-Token']=csrf;
  const response = await request(`/api${path}`, {method, headers, credentials:'same-origin', body:body===undefined?undefined:JSON.stringify(body), signal});
  let result;
  try{result=await response.json();}
  catch{
    if(response.ok)throw new Error('Risposta incompleta. Riprova.');
    result={detail:`Errore HTTP ${response.status}`};
  }
  if (!response.ok) {
    const message = Array.isArray(result.detail) ? result.detail.map(x=>{const field=(x.loc||[]).slice(1).join('.');return (field?field+': ':'')+String(x.msg||'Dato non valido').replace(/^Value error, /,'');}).join('; ') : typeof result.detail==='object' ? result.detail?.message : result.detail;
    const error = new Error(message || `Errore HTTP ${response.status}`);
    error.status = response.status;
    error.context = result.detail && !Array.isArray(result.detail) && typeof result.detail==='object' ? result.detail : null;
    throw error;
  }
  return result;
}
export function toast(message, error = false) {
  const container = document.getElementById('toasts');
  for (const previous of container.children) {
    if (previous.textContent === message) previous.remove();
  }
  const item = document.createElement('div');
  item.className = `toast ${error?'error':''}`;
  item.setAttribute('role',error?'alert':'status');
  const text=document.createElement('span');
  text.textContent=message;
  item.innerHTML=icon(error?'alert':'checkCircle');
  item.append(text);
  container.append(item);
  // Leave along the edge it came from, and pause while the pointer rests on it (Sonner principles).
  let remaining=error?8500:4500,started=Date.now(),timer;
  const leave=()=>{item.classList.add('leaving');item.addEventListener('transitionend',()=>item.remove(),{once:true});setTimeout(()=>item.remove(),400);};
  const arm=()=>{started=Date.now();timer=setTimeout(leave,remaining);};
  item.addEventListener('pointerenter',()=>{clearTimeout(timer);remaining-=Date.now()-started;});
  item.addEventListener('pointerleave',arm);
  arm();
}

async function downloadFile(path, payload, format) {
  const response = await request(`/api${path}`, {method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(payload)});
  if (!response.ok) {
    const body = await response.json().catch(()=>({}));
    const detail = Array.isArray(body.detail) ? body.detail.map(x=>x.msg).join('; ') : body.detail;
    throw new Error(detail || 'Esportazione non riuscita.');
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href=url;link.download=`vedra-opportunita.${format}`;
  document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

export const downloadExport = (format,dataset,ids) => downloadFile('/export',{format,dataset,ids},format);
export const downloadCatalog = (format,filters) => downloadFile('/catalog/export',{format,filters},format);
