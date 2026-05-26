#!/usr/bin/env node
/**
 * S² Intelligence Public API — Ake gateway
 */
const fs = require('fs');
const path = require('path');
const envFile = path.join(__dirname, '.env');
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    const val = trimmed.slice(eq + 1).trim();
    if (key && process.env[key] === undefined) process.env[key] = val;
  }
}

/**
 * - **Hosted** (no user Groq key): billing check → RAG → Ollama `s2-ake`
 * - **BYOK**: user Groq key → same prompt assembly + Groq
 *
 * Clients send thin payloads: text/messages, context (legal|general), optional matter fields.
 * Do not expose egregore names in product UI; internal id is always ake.
 */

const express = require('express');
const { buildCorsMiddleware } = require('./lib/cors-config');
const { groqChat } = require('./lib/groq');
const { ollamaChat, ollamaHealth } = require('./lib/ollama');
const { unifiedLoraChat, unifiedHealth } = require('./lib/unified-lora');
const { buildGatewayMessages } = require('./lib/prompts');
const { retrieveContext, ragStatus } = require('./lib/rag');
const { assembleContinuity } = require('./lib/continuity');
const { canonStatus } = require('./lib/canon');
const { memoryStatus, listOpenTensions, upsertTension, loadStore } = require('./lib/memory/tension-store');
const { reflectSessionHeuristic, scheduleReflection } = require('./lib/memory/reflection');
const { reloadIndex } = require('./lib/retrieval-index');
const { verifyHostedEntitlement } = require('./lib/billing');
const { generateStructuredPaths } = require('./lib/exploration-paths');
const {
  buildExplorationChatMessages,
  buildDigestMessages,
} = require('./lib/exploration-prompts');
const {
  DEFAULT_DOC_INTEL,
  docIntelHealth,
  processPdfProxy,
} = require('./lib/doc-intel-proxy');
const { resolveTemperature } = require('./lib/product-temperature');

const PORT = Number(process.env.PORT || 3010);
const LAB_GROQ_KEY = process.env.GROQ_API_KEY || '';
const DEFAULT_PRODUCT = process.env.BILLING_PRODUCT_ID || 'psla-hosted';
const PREFER_UNIFIED_LORA = process.env.HOSTED_PREFER_UNIFIED_LORA === 'true';
const HOSTED_EGREGORE = process.env.HOSTED_EGREGORE_ID || 'ake';
const HOSTED_TEMPERATURE = Number(process.env.OLLAMA_HOSTED_TEMPERATURE || process.env.OLLAMA_TEMPERATURE || 0.2);

const app = express();
app.use(buildCorsMiddleware());
app.use(express.json({ limit: '8mb' }));

function resolveGroqKey(req) {
  const header =
    req.get('X-Groq-Api-Key') ||
    req.get('x-groq-api-key') ||
    req.body?.groq_api_key;
  const key = (header || LAB_GROQ_KEY || '').trim();
  return key || null;
}

function lastUserText(body) {
  if (body.text || body.user_message) {
    return String(body.text || body.user_message);
  }
  if (Array.isArray(body.messages)) {
    for (let i = body.messages.length - 1; i >= 0; i--) {
      const m = body.messages[i];
      if (m?.role === 'user' && m?.content) return String(m.content);
    }
  }
  return '';
}

function wantsHosted(req, hasGroqKey) {
  const mode = (req.get('X-S2-Inference') || req.body?.inference || '').toLowerCase();
  if (mode === 'hosted' || mode === 'ollama') return true;
  if (mode === 'groq' || mode === 'byok') return false;
  return !hasGroqKey;
}

function ownerIdFrom(req) {
  return (
    req.get('X-Owner-Id') ||
    req.get('x-owner-id') ||
    req.get('X-User-Id') ||
    req.body?.owner_id ||
    req.body?.ownerId ||
    ''
  ).trim();
}

