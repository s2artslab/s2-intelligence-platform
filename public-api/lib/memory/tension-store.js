/**
 * Layer 4 — Tension memory (temporal self). JSON persistence per owner scope.
 */

const fs = require('fs');
const path = require('path');

const STORE_DIR =
  process.env.S2_TENSION_STORE || path.join(__dirname, '..', '..', 'data', 'tensions');

function ensureDir() {
  if (!fs.existsSync(STORE_DIR)) {
    fs.mkdirSync(STORE_DIR, { recursive: true });
  }
}

function safeOwnerId(ownerId) {
  const id = String(ownerId || 'global').trim() || 'global';
  return id.replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 128);
}

function storePath(ownerId) {
  return path.join(STORE_DIR, `${safeOwnerId(ownerId)}.json`);
}

function emptyStore() {
  return {
    tensions: [],
    trajectories: [],
    episodic: [],
    updated_at: new Date().toISOString(),
  };
}

function loadStore(ownerId) {
  ensureDir();
  const file = storePath(ownerId);
  if (!fs.existsSync(file)) return emptyStore();
  try {
    return { ...emptyStore(), ...JSON.parse(fs.readFileSync(file, 'utf8')) };
  } catch {
    return emptyStore();
  }
}

function saveStore(ownerId, data) {
  ensureDir();
  data.updated_at = new Date().toISOString();
  fs.writeFileSync(storePath(ownerId), JSON.stringify(data, null, 2), 'utf8');
  return data;
}

function listOpenTensions(ownerId, opts = {}) {
  const store = loadStore(ownerId);
  const limit = opts.limit ?? 8;
  return store.tensions
    .filter((t) => t.status === 'open' || t.status === 'deepened')
    .sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)))
    .slice(0, limit);
}

function upsertTension(ownerId, record) {
  const store = loadStore(ownerId);
  const now = new Date().toISOString();
  const id = record.id || `tension.${Date.now()}`;
  const idx = store.tensions.findIndex((t) => t.id === id);
  const entry = {
    id,
    statement: String(record.statement || '').trim(),
    status: record.status || 'open',
    linked_canon: record.linked_canon || [],
    linked_threads: record.linked_threads || [],
    trajectory_id: record.trajectory_id || null,
    updated_at: now,
    reflection_notes: record.reflection_notes || [],
  };
  if (!entry.statement) throw new Error('tension statement required');
  if (idx >= 0) {
    const prev = store.tensions[idx];
    entry.reflection_notes = [
      ...(prev.reflection_notes || []),
      ...(record.append_note
        ? [{ at: now, note: String(record.append_note) }]
        : []),
    ];
    store.tensions[idx] = { ...prev, ...entry };
  } else {
    store.tensions.push(entry);
  }
  saveStore(ownerId, store);
  return entry;
}

function appendEpisodic(ownerId, note) {
  const store = loadStore(ownerId);
  store.episodic.push({
    at: new Date().toISOString(),
    note: String(note).slice(0, 2000),
  });
  if (store.episodic.length > 50) {
    store.episodic = store.episodic.slice(-50);
  }
  saveStore(ownerId, store);
}

function tensionPromptBlock(ownerId, opts = {}) {
  const open = listOpenTensions(ownerId, opts);
  if (!open.length) return { text: '', tensionIds: [] };
  const maxChars = opts.maxChars ?? Number(process.env.TENSION_MAX_CHARS || 800);
  const lines = [];
  let total = 0;
  const tensionIds = [];
  for (const t of open) {
    const line = `• [${t.id}] ${t.statement}`;
    if (total + line.length > maxChars) break;
    lines.push(line);
    tensionIds.push(t.id);
    total += line.length;
  }
  return {
    text: lines.join('\n'),
    tensionIds,
  };
}

function memoryStatus() {
  ensureDir();
  const files = fs.existsSync(STORE_DIR)
    ? fs.readdirSync(STORE_DIR).filter((f) => f.endsWith('.json'))
    : [];
  return {
    available: true,
    storeDir: STORE_DIR,
    ownerFiles: files.length,
  };
}

module.exports = {
  STORE_DIR,
  loadStore,
  listOpenTensions,
  upsertTension,
  appendEpisodic,
  tensionPromptBlock,
  memoryStatus,
};
