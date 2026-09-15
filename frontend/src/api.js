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
  const item = document.createElement('div');
  item.className = `toast ${error?'error':''}`;
  item.setAttribute('role',error?'alert':'status');
  item.textContent = message;
  document.getElementById('toasts').append(item);
  setTimeout(()=>item.remove(),error?8500:4500);
}

export async function downloadExport(format, dataset, ids) {
  const response = await fetch('/api/export', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({format,dataset,ids})});
  if (!response.ok) {
    const body = await response.json().catch(()=>({}));
    throw new Error(body.detail || 'Esportazione non riuscita.');
  }
  const blob=await response.blob();
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;link.download=`vedra-opportunita.${format}`;
  document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
