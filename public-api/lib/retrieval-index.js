/**
 * Layer 5 — Unified retrieval index (canon + knowledge + discourse + product namespaces).
 */

const fs = require('fs');
const path = require('path');
const { loadCanonEntries, CANON_DIR } = require('./canon');

const KNOWLEDGE_DIR =
  process.env.S2_KNOWLEDGE_DIR || path.join(__dirname, '..', 'knowledge');

const DISCOURSE_INDEX =
  process.env.S2_DISCOURSE_INDEX ||
  path.join(__dirname, '..', 'data', 'discourse-index.json');

const RETRIEVAL_INDEX =
  process.env.S2_RETRIEVAL_INDEX ||
  path.join(__dirname, '..', 'data', 'retrieval-index.json');

const PRIVATE_INDEX_DIR =
  process.env.S2_PRIVATE_RAG_DIR || path.join(__dirname, '..', 'data', 'private-rag');

let _chunks = null;

function loadKnowledgeMeta() {
  const metaPath = path.join(KNOWLEDGE_DIR, 'meta.json');
  if (!fs.existsSync(metaPath)) return {};
  try {
    return JSON.parse(fs.readFileSync(metaPath, 'utf8'));
  } catch {
    return {};
  }
}

function normalizeChunk(raw, defaults = {}) {
  const ns = raw.namespaces || raw.namespace || defaults.namespaces || [];
  const namespaces = Array.isArray(ns) ? ns : [ns].filter(Boolean);
  return {
    id: raw.id || defaults.id,
    text: String(raw.text || raw.content || '').trim(),
    layer: raw.layer || defaults.layer || 'knowledge',
    cadence: raw.cadence || defaults.cadence,
    concept_tags: raw.concept_tags || raw.tags || [],
    symbolic_links: raw.symbolic_links || [],
    discourse_role: raw.discourse_role,
    contradicts: raw.contradicts || [],
    unresolved_with: raw.unresolved_with || [],
    tension_ids: raw.tension_ids || [],
    source: raw.source || defaults.source,
    namespaces,
    owner_id: raw.owner_id || defaults.owner_id || null,
    matter_id: raw.matter_id || defaults.matter_id || null,
  };
}

function walkKnowledgeFiles(dir, acc = []) {
  if (!fs.existsSync(dir)) return acc;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkKnowledgeFiles(full, acc);
    } else if (/\.(md|txt|json)$/i.test(entry.name) && entry.name !== 'meta.json') {
      acc.push(full);
    }
  }
  return acc;
}

function namespacesForPath(filePath, fileMeta = {}) {
  if (fileMeta.namespaces) return fileMeta.namespaces;
  const rel = path.relative(KNOWLEDGE_DIR, filePath).replace(/\\/g, '/');
  const parts = rel.split('/');
  if (parts[0] === 'products' && parts[1]) {
    const productId = parts[1].replace(/\.(md|txt|json)$/i, '');
    return ['s2-canon', `product:${productId}`];
  }
  if (fileMeta.namespace) return [fileMeta.namespace];
  return fileMeta.namespaces || ['s2-canon', 'community'];
}

