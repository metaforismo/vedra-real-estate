let csrf = '';
export function setCsrf(value) { csrf = value || ''; }
export async function api(path, options = {}) {
  const {method = 'GET', body, signal} = options;
  const headers = {Accept:'application/json'};
  if (body !== undefined) headers['Content-Type']='application/json';
  if (!['GET','HEAD'].includes(method)) headers['X-CSRF-Token']=csrf;
  const response = await fetch(`/api${path}`, {method, headers, credentials:'same-origin', body:body===undefined?undefined:JSON.stringify(body), signal});
  const result = await response.json().catch(()=>({detail:`Errore HTTP ${response.status}`}));
  if (!response.ok) {
    const message = Array.isArray(result.detail) ? result.detail.map(x=>`${(x.loc || []).slice(1).join('.')}: ${x.msg}`).join('; ') : result.detail;
    const error = new Error(message || `Errore HTTP ${response.status}`);
    error.status = response.status;
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
  item.textContent = message;
  container.append(item);
  setTimeout(()=>item.remove(),error?8500:4500);
}

async function downloadFile(path, payload, format) {
  const response = await fetch(`/api${path}`, {method:'POST',credentials:'same-origin',
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
