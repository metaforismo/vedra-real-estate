import {capture, resultsSummary} from './capture.js';

// Keyboard shortcut: same capture as the popup, result shown on the toolbar badge.
chrome.commands.onCommand.addListener(async (command, tab) => {
  if (command !== 'capture-page' || !tab) return;
  chrome.action.setBadgeText({tabId: tab.id, text: '…'});
  try {
    const result = await capture(tab);
    chrome.action.setBadgeBackgroundColor({tabId: tab.id, color: '#287361'});
    const results = result.kind === 'results';
    chrome.action.setBadgeText({tabId: tab.id, text: results ? String(Math.min(result.cards, 999)) : result.created ? 'OK' : '='});
    chrome.action.setTitle({tabId: tab.id, title: 'Vedra: ' + (results ? resultsSummary(result) : result.title)});
  } catch (error) {
    chrome.action.setBadgeBackgroundColor({tabId: tab.id, color: '#ae4654'});
    chrome.action.setBadgeText({tabId: tab.id, text: '!'});
    chrome.action.setTitle({tabId: tab.id, title: 'Vedra: ' + error.message});
  }
});

// Exposed for the automated extension test only; the UI uses the popup and the shortcut.
globalThis.vedraCapture = capture;
