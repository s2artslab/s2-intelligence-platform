/**
 * Ingest chunks into collective knowledge/ or private matter indexes.
 */

const fs = require('fs');
const path = require('path');
const { normalizeChunk, reloadIndex, KNOWLEDGE_DIR, PRIVATE_INDEX_DIR } = require('./retrieval-index');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function slugify(value) {
  return String(value || 'chunk')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 64);
}

function appendCollectiveChunk(chunk) {
  const normalized = normalizeChunk(chunk, {
    layer: chunk.layer || 'knowledge',
    source: chunk.source || 'ingest',
  });
  if (!normalized.text || normalized.text.length < 40) {
    throw new Error('Chunk text too short (min 40 chars)');
  }

  const ns = normalized.namespaces?.[0] || 'community';
  const productMatch = (normalized.namespaces || []).find((n) => n.startsWith('product:'));
  const subdir = productMatch
    ? path.join('products', productMatch.replace('product:', ''))
    : 'ingested';
  const dir = path.join(KNOWLEDGE_DIR, subdir);
  ensureDir(dir);

  const id = normalized.id || `${subdir}:${Date.now()}`;
  const outPath = path.join(dir, `${slugify(id)}.json`);
  fs.writeFileSync(
    outPath,
    JSON.stringify(
      {
        id,
        text: normalized.text,
        namespaces: normalized.namespaces || ['s2-canon', 'community'],
        concept_tags: normalized.concept_tags || [],
        source: normalized.source || path.relative(KNOWLEDGE_DIR, outPath),
      },
      null,
      2,
    ),
  );
  reloadIndex();
  return { path: outPath, id };
}

function appendPrivateChunks({ ownerId, matterId, chunks }) {
  if (!ownerId && !matterId) {
    throw new Error('ownerId or matterId required for private ingest');
  }
  const key = matterId ? `matter/${matterId}` : `owner/${ownerId}`;
  const dir = path.join(PRIVATE_INDEX_DIR, key);
  ensureDir(dir);
  const indexPath = path.join(dir, 'chunks.json');

  let existing = [];
  if (fs.existsSync(indexPath)) {
    try {
      const raw = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
      existing = Array.isArray(raw) ? raw : raw.chunks || [];
    } catch {
      existing = [];
    }
  }

  const added = [];
  for (const item of chunks) {
    const normalized = normalizeChunk(item, {
      layer: 'private',
      owner_id: ownerId,
      matter_id: matterId,
      namespaces: item.namespaces || (matterId ? [`matter:${matterId}`] : [`owner:${ownerId}`]),
    });
    if (normalized.text && normalized.text.length >= 20) {
      existing.push(normalized);
      added.push(normalized.id || `private:${existing.length}`);
    }
  }

  fs.writeFileSync(indexPath, JSON.stringify(existing, null, 2));
  reloadIndex();
  return { path: indexPath, added: added.length, total: existing.length };
}

function ingestKnowledgePack(pack) {
  const chunks = pack.chunks || pack.items || [];
  if (!Array.isArray(chunks) || !chunks.length) {
    throw new Error('pack.chunks array required');
  }
  const productId = pack.product_id || pack.productId;
  const defaultNs = productId
    ? ['s2-canon', `product:${String(productId).replace(/_/g, '-')}`]
    : ['s2-canon', 'community'];

  const results = [];
  for (const item of chunks) {
    const ns = item.namespaces || defaultNs;
    results.push(
      appendCollectiveChunk({
        ...item,
        namespaces: ns,
        source: item.source || `pack:${productId || 'generic'}`,
      }),
    );
  }
  return { ingested: results.length, files: results };
}

function chunkPlainText(text, opts = {}) {
  const maxLen = opts.maxLen || Number(process.env.RAG_INGEST_CHUNK_CHARS || 1200);
  const overlap = opts.overlap || 120;
  const paragraphs = String(text || '')
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 40);

  const chunks = [];
  let buffer = '';

  for (const para of paragraphs) {
    if ((buffer + '\n\n' + para).length <= maxLen) {
      buffer = buffer ? `${buffer}\n\n${para}` : para;
    } else {
      if (buffer) chunks.push(buffer);
      if (para.length > maxLen) {
        for (let i = 0; i < para.length; i += maxLen - overlap) {
          chunks.push(para.slice(i, i + maxLen));
        }
        buffer = '';
      } else {
        buffer = para;
      }
    }
  }
  if (buffer) chunks.push(buffer);
  return chunks;
}

module.exports = {
  appendCollectiveChunk,
  appendPrivateChunks,
  ingestKnowledgePack,
  chunkPlainText,
};