app.get('/health', async (_req, res) => {
  const ollama = await ollamaHealth();
  const unified = await unifiedHealth();
  const rag = ragStatus();
  res.json({
    ok: true,
    service: 's2-intelligence-public-api',
    port: PORT,
    assistant: 's2-ake',
    ollama,
    unified_lora: unified,
    hosted_inference:
      PREFER_UNIFIED_LORA && unified.ok ? 'unified-lora' : ollama.activeModel || 'ollama',
    rag,
    canon: canonStatus(),
    memory: memoryStatus(),
    continuity_layers: ['canon', 'discourse', 'cadence', 'memory', 'retrieval', 'asymmetry'],
    document_intelligence: await docIntelHealth(),
  });
});

app.get('/api/public/capability', async (req, res) => {
  const hasKey = Boolean(resolveGroqKey(req));
  const ollama = await ollamaHealth();
  const unified = await unifiedHealth();
  const rag = ragStatus();
  const hostedReady =
    (PREFER_UNIFIED_LORA && unified.ok) ||
    (ollama.ok && ollama.hasConfiguredModel);

  res.json({
    assistant_name: 'S² Assistant',
    rag_available: rag.available,
    rag_chunks: rag.chunkCount,
    system_prompt_available: true,
    hosted_available: hostedReady,
    groq_configured: hasKey,
    user_groq_required: !LAB_GROQ_KEY && !hostedReady,
    ollama_configured: ollama.ok,
    ollama_model_ready: ollama.hasConfiguredModel,
    unified_lora_ready: unified.ok,
    unified_egregores: unified.available || [],
    message: hasKey
      ? 'Ready — BYOK Groq or hosted S² inference.'
      : hostedReady
        ? 'Ready — hosted S² private AI (subscription or lab mode).'
        : 'Add Groq key in Settings, or ensure hosted Ollama model s2-ake is available.',
  });
});

async function handleChat(req, res) {
  try {
    const groqKey = resolveGroqKey(req);
    const useHosted = wantsHosted(req, Boolean(groqKey));
    const ownerId = ownerIdFrom(req);
    const productId =
      req.get('X-S2-Product-Id') || req.body?.product_id || DEFAULT_PRODUCT;

    if (useHosted) {
      await verifyHostedEntitlement(ownerId, productId);
    }

    const userQuery = lastUserText(req.body);
    const continuity = assembleContinuity(req.body, userQuery, ownerId || 'global');
    const messages = buildGatewayMessages(req.body, continuity.rag.text, {
      canonBlock: continuity.canonBlock,
      tensionBlock: continuity.tensionBlock,
      cadenceOverlay: continuity.cadence.overlay,
    });
    const maxTokens = req.body.max_tokens ?? 800;
    const temperature = resolveTemperature(req, {
      endpointDefault: useHosted ? HOSTED_TEMPERATURE : 0.4,
      productFallback: productId,
    });

    let result;
    let source;

    if (useHosted) {
      let usedUnified = false;
      if (PREFER_UNIFIED_LORA) {
        const unified = await unifiedHealth();
        if (unified.ok) {
          try {
            result = await unifiedLoraChat({
              messages,
              maxTokens,
              temperature,
              egregore: HOSTED_EGREGORE,
            });
            source = 'hosted-unified-lora';
            usedUnified = true;
          } catch (unifiedErr) {
            console.warn('[hosted] unified LoRA failed, falling back to Ollama:', unifiedErr.message);
          }
        }
      }
      if (!usedUnified) {
        result = await ollamaChat({ messages, maxTokens, temperature });
        source = 'hosted-ollama';
      }
    } else {
      result = await groqChat({
        apiKey: groqKey,
        messages,
        maxTokens,
        temperature,
      });
      source = 'groq-byok';
    }

    const assistantText = result.content || result.response || '';
    if (req.body.reflect !== false) {
      scheduleReflection({
        ownerId: ownerId || 'global',
        userText: userQuery,
        assistantText,
        sessionId: req.body.session_id || req.body.sessionId,
      });
    }

    res.json({
      success: true,
      content: assistantText,
      response: assistantText,
      model: result.model,
      source,
      assistant: 's2-ake',
      cadence: continuity.cadence.cadence,
      adapter_hint: continuity.cadence.adapterHint,
      rag_used: continuity.rag.chunks.length > 0,
      rag_chunks: continuity.rag.chunks,
      canon_used: Boolean(continuity.canonBlock),
      tensions_active: continuity.tensionIds,
      processing_time_ms: null,
    });
  } catch (e) {
    const status = e.statusCode || 500;
    res.status(status).json({
      success: false,
      error: e.message,
      content: '',
    });
  }
}

