/**
 * Ecosystem RAG routes — ingest, publish pack, harvest, beta chat, doc chunk ingest.
 */

const { reloadIndex, indexStatus } = require('./retrieval-index');
const { ragStatus } = require('./rag');
const { ingestKnowledgePack, appendCollectiveChunk } = require('./knowledge-ingest');
const { recordFeedback } = require('./harvest-store');
const { ingestExtractedDocument } = require('./doc-intel-chunk');
const { resolveNamespaces } = require('./rag-namespaces');

function internalAuth(req) {
  const expected = (
    process.env.KNOWLEDGE_INGEST_KEY ||
    process.env.STRATEGIST_HUB_API_KEY ||
    process.env.SHARAYAH_DIGEST_KEY ||
    ''
  ).trim();
  if (!expected) return false;
  const got = (req.get('X-API-Key') || req.get('x-api-key') || '').trim();
  return got === expected;
}

function betaAuth(req) {
  const secret = (process.env.BETA_CHAT_SECRET || process.env.BETA_FEEDBACK_SECRET || '').trim();
  if (!secret) return true;
  const got = (req.get('X-Beta-Chat-Secret') || req.get('x-beta-chat-secret') || '').trim();
  return got === secret;
}

function registerKnowledgeRoutes(app, { handleChat } = {}) {
  app.get('/api/public/knowledge/status', (_req, res) => {
    res.json({
      ok: true,
      rag: ragStatus(),
      index: indexStatus(),
    });
  });

  app.post('/api/internal/knowledge/reload', (req, res) => {
    if (!internalAuth(req)) {
      return res.status(401).json({ ok: false, error: 'Unauthorized' });
    }
    reloadIndex();
    return res.json({ ok: true, index: indexStatus() });
  });

  app.post('/api/internal/knowledge/ingest', (req, res) => {
    if (!internalAuth(req)) {
      return res.status(401).json({ ok: false, error: 'Unauthorized' });
    }
    try {
      const body = req.body || {};
      if (body.pack || body.chunks) {
        const result = ingestKnowledgePack(body.pack || body);
        return res.json({ ok: true, ...result });
      }
      const result = appendCollectiveChunk(body);
      return res.json({ ok: true, ...result });
    } catch (e) {
      return res.status(400).json({ ok: false, error: e.message });
    }
  });

  app.post('/api/internal/knowledge/publish-pack', (req, res) => {
    if (!internalAuth(req)) {
      return res.status(401).json({ ok: false, error: 'Unauthorized' });
    }
    try {
      const pack = req.body || {};
      if (!pack.product_id && !pack.productId) {
        return res.status(400).json({ ok: false, error: 'product_id required' });
      }
      const result = ingestKnowledgePack(pack);
      return res.json({ ok: true, ...result, product_id: pack.product_id || pack.productId });
    } catch (e) {
      return res.status(400).json({ ok: false, error: e.message });
    }
  });

  app.post('/api/public/document-intelligence/ingest-chunks', async (req, res) => {
    try {
      const body = req.body || {};
      const text = body.extracted_text || body.extractedText || body.text;
      if (!text) {
        return res.status(400).json({ ok: false, error: 'extracted_text required' });
      }
      const collective = body.collective === true && internalAuth(req);
      const result = ingestExtractedDocument({
        text,
        filename: body.filename,
        productId: body.product_id || body.productId,
        ownerId: body.owner_id || body.ownerId,
        matterId: body.matter_id || body.matterId,
        collective,
        namespaces: body.rag_namespaces || body.ragNamespaces,
      });
      return res.json({ ok: true, ...result });
    } catch (e) {
      return res.status(400).json({ ok: false, error: e.message });
    }
  });

  app.post('/api/public/harvest/feedback', (req, res) => {
    try {
      const body = req.body || {};
      const rating = body.rating ?? (body.thumbs_up === true ? 5 : body.thumbs_up === false ? 1 : null);
      const result = recordFeedback({
        productId: body.product_id || body.appId || body.app_id,
        ownerId: body.owner_id || body.ownerId,
        userQuery: body.user_query || body.userQuery || body.prompt,
        assistantReply: body.assistant_reply || body.assistantReply || body.reply,
        rating,
        ragUsed: body.rag_used ?? body.ragUsed,
        ragChunks: body.rag_chunks || body.ragChunks,
        namespaces: body.rag_namespaces || resolveNamespaces(body, req),
        context: body.context,
      });
      return res.json({ ok: true, ...result });
    } catch (e) {
      return res.status(400).json({ ok: false, error: e.message });
    }
  });

  if (typeof handleChat === 'function') {
    app.post('/api/public/beta/chat', (req, res) => {
      if (!betaAuth(req)) {
        return res.status(401).json({ ok: false, error: 'Unauthorized' });
      }
      const body = req.body || {};
      const appId = body.appId || body.app_id || body.product_id || 's2artslab-web';
      req.body = { ...body, product_id: body.product_id || appId };
      req.headers['x-s2-inference'] = req.headers['x-s2-inference'] || 'hosted';
      req.headers['x-s2-product-id'] = req.headers['x-s2-product-id'] || appId;
      if (!req.get('X-Owner-Id') && !req.get('x-owner-id')) {
        req.headers['x-owner-id'] = `beta:${appId}`;
      }
      return handleChat(req, res);
    });
  }
}

module.exports = { registerKnowledgeRoutes };
