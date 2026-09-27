// Shared by popup and shortcut: read the page the person is looking at and send it to Vedra.
// Nothing is navigated or clicked on their behalf: only the open tab's current HTML is sent.
export async function settings() {
  const {server = 'http://127.0.0.1:8000', token = ''} = await chrome.storage.local.get(['server', 'token']);
  return {server: server.replace(/\/+$/, ''), token};
}

export async function capture(tab) {
  const {server, token} = await settings();
  if (!token) throw new Error('Collega prima l’estensione: incolla il token da Vedra › Impostazioni.');
  if (!/^https?:/.test(tab.url || '')) throw new Error('Apri la pagina di un annuncio.');
  const [{result}] = await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: () => ({url: location.href, html: document.documentElement.outerHTML}),
  });
  let response;
  try {
    response = await fetch(server + '/api/capture', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
      body: JSON.stringify(result),
    });
  } catch {
    throw new Error('Vedra non risponde su ' + server + '. È avviato?');
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Invio non riuscito (' + response.status + ').');
  return {...body, server};
}