app.post('/api/ai/chat', handleChat);
app.post('/api/public/chat', handleChat);
app.post('/api/public/chat-with-context', handleChat);

function memoryAuthorized(req) {
  const expected = (
    process.env.MEMORY_API_KEY ||
    process.env.STRATEGIST_HUB_API_KEY ||
    process.env.SHARAYAH_DIGEST_KEY ||
    ''
  ).trim();
  if (!expected) return true;
  const got = (req.get('X-API-Key') || req.get('x-api-key') || '').trim();
  return got === expected;
}

/** Layer 4 — list open tensions for owner scope */
app.get('/api/public/memory/tensions', (req, res) => {
  if (!memoryAuthorized(req)) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }
  const ownerId = ownerIdFrom(req) || 'global';
  res.json({
    success: true,
    owner_id: ownerId,
    tensions: listOpenTensions(ownerId, {
      limit: Number(req.query.limit || 20),
    }),
  });
});

/** Layer 4 — upsert tension (apps, reflection) */
app.post('/api/public/memory/tensions', (req, res) => {
  if (!memoryAuthorized(req)) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }
  const ownerId = ownerIdFrom(req) || req.body?.owner_id || 'global';
  try {
    const tension = upsertTension(ownerId, req.body || {});
    res.json({ success: true, tension });
  } catch (e) {
    res.status(400).json({ success: false, error: e.message });
  }
});

/** Layer 4 — memory store summary */
app.get('/api/public/memory/status', (req, res) => {
  const ownerId = ownerIdFrom(req) || 'global';
  const store = loadStore(ownerId);
  res.json({
    success: true,
    owner_id: ownerId,
    memory: memoryStatus(),
    open_tensions: store.tensions.filter(
      (t) => t.status === 'open' || t.status === 'deepened',
    ).length,
    episodic_count: store.episodic.length,
  });
});

/** Internal — reload retrieval index + canon */
app.post('/api/internal/continuity/reload', (req, res) => {
  if (!memoryAuthorized(req)) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }
  reloadIndex();
  res.json({
    success: true,
    rag: ragStatus(),
    canon: canonStatus(),
  });
});

/** Internal — run reflection job for one session */
app.post('/api/internal/memory/reflect', (req, res) => {
  if (!memoryAuthorized(req)) {
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }
  const ownerId = ownerIdFrom(req) || req.body?.owner_id || 'global';
  const result = reflectSessionHeuristic({
    ownerId,
    userText: req.body?.user_text || req.body?.userText || '',
    assistantText: req.body?.assistant_text || req.body?.assistantText || '',
    sessionId: req.body?.session_id,
  });
  res.json({ success: true, ...result });
});

