/**
 * Harvest high-quality chat turns for DPO / Tier E (rag_used + positive rating).
 */

const fs = require('fs');
const path = require('path');

const HARVEST_DIR =
  process.env.S2_HARVEST_DIR ||
  path.join(__dirname, '..', 'data', 'harvest');

const DPO_OUT =
  process.env.S2_HARVEST_DPO_PATH ||
  '/opt/s2-ecosystem/egregore-training/training_data/preferences/ake_dpo_harvest.jsonl';

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function harvestPath() {
  const day = new Date().toISOString().slice(0, 10);
  return path.join(HARVEST_DIR, `chat-harvest-${day}.jsonl`);
}

function appendHarvest(entry) {
  ensureDir(HARVEST_DIR);
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    ...entry,
  });
  fs.appendFileSync(harvestPath(), `${line}\n`);
  return { path: harvestPath() };
}

function recordFeedback({
  productId,
  ownerId,
  userQuery,
  assistantReply,
  rating,
  ragUsed,
  ragChunks,
  namespaces,
  context,
}) {
  if (rating == null || Number(rating) < 1) {
    throw new Error('rating required (1-5 or thumbs up as 5)');
  }
  const score = Number(rating);
  if (score < 4 && process.env.HARVEST_MIN_RATING) {
    return { skipped: true, reason: 'below_min_rating' };
  }
  if (!ragUsed && process.env.HARVEST_REQUIRE_RAG === 'true') {
    return { skipped: true, reason: 'rag_not_used' };
  }

  const row = {
    product_id: productId,
    owner_id: ownerId || null,
    context: context || 'general',
    user: userQuery,
    assistant: assistantReply,
    rating: score,
    rag_used: Boolean(ragUsed),
    rag_chunks: ragChunks || [],
    namespaces: namespaces || [],
  };

  appendHarvest(row);

  if (score >= 4) {
    appendDpoCandidate(row);
  }

  return { ok: true, harvested: true };
}

function appendDpoCandidate(row) {
  const dpoDir = path.dirname(DPO_OUT);
  if (!fs.existsSync(dpoDir)) {
    try {
      fs.mkdirSync(dpoDir, { recursive: true });
    } catch {
      return { skipped: true, reason: 'dpo_path_missing' };
    }
  }

  const prompt = `User: ${row.user}\nAke:`;
  const chosen = String(row.assistant || '').replace(/^Ake:\s*/i, '');
  const line = JSON.stringify({
    prompt,
    chosen,
    rejected: '',
    metadata: {
      source: 'harvest',
      product_id: row.product_id,
      rag_used: row.rag_used,
      namespaces: row.namespaces,
    },
  });
  fs.appendFileSync(DPO_OUT, `${line}\n`);
  return { dpo: DPO_OUT };
}

module.exports = {
  appendHarvest,
  recordFeedback,
  harvestPath,
  HARVEST_DIR,
};
