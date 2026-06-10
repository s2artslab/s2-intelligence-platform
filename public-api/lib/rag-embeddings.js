/**
 * Optional Ollama embeddings for hybrid RAG (keyword + cosine).
 */

const fs = require('fs');
const path = require('path');

const OLLAMA_BASE = (process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434').replace(
  /\/$/,
  '',
);
const EMBED_MODEL = process.env.RAG_EMBED_MODEL || 'nomic-embed-text';
const CACHE_PATH =
  process.env.RAG_EMBED_CACHE ||
  path.join(__dirname, '..', 'data', 'rag-embed-cache.json');

let _cache = null;

function loadCache() {
  if (_cache) return _cache;
  try {
    if (fs.existsSync(CACHE_PATH)) {
      _cache = JSON.parse(fs.readFileSync(CACHE_PATH, 'utf8'));
      return _cache;
    }
  } catch {
    /* ignore */
  }
  _cache = {};
  return _cache;
}

function saveCache() {
  try {
    const dir = path.dirname(CACHE_PATH);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(CACHE_PATH, JSON.stringify(_cache, null, 0));
  } catch (e) {
    console.warn('[rag-embed] cache save failed:', e.message);
  }
}

function cacheKey(text) {
  const crypto = require('crypto');
  return crypto.createHash('sha256').update(String(text)).digest('hex').slice(0, 24);
}

function cosine(a, b) {
  if (!a?.length || !b?.length || a.length !== b.length) return 0;
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < a.length; i += 1) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  if (!na || !nb) return 0;
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}

async function embedText(text) {
  const trimmed = String(text || '').trim().slice(0, 8000);
  if (!trimmed) return null;

  const key = cacheKey(trimmed);
  const cache = loadCache();
  if (cache[key]) return cache[key];

  const res = await fetch(`${OLLAMA_BASE}/api/embeddings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: EMBED_MODEL, prompt: trimmed }),
    signal: AbortSignal.timeout(Number(process.env.RAG_EMBED_TIMEOUT_MS || 30000)),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Ollama embed HTTP ${res.status}: ${err.slice(0, 200)}`);
  }

  const data = await res.json();
  const vec = data?.embedding;
  if (!Array.isArray(vec) || !vec.length) {
    throw new Error('Ollama embed returned empty vector');
  }

  cache[key] = vec;
  _cache = cache;
  saveCache();
  return vec;
}

async function embedQuery(text) {
  return embedText(text);
}

function embeddingsEnabled() {
  return process.env.RAG_USE_EMBEDDINGS === 'true' || process.env.RAG_USE_EMBEDDINGS === '1';
}

module.exports = {
  embedText,
  embedQuery,
  cosine,
  embeddingsEnabled,
  EMBED_MODEL,
};
