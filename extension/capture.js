// Shared by popup and shortcut: read the page the person is looking at and send it to Vedra.
// Nothing is navigated or clicked on their behalf: only the open tab's current HTML is sent.
export async function settings() {
  const {server = 'http://127.0.0.1:8000', token = ''} = await chrome.storage.local.get(['server', 'token']);
  return {server: server.replace(/\/+$/, ''), token};
}

// A portal results page is imported card by card: "14 annunci · 9 nuovi · 5 aggiornati · 2 senza prezzo".
export function resultsSummary(r) {
  const n = (value, one, many) => `${value} ${value === 1 ? one : many}`;
  return [n(r.cards, 'annuncio', 'annunci'), r.created && n(r.created, 'nuovo', 'nuovi'), r.updated && n(r.updated, 'aggiornato', 'aggiornati'),
    r.unchanged && `${r.unchanged} già ${r.unchanged === 1 ? 'presente' : 'presenti'}`, r.no_price && `${r.no_price} senza prezzo`].filter(Boolean).join(' · ');
}

export async function capture(tab) {
  const {server, token} = await settings();
  if (!token) throw new Error('Collega prima l’estensione: incolla il token da Vedra › Impostazioni.');
  if (!/^https?:/.test(tab.url || '')) throw new Error('Apri un annuncio o una pagina di risultati.');
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
