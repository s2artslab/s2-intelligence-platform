/**
 * Layer 5 — Philosophical retrieval (keyword + tags + tension boost).
 */

const { loadAllChunks } = require('./retrieval-index');

function tokenize(text) {
  return String(text)
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 2);
}

function scoreChunk(queryTokens, chunk, activeTensionIds = []) {
  const chunkTokens = new Set(tokenize(chunk.text));
  let score = 0;
  for (const t of queryTokens) {
    if (chunkTokens.has(t)) score += 1;
  }
  for (const tag of chunk.concept_tags || []) {
    const tagTokens = tokenize(tag);
    for (const t of queryTokens) {
      if (tagTokens.includes(t)) score += 2;
    }
  }
  for (const link of chunk.symbolic_links || []) {
    for (const t of queryTokens) {
      if (tokenize(link).includes(t)) score += 2;
    }
  }
  if (chunk.layer === 'canon') score += 1;
  for (const tid of chunk.tension_ids || []) {
    if (activeTensionIds.includes(tid)) score += 4;
  }
  for (const u of chunk.unresolved_with || []) {
    if (activeTensionIds.includes(u)) score += 3;
  }
  return score;
}

/**
 * @param {string} query
 * @param {{ limit?: number, maxChars?: number, cadence?: string, tensionIds?: string[] }} opts
 */
function retrieveContext(query, opts = {}) {
  const limit = opts.limit ?? Number(process.env.RAG_LIMIT || 5);
  const maxChars = opts.maxChars ?? Number(process.env.RAG_MAX_CHARS || 3000);
  const chunks = loadAllChunks();
  const tensionIds = opts.tensionIds || [];

  if (!chunks.length || !query?.trim()) {
    return { text: '', chunks: [], available: chunks.length > 0 };
  }

  const queryTokens = tokenize(query);
  let ranked = chunks
    .map((c) => ({
      chunk: c,
      score: scoreChunk(queryTokens, c, tensionIds),
    }))
    .filter((r) => r.score > 0);

  if (opts.egregoreId) {
    const eg = String(opts.egregoreId).toLowerCase();
    ranked = ranked.map((r) => ({
      ...r,
      score:
        r.score +
        ((r.chunk.concept_tags || []).some((t) => String(t).toLowerCase().includes(eg)) ? 3 : 0) +
        (String(r.chunk.source || '').toLowerCase().includes(eg) ? 2 : 0),
    }));
  }

  if (opts.cadence) {
    ranked = ranked.map((r) => ({
      ...r,
      score:
        r.score +
        (r.chunk.cadence === opts.cadence ? 2 : 0) +
        (r.chunk.layer === 'canon' && opts.cadence === 'philosophy' ? 1 : 0),
    }));
  }

  ranked.sort((a, b) => b.score - a.score);
  ranked = ranked.slice(0, limit);

  let total = 0;
  const selected = [];
  for (const { chunk } of ranked) {
    if (total + chunk.text.length > maxChars) break;
    selected.push(chunk);
    total += chunk.text.length;
  }

  const text = selected
    .map((c) => {
      const role = c.discourse_role ? `[${c.discourse_role}] ` : '';
      return `${role}${c.text}`;
    })
    .join('\n\n');

  return {
    text,
    chunks: selected.map((c) => ({
      id: c.id,
      source: c.source,
      layer: c.layer,
      cadence: c.cadence,
    })),
    available: true,
  };
}

function ragStatus() {
  const { indexStatus } = require('./retrieval-index');
  const idx = indexStatus();
  return {
    available: idx.chunkCount > 0,
    chunkCount: idx.chunkCount,
    byLayer: idx.byLayer,
    knowledgeDir: idx.knowledgeDir,
    canonDir: idx.canonDir,
    discourseIndex: idx.discourseIndex,
    prebuiltIndex: idx.prebuilt,
  };
}

/** @deprecated use loadAllChunks */
function loadKnowledgeChunks() {
  return loadAllChunks();
}

module.exports = { retrieveContext, ragStatus, loadKnowledgeChunks };
