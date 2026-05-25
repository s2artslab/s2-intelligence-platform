/**
 * Lightweight collective-knowledge retrieval (keyword overlap).
 * No external vector DB required; extend later with embeddings.
 */

const fs = require('fs');
const path = require('path');

const KNOWLEDGE_DIR =
  process.env.S2_KNOWLEDGE_DIR ||
  path.join(__dirname, '..', 'knowledge');

let _chunks = null;

function tokenize(text) {
  return String(text)
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 2);
}

function loadKnowledgeChunks() {
  if (_chunks !== null) return _chunks;
  _chunks = [];
  if (!fs.existsSync(KNOWLEDGE_DIR)) {
    return _chunks;
  }

  const files = fs.readdirSync(KNOWLEDGE_DIR).filter((f) => /\.(md|txt|json)$/i.test(f));
  for (const file of files) {
    const full = path.join(KNOWLEDGE_DIR, file);
    try {
      const raw = fs.readFileSync(full, 'utf8');
      if (file.endsWith('.json')) {
        const doc = JSON.parse(raw);
        const items = Array.isArray(doc) ? doc : doc.chunks || doc.items || [];
        for (const item of items) {
          const text = item.text || item.content || '';
          if (text.trim()) {
            _chunks.push({
              id: item.id || `${file}:${_chunks.length}`,
              text: text.trim(),
              tags: item.tags || [],
              source: file,
            });
          }
        }
      } else {
        const sections = raw.split(/\n(?=#{1,3}\s)/);
        for (let i = 0; i < sections.length; i++) {
          const text = sections[i].trim();
          if (text.length > 80) {
            _chunks.push({
              id: `${file}:s${i}`,
              text,
              tags: [],
              source: file,
            });
          }
        }
      }
    } catch (e) {
      console.warn(`[rag] skip ${file}: ${e.message}`);
    }
  }
  console.log(`[rag] loaded ${_chunks.length} chunks from ${KNOWLEDGE_DIR}`);
  return _chunks;
}

function scoreChunk(queryTokens, chunk) {
  const chunkTokens = new Set(tokenize(chunk.text));
  let score = 0;
  for (const t of queryTokens) {
    if (chunkTokens.has(t)) score += 1;
  }
  for (const tag of chunk.tags || []) {
    const tagTokens = tokenize(tag);
    for (const t of queryTokens) {
      if (tagTokens.includes(t)) score += 2;
    }
  }
  return score;
}

/**
 * @param {string} query
 * @param {{ limit?: number, maxChars?: number }} opts
 */
function retrieveContext(query, opts = {}) {
  const limit = opts.limit ?? Number(process.env.RAG_LIMIT || 5);
  const maxChars = opts.maxChars ?? Number(process.env.RAG_MAX_CHARS || 3000);
  const chunks = loadKnowledgeChunks();
  if (!chunks.length || !query?.trim()) {
    return { text: '', chunks: [], available: chunks.length > 0 };
  }

  const queryTokens = tokenize(query);
  const ranked = chunks
    .map((c) => ({ chunk: c, score: scoreChunk(queryTokens, c) }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  let total = 0;
  const selected = [];
  for (const { chunk } of ranked) {
    if (total + chunk.text.length > maxChars) break;
    selected.push(chunk);
    total += chunk.text.length;
  }

  const text = selected.map((c) => c.text).join('\n\n');
  return {
    text,
    chunks: selected.map((c) => ({ id: c.id, source: c.source })),
    available: true,
  };
}

function ragStatus() {
  const chunks = loadKnowledgeChunks();
  return {
    available: chunks.length > 0,
    chunkCount: chunks.length,
    knowledgeDir: KNOWLEDGE_DIR,
  };
}

module.exports = { retrieveContext, ragStatus, loadKnowledgeChunks };
