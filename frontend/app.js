// ── State ──────────────────────────────────────────────────────────────────────
const API = 'http://localhost:8000';
let state = {
  llmModel: 'llama3',
  embedModel: 'nomic-embed-text',
  nResults: 5,
  docFilter: null,      // null = all docs
  documents: [],
  ollamaOnline: false,
  chatHistory: [],
  isStreaming: false,
};

// ── Init ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  checkOllamaStatus();
  loadDocuments();

  // Auto-resize textarea
  const input = document.getElementById('chat-input');
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 140) + 'px';
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});

// ── Navigation ─────────────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');

  if (name === 'documents') loadDocuments();
  if (name === 'settings') populateSettingsUI();
}

// ── Settings ───────────────────────────────────────────────────────────────────
function loadSettings() {
  const saved = JSON.parse(localStorage.getItem('vault-settings') || '{}');
  state.llmModel    = saved.llmModel    || 'llama3';
  state.embedModel  = saved.embedModel  || 'nomic-embed-text';
  state.nResults    = saved.nResults    || 5;
}

function saveSettings() {
  state.llmModel   = document.getElementById('llm-input').value.trim()   || 'llama3';
  state.embedModel = document.getElementById('embed-input').value.trim() || 'nomic-embed-text';
  state.nResults   = parseInt(document.getElementById('n-results').value) || 5;
  localStorage.setItem('vault-settings', JSON.stringify({
    llmModel: state.llmModel,
    embedModel: state.embedModel,
    nResults: state.nResults,
  }));
  toast('Settings saved!', 'success');
}

function populateSettingsUI() {
  document.getElementById('llm-input').value    = state.llmModel;
  document.getElementById('embed-input').value  = state.embedModel;
  document.getElementById('n-results').value    = state.nResults;
  document.getElementById('n-results-label').textContent = state.nResults;
}

// ── Ollama Status ──────────────────────────────────────────────────────────────
async function checkOllamaStatus() {
  const dot   = document.getElementById('ollama-dot');
  const label = document.getElementById('ollama-label');
  const detail = document.getElementById('ollama-detail');
  try {
    const res  = await fetch(`${API}/ollama/status`);
    const data = await res.json();
    state.ollamaOnline = data.running;
    if (data.running) {
      dot.className   = 'status-dot online';
      label.textContent = `Ollama online`;
      if (detail) {
        detail.innerHTML = `✅ Ollama is running. <strong>${data.models.length}</strong> model(s) available.`;
        renderModelChips(data.models);
      }
    } else {
      dot.className   = 'status-dot offline';
      label.textContent = 'Ollama offline';
      if (detail) detail.innerHTML = '❌ Ollama is not running. <a href="https://ollama.com" target="_blank" style="color:var(--accent)">Install & start Ollama</a>, then pull a model:<br><br><code style="font-family:JetBrains Mono,monospace;color:var(--accent-2)">ollama pull llama3<br>ollama pull nomic-embed-text</code>';
    }
  } catch {
    dot.className   = 'status-dot offline';
    label.textContent = 'Backend offline';
    if (detail) detail.textContent = '❌ Cannot reach backend at http://localhost:8000. Start the Python server.';
  }
}