/** PSLA exploration — structured litigation paths (JSON schema). */
app.post('/api/psla/exploration/paths', async (req, res) => {
  try {
    const groqKey = resolveGroqKey(req);
    const useHosted = wantsHosted(req, Boolean(groqKey));
    const ownerId = ownerIdFrom(req);
    const productId =
      req.get('X-S2-Product-Id') || req.body?.product_id || 'psla-exploration';

    if (useHosted) {
      await verifyHostedEntitlement(ownerId, productId);
    }

    const userQuery =
      req.body.user_message ||
      req.body.text ||
      'Compare litigation paths for this pre-filing situation.';
    const continuity = assembleContinuity(
      { ...req.body, exploration: true, product_id: 'psla-exploration' },
      `${userQuery} ${req.body.jurisdiction || ''} pre-filing litigation paths`,
      ownerId || 'global',
    );

    const { paths, model, source } = await generateStructuredPaths({
      body: req.body,
      ragBlock: continuity.rag.text,
      groqKey,
      useHosted,
      maxTokens: req.body.max_tokens ?? 4000,
      temperature: resolveTemperature(req, {
        endpointDefault: 0.15,
        productFallback: productId,
      }),
    });

    res.json({
      success: true,
      paths,
      model,
      source,
      rag_used: continuity.rag.chunks.length > 0,
      product: 'psla-exploration',
    });
  } catch (e) {
    res.status(e.statusCode || 500).json({
      success: false,
      error: e.message,
      paths: [],
    });
  }
});

/** PSLA exploration chat — pre-filing prompt pack + workspace context. */
app.post('/api/psla/exploration/chat', async (req, res) => {
  try {
    const groqKey = resolveGroqKey(req);
    const useHosted = wantsHosted(req, Boolean(groqKey));
    const ownerId = ownerIdFrom(req);
    const productId =
      req.get('X-S2-Product-Id') || req.body?.product_id || 'psla-exploration';

    if (useHosted) {
      await verifyHostedEntitlement(ownerId, productId);
    }

    const userQuery = lastUserText(req.body);
    const continuity = assembleContinuity(
      { ...req.body, exploration: true },
      userQuery,
      ownerId || 'global',
    );

    const messages = buildExplorationChatMessages(req.body, continuity.rag.text);
    const maxTokens = req.body.max_tokens ?? 3000;
    const temperature = resolveTemperature(req, {
      endpointDefault: Number(process.env.OLLAMA_EXPLORATION_TEMPERATURE || 0.15),
      productFallback: productId,
    });

    let result;
    let source;
    if (useHosted) {
      result = await ollamaChat({ messages, maxTokens, temperature });
      source = 'hosted-ollama-exploration';
    } else {
      result = await groqChat({
        apiKey: groqKey,
        messages,
        maxTokens,
        temperature,
      });
      source = 'groq-exploration';
    }

    res.json({
      success: true,
      content: result.content,
      response: result.content,
      model: result.model,
      source,
      rag_used: continuity.rag.chunks.length > 0,
      cadence: continuity.cadence.cadence,
      product: 'psla-exploration',
    });
  } catch (e) {
    res.status(e.statusCode || 500).json({
      success: false,
      error: e.message,
      content: '',
    });
  }
});

/** Summarize long exploration materials before chat/path prompts. */
app.post('/api/psla/exploration/material-digest', async (req, res) => {
  try {
    const groqKey = resolveGroqKey(req);
    const useHosted = wantsHosted(req, Boolean(groqKey));
    if (useHosted) {
      await verifyHostedEntitlement(
        ownerIdFrom(req),
        req.get('X-S2-Product-Id') || 'psla-exploration',
      );
    }

    const messages = buildDigestMessages(req.body);
    const maxTokens = req.body.max_tokens ?? 2000;
    const temperature = 0.15;

    let raw;
    if (!useHosted && groqKey) {
      const result = await groqChat({
        apiKey: groqKey,
        messages,
        maxTokens,
        temperature,
        responseFormat: { type: 'json_object' },
      });
      raw = result.content;
    } else {
      const result = await ollamaChat({ messages, maxTokens, temperature });
      raw = result.content;
    }

    const { extractJsonObject } = require('./lib/exploration-paths');
    const digest = extractJsonObject(raw);

    res.json({
      success: true,
      digest,
      product: 'psla-exploration',
    });
  } catch (e) {
    res.status(e.statusCode || 500).json({
      success: false,
      error: e.message,
    });
  }
});

