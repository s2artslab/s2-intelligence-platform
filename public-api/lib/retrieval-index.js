/**
 * Layer 5 — Unified retrieval index (canon + knowledge + discourse export).
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
  };
}

function loadKnowledgeChunks(fileMeta = {}) {
  const chunks = [];
  if (!fs.existsSync(KNOWLEDGE_DIR)) return chunks;

  const files = fs
    .readdirSync(KNOWLEDGE_DIR)
    .filter((f) => /\.(md|txt|json)$/i.test(f) && f !== 'meta.json');

  for (const file of files) {
    const full = path.join(KNOWLEDGE_DIR, file);
    const meta = fileMeta[file] || fileMeta[file.replace(/\.md$/i, '')] || {};
    try {
      const raw = fs.readFileSync(full, 'utf8');
      if (file.endsWith('.json')) {
        const doc = JSON.parse(raw);
        const items = Array.isArray(doc) ? doc : doc.chunks || doc.items || [];
        for (const item of items) {
          const c = normalizeChunk(item, {
            id: item.id || `${file}:${chunks.length}`,
            source: file,
            layer: 'knowledge',
            ...meta,
          });
          if (c.text) chunks.push(c);
        }
      } else {
        const sections = raw.split(/\n(?=#{1,3}\s)/);
        for (let i = 0; i < sections.length; i++) {
          const text = sections[i].trim();
          if (text.length > 80) {
            chunks.push(
              normalizeChunk(
                {
                  id: `${file}:s${i}`,
                  text,
                  source: file,
                },
                { layer: 'knowledge', ...meta },
              ),
            );
          }
        }
      }
    } catch (e) {
      console.warn(`[retrieval] skip ${file}: ${e.message}`);
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
        normalizeChunk(item, { layer: 'discourse', source: DISCOURSE_INDEX }),
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

function loadAllChunks() {
  if (_chunks !== null) return _chunks;

  const prebuilt = loadPrebuiltIndex();
  if (prebuilt?.length) {
    _chunks = prebuilt;
    console.log(`[retrieval] loaded ${_chunks.length} chunks from ${RETRIEVAL_INDEX}`);
    return _chunks;
  }

  const fileMeta = loadKnowledgeMeta();
  _chunks = [
    ...loadCanonEntries().map((e) => normalizeChunk(e, { layer: 'canon' })),
    ...loadKnowledgeChunks(fileMeta),
    ...loadDiscourseIndex(),
  ];
  console.log(
    `[retrieval] loaded ${_chunks.length} chunks (canon+knowledge+discourse)`,
  );
  return _chunks;
}

function reloadIndex() {
  _chunks = null;
  const { reloadCanon } = require('./canon');
  reloadCanon();
  return loadAllChunks();
}

function indexStatus() {
  const chunks = loadAllChunks();
  const byLayer = {};
  for (const c of chunks) {
    byLayer[c.layer] = (byLayer[c.layer] || 0) + 1;
  }
  return {
    chunkCount: chunks.length,
    byLayer,
    knowledgeDir: KNOWLEDGE_DIR,
    canonDir: CANON_DIR,
    discourseIndex: DISCOURSE_INDEX,
    retrievalIndex: RETRIEVAL_INDEX,
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
  normalizeChunk,
};
