'use strict';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const unconfiguredEl = document.getElementById('unconfigured');
const pageInfoEl     = document.getElementById('pageInfo');
const pageTitleEl    = document.getElementById('pageTitle');
const pageUrlEl      = document.getElementById('pageUrl');
const saveBtn        = document.getElementById('saveBtn');
const statusEl       = document.getElementById('status');
const optionsBtn     = document.getElementById('optionsBtn');
const openSettingsBtn = document.getElementById('openSettingsBtn');

// ── State ─────────────────────────────────────────────────────────────────────
let apiUrl   = '';
let apiToken = '';
let tabUrl   = '';

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const settings = await getSettings();
  apiUrl   = settings.apiUrl   || '';
  apiToken = settings.apiToken || '';

  if (!apiUrl || !apiToken) {
    showUnconfigured();
    return;
  }

  const tab = await getCurrentTab();
  tabUrl = tab.url || '';
  pageTitleEl.textContent = tab.title || tabUrl;
  pageUrlEl.textContent   = tabUrl;

  pageInfoEl.style.display = 'block';
  saveBtn.disabled = false;
});

// ── Options button (gear) ─────────────────────────────────────────────────────
optionsBtn.addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});

// ── "Open Settings" button (unconfigured state) ───────────────────────────────
openSettingsBtn.addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});

// ── Save button ───────────────────────────────────────────────────────────────
saveBtn.addEventListener('click', async () => {
  saveBtn.disabled = true;
  showStatus('Saving…', 'saving');

  try {
    const response = await fetch(`${apiUrl}/api/v1/articles`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url: tabUrl }),
    });

    if (response.status === 201) {
      showStatus('✅ Saved! Recap AI is classifying it.', 'success');
      // Leave button disabled — article already queued, no need to save again.
      return;
    }

    // Try to get a helpful error message from the JSON body
    let errMsg = `Server error (${response.status})`;
    try {
      const body = await response.json();
      if (body.error) errMsg = body.error;
    } catch (_) { /* ignore parse errors */ }

    if (response.status === 401) {
      errMsg = 'Invalid API token. Update it in settings.';
    } else if (response.status === 400 && errMsg === `Server error (${response.status})`) {
      errMsg = 'Bad request — check your server URL in settings.';
    }

    showStatus('❌ ' + errMsg, 'error');
    saveBtn.disabled = false;

  } catch (err) {
    // Network-level failure (offline, wrong URL, CORS, etc.)
    showStatus('❌ Could not reach RecapAI. Check your server URL in settings.', 'error');
    saveBtn.disabled = false;
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(['apiUrl', 'apiToken'], resolve);
  });
}

function getCurrentTab() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0] || {});
    });
  });
}

function showUnconfigured() {
  unconfiguredEl.style.display = 'block';
  pageInfoEl.style.display     = 'none';
  saveBtn.style.display        = 'none';
}

function showStatus(msg, type) {
  statusEl.textContent = msg;
  statusEl.className   = type;
}