/**
 * Web-safe PDF proxy — browser posts base64; server forwards to public doc-intel.
 * Body: { filename, content_base64 }
 */
app.post('/api/public/document-intelligence/process-pdf', async (req, res) => {
  try {
    const b64 = req.body?.content_base64 || req.body?.contentBase64;
    if (!b64) {
      return res.status(400).json({ success: false, error: 'content_base64 required' });
    }
    const bytes = Buffer.from(String(b64), 'base64');
    const filename = req.body?.filename || 'document.pdf';
    const baseUrl = req.body?.doc_intel_url || DEFAULT_DOC_INTEL;
    const result = await processPdfProxy({ bytes, filename, baseUrl });
    res.json({
      success: true,
      extracted_text: result.extractedText,
      document_id: result.documentId,
      doc_intel_url: baseUrl.replace(/\/$/, ''),
    });
  } catch (e) {
    res.status(e.statusCode || 500).json({
      success: false,
      error: e.message,
    });
  }
});

app.get('/api/public/document-intelligence/health', async (_req, res) => {
  res.json(await docIntelHealth());
});

/** Strategist hub Worker — hosted Ollama (s2-ake) for narrative, proposals, growth, beta. */
function strategistHubAuthorized(req) {
  const expected = (
    process.env.STRATEGIST_HUB_API_KEY ||
    process.env.SHARAYAH_DIGEST_KEY ||
    ''
  ).trim();
  if (!expected) return false;
  const got = (
    req.get('X-API-Key') ||
    req.get('x-api-key') ||
    req.get('X-Sharayah-Digest') ||
    ''
  ).trim();
  return got === expected;
}

app.post('/api/public/strategist/generate', async (req, res) => {
  if (!strategistHubAuthorized(req)) {
    return res.status(401).json({ ok: false, error: 'Unauthorized' });
  }
  const prompt = String(req.body?.prompt || '').trim();
  if (!prompt) {
    return res.status(400).json({ ok: false, error: 'Missing prompt' });
  }
  const egregore = String(req.body?.egregore || HOSTED_EGREGORE).trim() || 'ake';
  const maxTokens = Number(req.body?.max_length) || Number(req.body?.max_tokens) || 2500;
  const temperature = resolveTemperature(req, {
    endpointDefault: 0.72,
    productFallback: 'sharayah-strategist',
  });
  try {
    const result = await ollamaChat({
      messages: [{ role: 'user', content: prompt }],
      maxTokens,
      temperature,
    });
    const response = String(result.content || '').trim();
    return res.json({
      ok: true,
      response,
      egregore,
      service: 'ollama',
      model: result.model,
    });
  } catch (e) {
    return res.status(503).json({ ok: false, error: e.message || String(e) });
  }
});

app.listen(PORT, () => {
  console.log(`S² Intelligence API (Ake gateway) http://0.0.0.0:${PORT}`);
  console.log(`  Ollama: ${process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434'}`);
  console.log(`  Model:  ${process.env.OLLAMA_MODEL || 's2-ake'}`);
  console.log(
    `  Unified LoRA: ${process.env.UNIFIED_EGREGORE_URL || 'http://127.0.0.1:8100'} (prefer=${PREFER_UNIFIED_LORA})`,
  );
  console.log(`  Doc-intel: ${DEFAULT_DOC_INTEL}`);
  console.log(
    LAB_GROQ_KEY
      ? '  Lab GROQ_API_KEY set'
      : '  BYOK: clients send X-Groq-Api-Key',
  );
  console.log(
    process.env.HOSTED_REQUIRE_BILLING === 'true'
      ? '  Hosted billing: REQUIRED'
      : '  Hosted billing: optional (set HOSTED_REQUIRE_BILLING=true)',
  );
});