function renderModelChips(models) {
  const list = document.getElementById('llm-model-list');
  if (!list) return;
  list.innerHTML = '';
  models.forEach(m => {
    const chip = document.createElement('div');
    chip.className = 'model-chip' + (m === state.llmModel ? ' active' : '');
    chip.textContent = m;
    chip.onclick = () => {
      document.querySelectorAll('.model-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      document.getElementById('llm-input').value = m;
    };
    list.appendChild(chip);
  });
}

// ── Documents ──────────────────────────────────────────────────────────────────
async function loadDocuments() {
  try {
    const res  = await fetch(`${API}/documents`);
    const data = await res.json();
    state.documents = data.documents || [];
    renderDocGrid();
    renderChatFilters();
    updateVaultStat();
  } catch {
    // Backend not yet running — show empty state gracefully
    state.documents = [];
    renderDocGrid();
  }
}

function updateVaultStat() {
  const el = document.getElementById('vault-stat');
  if (el) el.textContent = `${state.documents.length} document${state.documents.length !== 1 ? 's' : ''} in vault`;
}

function renderDocGrid() {
  const grid  = document.getElementById('docs-grid');
  const empty = document.getElementById('docs-empty');

  // Remove all doc cards (keep empty state)
  grid.querySelectorAll('.doc-card').forEach(c => c.remove());

  if (!state.documents.length) {
    empty.style.display = 'flex';
    return;
  }
  empty.style.display = 'none';

  state.documents.forEach(doc => {
    const card = createDocCard(doc);
    grid.appendChild(card);
  });
}

const EXT_ICONS = { pdf:'📕', docx:'📘', txt:'📄', md:'📝', markdown:'📝', html:'🌐', htm:'🌐' };
const EXT_COLORS = {
  pdf:'rgba(239,68,68,.15)',docx:'rgba(59,130,246,.15)',
  txt:'rgba(16,185,129,.15)',md:'rgba(245,158,11,.15)',
  html:'rgba(139,92,246,.15)'
};

function createDocCard(doc) {
  const ext  = (doc.ext || '.txt').replace('.', '').toLowerCase();
  const icon = EXT_ICONS[ext]  || '📄';
  const color= EXT_COLORS[ext] || 'rgba(255,255,255,.08)';
  const size = formatBytes(doc.size || 0);

  const card = document.createElement('div');
  card.className = 'doc-card';
  card.id = 'doc-card-' + doc.id;
  card.innerHTML = `
    <div class="doc-card-header">
      <div class="doc-file-icon" style="background:${color}">${icon}</div>
      <div class="doc-info">
        <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
        <div class="doc-meta">${size} · ${new Date(doc.uploaded || Date.now()).toLocaleDateString()}</div>
      </div>
    </div>
    <div class="doc-footer">
      <span class="chunk-badge">🧩 ${doc.chunk_count} chunks</span>
      <div style="display:flex;gap:8px">
        <button class="btn btn-ghost btn-sm" onclick="chatWithDoc('${doc.filename}')">💬 Chat</button>
        <button class="btn btn-danger btn-sm" onclick="deleteDoc('${doc.id}','${doc.filename}')">🗑</button>
      </div>
    </div>`;
  return card;
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
  return (bytes/(1024*1024)).toFixed(1) + ' MB';
}

function chatWithDoc(filename) {
  // Switch to chat page and set filter
  showPage('chat');
  const filterEl = document.querySelector(`[data-filename="${CSS.escape(filename)}"]`);
  setDocFilter(filename, filterEl || document.getElementById('filter-all'));
}

async function deleteDoc(id, filename) {
  if (!confirm(`Remove "${filename}" from the vault?`)) return;
  try {
    const res = await fetch(`${API}/documents/${id}`, { method: 'DELETE' });
    const data = await res.json();
    toast(data.message || 'Removed.', 'success');
    loadDocuments();
  } catch (e) {
    toast('Failed to delete document.', 'error');
  }
}

// ── Upload ─────────────────────────────────────────────────────────────────────
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('upload-zone').classList.add('drag-over');
}
function handleDragLeave(e) {
  document.getElementById('upload-zone').classList.remove('drag-over');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('upload-zone').classList.remove('drag-over');
  const files = Array.from(e.dataTransfer.files);
  uploadFiles(files);
}
function handleFileSelect(e) {
  uploadFiles(Array.from(e.target.files));
  e.target.value = '';
}