function loadFileChunks(full, fileMeta = {}) {
  const chunks = [];
  const file = path.basename(full);
  const rel = path.relative(KNOWLEDGE_DIR, full).replace(/\\/g, '/');
  const namespaces = namespacesForPath(full, fileMeta);

  try {
    const raw = fs.readFileSync(full, 'utf8');
    if (file.endsWith('.json')) {
      const doc = JSON.parse(raw);
      const items = Array.isArray(doc) ? doc : doc.chunks || doc.items || [];
      for (const item of items) {
        const c = normalizeChunk(item, {
          id: item.id || `${rel}:${chunks.length}`,
          source: rel,
          layer: 'knowledge',
          namespaces: item.namespaces || namespaces,
          ...fileMeta,
        });
        if (c.text) chunks.push(c);
      }
    } else {
      const sections = raw.split(/\n(?=#{1,3}\s)/);
      for (let i = 0; i < sections.length; i += 1) {
        const text = sections[i].trim();
        if (text.length > 80) {
          chunks.push(
            normalizeChunk(
              {
                id: `${rel}:s${i}`,
                text,
                source: rel,
                namespaces,
              },
              { layer: 'knowledge', ...fileMeta },
            ),
          );
        }
      }
    }
  } catch (e) {
    console.warn(`[retrieval] skip ${rel}: ${e.message}`);
  }
  return chunks;
}

function loadKnowledgeChunks(fileMeta = {}) {
  const chunks = [];
  if (!fs.existsSync(KNOWLEDGE_DIR)) return chunks;

  for (const full of walkKnowledgeFiles(KNOWLEDGE_DIR)) {
    const file = path.basename(full);
    const meta = fileMeta[file] || fileMeta[file.replace(/\.md$/i, '')] || {};
    chunks.push(...loadFileChunks(full, meta));
  }
  return chunks;
}

function loadPrivateChunks(ownerId, matterId) {
  const chunks = [];
  if (!ownerId && !matterId) return chunks;

  const dirs = [];
  if (matterId) dirs.push(path.join(PRIVATE_INDEX_DIR, 'matter', matterId));
  if (ownerId) dirs.push(path.join(PRIVATE_INDEX_DIR, 'owner', ownerId));

  for (const dir of dirs) {
    const indexPath = path.join(dir, 'chunks.json');
    if (!fs.existsSync(indexPath)) continue;
    try {
      const items = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
      const list = Array.isArray(items) ? items : items.chunks || [];
      for (const item of list) {
        const c = normalizeChunk(item, {
          layer: 'private',
          owner_id: ownerId || item.owner_id,
          matter_id: matterId || item.matter_id,
          namespaces: item.namespaces || [`matter:${matterId || 'private'}`],
        });
        if (c.text) chunks.push(c);
      }
    } catch (e) {
      console.warn(`[retrieval] private skip ${indexPath}: ${e.message}`);
    }
  }
  return chunks;
}

function loadDiscourseIndex() {
  if (!fs.existsSync(DISCOURSE_INDEX)) return [];
  try {
    const doc = JSON.parse(fs.readFileSync(DISCOURSE_INDEX, 'utf8'));
    const items = doc.chunks || doc;
    if (!Array.isArray(items)) return [];
    return items
      .map((item) =>
        normalizeChunk(item, {
          layer: 'discourse',
          source: DISCOURSE_INDEX,
          namespaces: item.namespaces || ['s2-canon'],
        }),
      )
      .filter((c) => c.text);
  } catch (e) {
    console.warn(`[retrieval] discourse index: ${e.message}`);
    return [];
  }
}

function loadPrebuiltIndex() {
  if (!fs.existsSync(RETRIEVAL_INDEX)) return null;
  try {
    const doc = JSON.parse(fs.readFileSync(RETRIEVAL_INDEX, 'utf8'));
    const items = doc.chunks || doc;
    if (!Array.isArray(items)) return null;
    return items.map((item) => normalizeChunk(item)).filter((c) => c.text);
  } catch {
    return null;
  }
}

function loadAllChunks(opts = {}) {
  if (_chunks !== null && !opts.ownerId && !opts.matterId && !opts.forceReload) {
    return _chunks;
  }

  const prebuilt = loadPrebuiltIndex();
  if (prebuilt?.length && !opts.ownerId && !opts.matterId) {
    _chunks = prebuilt;
    console.log(`[retrieval] loaded ${_chunks.length} chunks from ${RETRIEVAL_INDEX}`);
    return _chunks;
  }

  const fileMeta = loadKnowledgeMeta();
  const base = [
    ...loadCanonEntries().map((e) =>
      normalizeChunk(e, { layer: 'canon', namespaces: e.namespaces || ['s2-canon'] }),
    ),
    ...loadKnowledgeChunks(fileMeta),
    ...loadDiscourseIndex(),
  ];

  const privateChunks = loadPrivateChunks(opts.ownerId, opts.matterId);
  const all = [...base, ...privateChunks];

  if (!opts.ownerId && !opts.matterId) {
    _chunks = all;
    console.log(`[retrieval] loaded ${all.length} chunks (canon+knowledge+discourse)`);
  }
  return all;
}

function reloadIndex() {
  _chunks = null;
  try {
    const { reloadCanon } = require('./canon');
    reloadCanon();
  } catch {
    /* optional */
  }
  return loadAllChunks({ forceReload: true });
}

function indexStatus() {
  const chunks = loadAllChunks();
  const byLayer = {};
  const byNamespace = {};
  for (const c of chunks) {
    byLayer[c.layer] = (byLayer[c.layer] || 0) + 1;
    for (const n of c.namespaces || ['(none)']) {
      byNamespace[n] = (byNamespace[n] || 0) + 1;
    }
  }
  return {
    chunkCount: chunks.length,
    byLayer,
    byNamespace,
    knowledgeDir: KNOWLEDGE_DIR,
    canonDir: CANON_DIR,
    discourseIndex: DISCOURSE_INDEX,
    retrievalIndex: RETRIEVAL_INDEX,
    privateIndexDir: PRIVATE_INDEX_DIR,
    prebuilt: Boolean(fs.existsSync(RETRIEVAL_INDEX)),
  };
}

module.exports = {
  loadAllChunks,
  reloadIndex,
  indexStatus,
  KNOWLEDGE_DIR,
  DISCOURSE_INDEX,
  RETRIEVAL_INDEX,
  PRIVATE_INDEX_DIR,
  normalizeChunk,
  loadFileChunks,
};
