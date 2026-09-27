import {capture, settings} from './capture.js';

const $ = id => document.getElementById(id);
const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
const current = await settings();
$('server').value = current.server;
$('token').value = current.token;
$('page').textContent = tab?.url ? new URL(tab.url).hostname.replace(/^www\./, '') + ' · ' + (tab.title || '').slice(0, 80) : 'Nessuna pagina';
if (!current.token) $('setup').open = true;

$('save').addEventListener('click', async () => {
  const server = $('server').value.trim() || 'http://127.0.0.1:8000';
  // A remote Vedra needs an explicit host permission; local installs are covered by the manifest.
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(server)) {
    const granted = await chrome.permissions.request({origins: [new URL(server).origin + '/*']});
    if (!granted) return show('Permesso negato per ' + server, true);
  }
  await chrome.storage.local.set({server, token: $('token').value.trim()});
  $('setup').open = false;
  show('Collegamento salvato.');
});

$('send').addEventListener('click', async () => {
  $('send').disabled = true;
  $('send').textContent = 'Lettura in corso…';
  try {
    const r = await capture(tab);
    const price = r.price == null ? 'prezzo non indicato' : r.currency === 'EUR'
      ? new Intl.NumberFormat('it-IT', {style: 'currency', currency: 'EUR', maximumFractionDigits: 0}).format(r.price)
      : new Intl.NumberFormat('it-IT').format(r.price);
    show(`<strong>${r.created ? 'Aggiunto' : 'Aggiornato'}</strong> ${escapeHtml(r.title)}<br><span>${escapeHtml([r.city, r.zone].filter(Boolean).join(' · '))} · ${price}</span><br><a href="${r.server}/#properties" target="_blank">Apri in Vedra</a>`, false, true);
  } catch (error) {
    show(error.message, true);
  } finally {
    $('send').disabled = false;
    $('send').textContent = 'Invia a Vedra';
  }
});

function show(message, error = false, html = false) {
  const node = $('result');
  node.className = error ? 'error' : 'ok';
  if (html) node.innerHTML = message; else node.textContent = message;
}
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}