async function uploadFiles(files) {
  if (!files.length) return;
  const progressWrap = document.getElementById('progress-wrap');
  const progressFill = document.getElementById('progress-fill');
  const progressLabel = document.getElementById('progress-label');
  progressWrap.classList.add('show');

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const pct  = Math.round(((i) / files.length) * 100);
    progressFill.style.width  = pct + '%';
    progressLabel.textContent = `Processing ${file.name} (${i+1}/${files.length})…`;

    const form = new FormData();
    form.append('file', file);
    form.append('embed_model', state.embedModel);

    try {
      const res  = await fetch(`${API}/documents/upload`, { method: 'POST', body: form });
      const data = await res.json();
      if (res.ok) {
        toast(`✅ "${file.name}" indexed — ${data.chunk_count} chunks`, 'success');
      } else {
        toast(`❌ ${data.detail || 'Upload failed for ' + file.name}`, 'error');
      }
    } catch {
      toast(`❌ Could not reach backend. Is the server running?`, 'error');
    }
  }

  progressFill.style.width  = '100%';
  progressLabel.textContent = 'Done!';
  setTimeout(() => {
    progressWrap.classList.remove('show');
    progressFill.style.width = '0%';
  }, 1200);

  loadDocuments();
}

// ── Chat Filters ───────────────────────────────────────────────────────────────
function renderChatFilters() {
  const container = document.getElementById('chat-doc-filters');
  if (!container) return;
  container.innerHTML = '';
  state.documents.forEach(doc => {
    const ext  = (doc.ext || '').replace('.','').toLowerCase();
    const icon = EXT_ICONS[ext] || '📄';
    const item = document.createElement('div');
    item.className = 'filter-item';
    item.dataset.filename = doc.filename;
    item.innerHTML = `<span class="filter-icon">${icon}</span>${doc.filename}`;
    item.onclick = () => setDocFilter(doc.filename, item);
    container.appendChild(item);
  });
}

function setDocFilter(filename, el) {
  state.docFilter = filename;
  document.querySelectorAll('.filter-item').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');
  const label = document.getElementById('chat-doc-label');
  label.textContent = filename ? `Searching in: ${filename}` : 'Searching across all documents';
}

// ── Chat ───────────────────────────────────────────────────────────────────────
async function sendMessage() {
  if (state.isStreaming) return;
  const input = document.getElementById('chat-input');
  const query = input.value.trim();
  if (!query) return;

  // Clear welcome screen on first message
  document.getElementById('chat-welcome').style.display = 'none';

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;

  appendMessage('user', query);
  const aiMsg = appendMessage('ai', '');
  const dotsEl = document.createElement('div');
  dotsEl.className = 'typing-dots';
  dotsEl.innerHTML = '<span></span><span></span><span></span>';
  aiMsg.querySelector('.msg-text').appendChild(dotsEl);

  state.isStreaming = true;
  let fullText = '';

  try {
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        llm_model:    state.llmModel,
        embed_model:  state.embedModel,
        n_results:    state.nResults,
        source_filter: state.docFilter,
        stream:       true,
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Server error');
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    dotsEl.remove();
    const textEl = aiMsg.querySelector('.msg-text');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      fullText += chunk;
      textEl.textContent = fullText;
      scrollChatBottom();
    }
  } catch (e) {
    dotsEl.remove();
    aiMsg.querySelector('.msg-text').textContent = `⚠️ Error: ${e.message}`;
    toast(e.message, 'error');
  }

  state.isStreaming = false;
  document.getElementById('send-btn').disabled = false;
  input.focus();
  scrollChatBottom();
}

function appendMessage(role, text) {
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `msg msg-${role}`;
  const avatar = role === 'user' ? '👤' : '🤖';
  const label  = role === 'user' ? 'You' : 'AI Vault';
  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-body">
      <div class="msg-role">${label}</div>
      <div class="msg-text">${text}</div>
    </div>`;
  messages.appendChild(div);
  scrollChatBottom();
  return div;
}

function scrollChatBottom() {
  const el = document.getElementById('chat-messages');
  el.scrollTop = el.scrollHeight;
}

function clearChat() {
  const messages = document.getElementById('chat-messages');
  messages.querySelectorAll('.msg').forEach(m => m.remove());
  document.getElementById('chat-welcome').style.display = 'flex';
}

// ── Toasts ─────────────────────────────────────────────────────────────────────
function toast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  el.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'slideOut .3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}
