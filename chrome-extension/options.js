'use strict';

const apiUrlInput  = document.getElementById('apiUrl');
const apiTokenInput = document.getElementById('apiToken');
const toggleBtn    = document.getElementById('toggleToken');
const saveBtn      = document.getElementById('saveBtn');
const statusEl     = document.getElementById('status');

// ── Load saved settings on page open ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  chrome.storage.sync.get(['apiUrl', 'apiToken'], (result) => {
    if (result.apiUrl)   apiUrlInput.value   = result.apiUrl;
    if (result.apiToken) apiTokenInput.value = result.apiToken;
  });
});

// ── Show / Hide token ────────────────────────────────────────────────────────
toggleBtn.addEventListener('click', () => {
  const isPassword = apiTokenInput.type === 'password';
  apiTokenInput.type  = isPassword ? 'text' : 'password';
  toggleBtn.textContent = isPassword ? 'Hide' : 'Show';
});

// ── Save settings ────────────────────────────────────────────────────────────
saveBtn.addEventListener('click', () => {
  const apiUrl   = apiUrlInput.value.trim().replace(/\/$/, ''); // strip trailing slash
  const apiToken = apiTokenInput.value.trim();

  if (!apiUrl) {
    showStatus('Please enter your RecapAI server URL.', 'error');
    return;
  }
  if (!apiToken) {
    showStatus('Please enter your API token.', 'error');
    return;
  }

  chrome.storage.sync.set({ apiUrl, apiToken }, () => {
    if (chrome.runtime.lastError) {
      showStatus('Error saving: ' + chrome.runtime.lastError.message, 'error');
    } else {
      showStatus('Settings saved!', 'success');
    }
  });
});

function showStatus(msg, type) {
  statusEl.textContent = msg;
  statusEl.className   = type;
}
