/**
 * Layer 5 — Retrieval (keyword + optional embeddings) with namespace filtering.
 */

const { loadAllChunks } = require('./retrieval-index');
const { chunkMatchesNamespaces } = require('./rag-namespaces');
const { embedQuery, cosine, embeddingsEnabled } = require('./rag-embeddings');

function tokenize(text) {
  return String(text)
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 2);
}

function scoreChunkKeyword(queryTokens, chunk, activeTensionIds = []) {
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
  for (const ns of chunk.namespaces || []) {
    if (queryTokens.some((t) => ns.includes(t))) score += 1;
  }
  return score;
}

async function scoreChunkHybrid(queryTokens, queryEmbed, chunk, activeTensionIds) {
  let score = scoreChunkKeyword(queryTokens, chunk, activeTensionIds);
  if (queryEmbed && Array.isArray(chunk.embedding) && chunk.embedding.length) {
    const sim = cosine(queryEmbed, chunk.embedding);
    score += sim * Number(process.env.RAG_EMBED_WEIGHT || 8);
  }
  return score;
}

/**
 * @param {string} query
 * @param {{ limit?: number, maxChars?: number, cadence?: string, tensionIds?: string[], egregoreId?: string, namespaces?: string[], ownerId?: string, matterId?: string }} opts
 */
async function retrieveContext(query, opts = {}) {
  const limit = opts.limit ?? Number(process.env.RAG_LIMIT || 5);
  const maxChars = opts.maxChars ?? Number(process.env.RAG_MAX_CHARS || 3000);
  const namespaces = opts.namespaces || [];
  const tensionIds = opts.tensionIds || [];

  const chunks = loadAllChunks({
    ownerId: opts.ownerId,
    matterId: opts.matterId,
  });

  if (!chunks.length || !query?.trim()) {
    return { text: '', chunks: [], available: chunks.length > 0, mode: 'none' };
  }

  const queryTokens = tokenize(query);
  let pool = chunks.filter((c) => chunkMatchesNamespaces(c, namespaces));

  if (opts.matterId) {
    pool = pool.filter(
      (c) =>
        c.layer !== 'private' ||
        c.matter_id === opts.matterId ||
        (c.namespaces || []).includes(`matter:${opts.matterId}`),
    );
  }

  let queryEmbed = null;
  let mode = 'keyword';
  if (embeddingsEnabled()) {
    try {
      queryEmbed = await embedQuery(query);
      mode = 'hybrid';
    } catch (e) {
      console.warn('[rag] embeddings unavailable, keyword only:', e.message);
    }
  }

  let ranked = [];
  for (const chunk of pool) {
    const score = await scoreChunkHybrid(queryTokens, queryEmbed, chunk, tensionIds);
    if (score > 0) ranked.push({ chunk, score });
  }

  if (opts.egregoreId) {
    const eg = String(opts.egregoreId).toLowerCase();
    ranked = ranked.map((r) => ({
      ...r,
      score:
        r.score +
        ((r.chunk.concept_tags || []).some((t) => String(t).toLowerCase().includes(eg))
          ? 3
          : 0) +
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
      const ns = c.namespaces?.length ? `[${c.namespaces.join(',')}] ` : '';
      return `${ns}${role}${c.text}`;
    })
    .join('\n\n');

  return {
    text,
    chunks: selected.map((c) => ({
      id: c.id,
      source: c.source,
      layer: c.layer,
      cadence: c.cadence,
      namespaces: c.namespaces,
    })),
    available: true,
    mode,
    namespaces,
  };
}

function ragStatus() {
  const { indexStatus } = require('./retrieval-index');
  const idx = indexStatus();
  return {
    available: idx.chunkCount > 0,
    chunkCount: idx.chunkCount,
    byLayer: idx.byLayer,
    byNamespace: idx.byNamespace,
    knowledgeDir: idx.knowledgeDir,
    canonDir: idx.canonDir,
    discourseIndex: idx.discourseIndex,
    prebuiltIndex: idx.prebuilt,
    embeddings: embeddingsEnabled(),
    embedModel: process.env.RAG_EMBED_MODEL || 'nomic-embed-text',
  };
}

/** Sync wrapper for callers not yet async */
function retrieveContextSync(query, opts = {}) {
  return retrieveContext(query, opts);
}

module.exports = {
  retrieveContext,
  retrieveContextSync,
  ragStatus,
  loadKnowledgeChunks: () => loadAllChunks(),
};
