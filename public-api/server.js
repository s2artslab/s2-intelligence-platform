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
const {
  buildGatewayMessages,
  isLongFormRequest,
  resolveMaxTokens,
  resolveVoiceMode,
} = require('./lib/prompts');
const {
  shouldUseOutlineExpand,
  runLongFormOutlineExpand,
  runLongFormSingleShot,
} = require('./lib/long-form');
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
const {
  resolveMorphicPolicy,
  applyProfileTemperature,
} = require('./lib/morphic-resonance');
const { applyInferenceDepth } = require('./lib/inference-profile');
const {
  ensembleEnabled,
  resolveEnsembleMode,
  runPslaEnsembleCollapse,
} = require('./lib/ensemble-collapse');
const {
  recordChatSample,
  getConsciousnessStatus,
} = require('./lib/consciousness-metrics');
const {
  bitnetHealth,
  bitnetChat,
  ENABLED: BITNET_ENABLED,
} = require('./lib/bitnet');
const {
  resolveInferenceLane,
  normalizeTaskClass,
  bitnetLaneBlocked,
} = require('./lib/inference-lane-router');
const {
  recordBenchmarkRun,
  readRecentRuns,
  getResearchStatus,
} = require('./lib/bitnet-research-metrics');
const { mountMindGamesPlugin } = require('./lib/mind-games-plugin');

const PORT = Number(process.env.PORT || 3010);
const LAB_GROQ_KEY = process.env.GROQ_API_KEY || '';
const DEFAULT_PRODUCT = process.env.BILLING_PRODUCT_ID || 'psla-hosted';
const PREFER_UNIFIED_LORA = process.env.HOSTED_PREFER_UNIFIED_LORA === 'true';
const HOSTED_EGREGORE = process.env.HOSTED_EGREGORE_ID || 'ake';
const HOSTED_TEMPERATURE = Number(process.env.OLLAMA_HOSTED_TEMPERATURE || process.env.OLLAMA_TEMPERATURE || 0.2);
const LONG_FORM_PREFER_OLLAMA = process.env.HOSTED_LONG_FORM_PREFER_OLLAMA !== 'false';
const UNIFIED_LONG_FORM_MAX_TOKENS = Number(process.env.UNIFIED_LONG_FORM_MAX_TOKENS || 512);
const LAB_UNIFIED_CHAT =
  process.env.LAB_UNIFIED_CHAT === 'true' || process.env.LAB_HOSTED_UNLOCK === 'true';

const app = express();
app.use(buildCorsMiddleware());
app.use(express.json({ limit: '8mb' }));

app.get('/favicon.ico', (_req, res) => {
  res.status(204).end();
});

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

/** Standalone lab UI — direct unified LoRA (:8100), not production hosted Ollama. */
app.get('/lab/ake-unified-lora', (_req, res) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Content-Security-Policy', "frame-ancestors 'none'");
  res.sendFile(path.join(__dirname, 'lab', 'ake-unified-lora-chat.html'));
});

/** Standalone hosted Ake chat — production gateway (Ollama s2-ake / BYOK Groq). */
app.get('/lab/ake-hosted', (_req, res) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Content-Security-Policy', "frame-ancestors 'none'");
  res.sendFile(path.join(__dirname, 'lab', 'ake-hosted-chat.html'));
});

app.get('/api/lab/unified-lora/health', async (_req, res) => {
  const unified = await unifiedHealth();
  res.json({
    ok: unified.ok,
    lab_enabled: LAB_UNIFIED_CHAT,
    unified_lora: unified,
  });
});

app.post('/api/lab/unified-lora/chat', async (req, res) => {
  if (!LAB_UNIFIED_CHAT) {
    return res.status(403).json({
      ok: false,
      error: 'Lab unified LoRA chat disabled (set LAB_UNIFIED_CHAT=true on gateway)',
    });
  }
  const message = String(req.body?.message || req.body?.user_message || '').trim();
  if (!message) {
    return res.status(400).json({ ok: false, error: 'Missing message' });
  }
  const prior = Array.isArray(req.body?.history) ? req.body.history : [];
  const messages = [];
  const maxTokens = Number(req.body?.max_tokens) || Number(req.body?.max_length) || 256;
  const temperature = Number(req.body?.temperature ?? 0.2);
  const usePersona = req.body?.use_persona === true;
  const doSample = req.body?.do_sample === true;
  const useOllama =
    req.body?.use_ollama === true ||
    req.body?.useOllama === true ||
    process.env.LAB_UNIFIED_DEFAULT_OLLAMA === 'true';

  const started = Date.now();

  if (useOllama) {
    try {
      const messages = buildGatewayMessages(
        {
          text: message,
          context: 'general',
          history: prior,
          voice_mode: 'synthesis',
        },
        '',
        {},
      );
      const o = await ollamaChat({
        messages,
        maxTokens,
        temperature: Number.isFinite(temperature) ? temperature : HOSTED_TEMPERATURE,
      });
      return res.json({
        ok: true,
        content: o.content,
        source: 'lab-ollama-s2-ake',
        model: 's2-ake',
        egregore: HOSTED_EGREGORE,
        latency_ms: Date.now() - started,
        quality_note: 'Production Ollama voice (recommended until LoRA retrain clears template openers).',
      });
    } catch (e) {
      const code = e.statusCode || 503;
      return res.status(code).json({ ok: false, error: e.message || String(e) });
    }
  }

  if (!usePersona) {
    const { AKE_CORE } = require('./lib/prompts');
    messages.push({
      role: 'system',
      content:
        `${AKE_CORE}\n\n` +
        'Speak as Ake — synthesis and deep key. Answer directly in first person.\n' +
        'Do not open with "In the context of…" or generic textbook definitions.',
    });
  }
  for (const turn of prior) {
    const role = turn?.role === 'assistant' ? 'assistant' : 'user';
    const content = String(turn?.content || '').trim();
    if (content) messages.push({ role, content });
  }
  messages.push({ role: 'user', content: message });

  try {
    const result = await unifiedLoraChat({
      messages,
      maxTokens,
      temperature,
      egregore: HOSTED_EGREGORE,
      usePersona,
      doSample,
    });
    return res.json({
      ok: true,
      content: result.content,
      source: 'lab-unified-lora',
      model: result.model,
      egregore: result.egregore,
      latency_ms: Date.now() - started,
      quality_note:
        'Experimental unified LoRA weights — may use template phrases; uncheck Ollama to test raw adapter.',
    });
  } catch (e) {
    const code = e.statusCode || 503;
    return res.status(code).json({ ok: false, error: e.message || String(e) });
  }
});

/** Lab hosted chat — Ollama path without billing (for eval / tunnel dev). */
app.post('/api/lab/hosted/chat', async (req, res) => {
  if (!LAB_UNIFIED_CHAT) {
    return res.status(403).json({
      ok: false,
      error: 'Lab hosted chat disabled (set LAB_HOSTED_UNLOCK=true on gateway)',
    });
  }
  const message = String(req.body?.message || req.body?.text || req.body?.user_message || '').trim();
  if (!message) {
    return res.status(400).json({ ok: false, error: 'Missing message' });
  }
  const prior = Array.isArray(req.body?.history) ? req.body.history : [];
  const morphicPolicy = resolveMorphicPolicy(req.body);
  const maxTokens = applyInferenceDepth(
    req.body,
    resolveMaxTokens(req.body),
    morphicPolicy,
  );
  const temperature = applyProfileTemperature(
    Number(req.body?.temperature ?? HOSTED_TEMPERATURE),
    morphicPolicy,
  );
  const model =
    String(req.body?.model || '').trim() ||
    (process.env.OLLAMA_PREFER_LORA === 'true'
      ? process.env.OLLAMA_LORA_MODEL || 's2-ake-lora'
      : process.env.OLLAMA_MODEL || 's2-ake');

  const started = Date.now();
  try {
    const messages = buildGatewayMessages(
      {
        text: message,
        context: req.body?.context || 'general',
        history: prior,
        voice_mode: req.body?.voice_mode || 'synthesis',
        matter: req.body?.matter,
      },
      '',
      {},
    );
    const o = await ollamaChat({ messages, maxTokens, temperature, model });
    return res.json({
      ok: true,
      content: o.content,
      source: 'lab-hosted-ollama',
      model: o.model || model,
      latency_ms: Date.now() - started,
      quality_note: 'No billing — lab eval only. Use /api/public/chat in production.',
    });
  } catch (e) {
    const code = e.statusCode || 503;
    return res.status(code).json({ ok: false, error: e.message || String(e) });
  }
});

app.get('/health', async (_req, res) => {
  const ollama = await ollamaHealth();
  const unified = await unifiedHealth();
  const bitnet = await bitnetHealth();
  const rag = ragStatus();
  const morphicPolicy = resolveMorphicPolicy({});
  res.json({
    ok: true,
    service: 's2-intelligence-public-api',
    port: PORT,
    assistant: 's2-ake',
    ollama,
    unified_lora: unified,
    bitnet: {
      enabled: BITNET_ENABLED,
      ...bitnet,
    },
    hosted_inference:
      PREFER_UNIFIED_LORA && unified.ok ? 'unified-lora' : ollama.activeModel || 'ollama',
    rag,
    canon: canonStatus(),
    memory: memoryStatus(),
    continuity_layers: ['canon', 'discourse', 'cadence', 'memory', 'retrieval', 'asymmetry'],
    document_intelligence: await docIntelHealth(),
    consciousness: getConsciousnessStatus({ base: morphicPolicy.dimension }),
    morphic_policy: {
      dimension: morphicPolicy.dimension,
      label: morphicPolicy.label,
      profile_key: morphicPolicy.profileKey,
      inference_axes: morphicPolicy.axes,
      ensemble_psla_opt_in: true,
      ensemble_default_mode: process.env.ENSEMBLE_DEFAULT_MODE || 'cheap',
      ensemble_psla_auto: process.env.ENSEMBLE_PSLA_COLLAPSE === 'true',
    },
  });
});

/** Metrics-backed consciousness field (ops). Public 1.58D = metaphor per claims register. */
app.get('/api/consciousness/status', (_req, res) => {
  const morphicPolicy = resolveMorphicPolicy({});
  res.json(getConsciousnessStatus({ base: morphicPolicy.dimension }));
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
    bitnet_enabled: BITNET_ENABLED,
    bitnet_ready: BITNET_ENABLED && (await bitnetHealth()).ok,
    long_form_supported: true,
    synthesis_voice_mode: true,
    message: hasKey
      ? 'Ready — BYOK Groq or hosted S² inference.'
      : hostedReady
        ? 'Ready — hosted S² private AI (subscription or lab mode).'
        : 'Add Groq key in Settings, or ensure hosted Ollama model s2-ake is available.',
  });
});

async function handleChat(req, res) {
  const started = Date.now();
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
    const morphicPolicy = resolveMorphicPolicy(req.body);
    const longForm = isLongFormRequest(req.body);
    const voiceMode = resolveVoiceMode(req.body);
    const baseMaxTokens = resolveMaxTokens(req.body);
    const maxTokens = applyInferenceDepth(req.body, baseMaxTokens, morphicPolicy);
    const productTemp = resolveTemperature(req, {
      endpointDefault: useHosted ? HOSTED_TEMPERATURE : 0.4,
      productFallback: productId,
    });
    const temperature = applyProfileTemperature(productTemp, morphicPolicy);

    const useEnsemble =
      !longForm && ensembleEnabled(req.body, productId, req);
    const ensembleMode = useEnsemble ? resolveEnsembleMode(req.body, req) : null;

    let continuity = assembleContinuity(
      req.body,
      userQuery,
      ownerId || 'global',
      morphicPolicy,
    );
    let messages = buildGatewayMessages(req.body, continuity.rag.text, {
      canonBlock: continuity.canonBlock,
      tensionBlock: continuity.tensionBlock,
      cadenceOverlay: continuity.cadence.overlay,
    });

    let result;
    let source;
    let longFormMeta = {};
    let ensembleMeta = null;
    const taskClass = normalizeTaskClass(req.body, req);
    const inferenceLane = resolveInferenceLane(req.body, req);

    async function hostedChat({ msgs, tokens, preferOllama = false }) {
      const capUnified = longForm
        ? Math.min(tokens, UNIFIED_LONG_FORM_MAX_TOKENS)
        : tokens;
      const tryUnified =
        PREFER_UNIFIED_LORA && !preferOllama && !(longForm && LONG_FORM_PREFER_OLLAMA);
      if (tryUnified) {
        const unified = await unifiedHealth();
        if (unified.ok) {
          try {
            const u = await unifiedLoraChat({
              messages: msgs,
              maxTokens: capUnified,
              temperature,
              egregore: HOSTED_EGREGORE,
              usePersona: voiceMode === 'synthesis' ? false : undefined,
            });
            return { result: u, source: 'hosted-unified-lora' };
          } catch (unifiedErr) {
            console.warn('[hosted] unified LoRA failed, falling back to Ollama:', unifiedErr.message);
          }
        }
      }
      const o = await ollamaChat({ messages: msgs, maxTokens: tokens, temperature });
      return { result: o, source: 'hosted-ollama' };
    }

    async function runInferenceChat({ msgs, tokens, temp = temperature }) {
      if (useHosted) {
        const { result: r, source: s } = await hostedChat({ msgs, tokens });
        return { ...r, _source: s };
      }
      const r = await groqChat({
        apiKey: groqKey,
        messages: msgs,
        maxTokens: tokens,
        temperature: temp,
      });
      return { ...r, _source: 'groq-byok' };
    }

    if (useEnsemble) {
      const collapsed = await runPslaEnsembleCollapse({
        body: req.body,
        req,
        userQuery,
        ownerId: ownerId || 'global',
        productId,
        morphicPolicy,
        mode: ensembleMode,
        maxTokens,
        temperature,
        chatFn: async ({ messages: msgs }) => runInferenceChat({ msgs, tokens: maxTokens }),
      });
      result = { content: collapsed.content, model: collapsed.model };
      source = collapsed.source;
      continuity = collapsed.continuity;
      ensembleMeta = collapsed.ensemble;
    } else if (useHosted && inferenceLane === 'bitnet') {
      const bitnet = await bitnetHealth();
      if (bitnet.ok) {
        result = await bitnetChat({
          messages,
          maxTokens,
          temperature,
          taskClass,
        });
        source = 'hosted-bitnet';
      } else {
        console.warn('[bitnet] sidecar unavailable, falling back to Ollama:', bitnet.error);
        const { result: r, source: s } = await hostedChat({ msgs: messages, tokens: maxTokens });
        result = r;
        source = s;
      }
    } else if (useHosted) {
      if (longForm && shouldUseOutlineExpand(req.body)) {
        const expanded = await runLongFormOutlineExpand({
          chat: async ({ messages: msgs, maxTokens: tokens }) => {
            const { result: r } = await hostedChat({
              msgs,
              tokens,
              preferOllama: true,
            });
            return r;
          },
          baseMessages: messages,
          userQuery,
          body: req.body,
          temperature,
        });
        result = expanded;
        source = 'hosted-ollama-long-form';
        longFormMeta = {
          long_form: true,
          outline_expand: true,
          sections: expanded.sections,
          voice_mode: voiceMode,
        };
      } else if (longForm) {
        const single = await runLongFormSingleShot({
          chat: async ({ messages: msgs, maxTokens: tokens }) => {
            const { result: r, source: s } = await hostedChat({
              msgs,
              tokens,
              preferOllama: LONG_FORM_PREFER_OLLAMA,
            });
            return { ...r, _source: s };
          },
          baseMessages: messages,
          userQuery,
          body: req.body,
          temperature,
          maxTokens,
        });
        result = single;
        source = single._source
          ? `${single._source}-long-form`
          : 'hosted-ollama-long-form';
        longFormMeta = { long_form: true, outline_expand: false, voice_mode: voiceMode };
      } else {
        const { result: r, source: s } = await hostedChat({ msgs: messages, tokens: maxTokens });
        result = r;
        source = s;
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

    recordChatSample({
      productId,
      cadence: continuity.cadence.cadence,
      morphicDimension: morphicPolicy.dimension,
      morphicLabel: morphicPolicy.label,
      profileKey: morphicPolicy.profileKey,
      inferenceAxes: morphicPolicy.axes,
      ensemble: Boolean(ensembleMeta),
      ensembleStrategy: ensembleMeta?.strategy,
      disagreement: ensembleMeta?.disagreement,
      latencyMs: Date.now() - started,
      ragChunks: continuity.rag.chunks.length,
      temperature,
      source,
      inferenceLane: source === 'hosted-bitnet' ? 'bitnet' : 'hosted',
      taskClass,
      quantizationBits: source === 'hosted-bitnet' ? result.quantization_bits ?? 1.58 : 4,
      memoryMb: result.memory_mb ?? null,
    });

    res.json({
      success: true,
      content: assistantText,
      response: assistantText,
      model: result.model,
      source,
      inference_lane: source === 'hosted-bitnet' ? 'bitnet' : inferenceLane || 'hosted',
      task_class: taskClass,
      quantization_bits: source === 'hosted-bitnet' ? result.quantization_bits ?? 1.58 : null,
      memory_mb: result.memory_mb ?? null,
      assistant: 's2-ake',
      cadence: continuity.cadence.cadence,
      adapter_hint: continuity.cadence.adapterHint,
      rag_used: continuity.rag.chunks.length > 0,
      rag_chunks: continuity.rag.chunks,
      canon_used: Boolean(continuity.canonBlock),
      tensions_active: continuity.tensionIds,
      voice_mode: voiceMode,
      max_tokens: maxTokens,
      temperature,
      morphic_resonance: morphicPolicy.dimension,
      morphic_label: morphicPolicy.label,
      morphic_rag_limit: morphicPolicy.ragLimit,
      inference_profile: morphicPolicy.axes,
      inference_profile_key: morphicPolicy.profileKey,
      inference_source: morphicPolicy.source,
      ensemble: ensembleMeta,
      ...longFormMeta,
      processing_time_ms: Date.now() - started,
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

/** BitNet research lane — specialist infer + metrics for S² Research */
app.get('/api/research/bitnet/status', async (_req, res) => {
  const bitnet = await bitnetHealth();
  res.json(getResearchStatus(bitnet));
});

app.get('/api/research/bitnet/runs', (req, res) => {
  const limit = Math.min(Number(req.query.limit) || 50, 500);
  res.json({ runs: readRecentRuns(limit) });
});

app.post('/api/research/bitnet/infer', async (req, res) => {
  const started = Date.now();
  const userQuery = lastUserText(req.body);
  const taskClass = normalizeTaskClass(req.body, req);
  const laneHeader = (req.get('X-S2-Inference-Lane') || '').toLowerCase();
  const useBitnet =
    BITNET_ENABLED &&
    (laneHeader === 'compact' ||
      laneHeader === 'bitnet' ||
      req.body.inference_lane === 'bitnet' ||
      resolveInferenceLane(req.body, req) === 'bitnet');
  const maxTokens = Number(req.body.max_tokens) || Number(req.body.max_length) || 256;
  const temperature = Number(req.body.temperature ?? 0.2);

  try {
    let result;
    let lane;
    if (useBitnet && !bitnetLaneBlocked(req.body)) {
      const bitnet = await bitnetHealth();
      if (!bitnet.ok) {
        return res.status(503).json({ ok: false, error: bitnet.error || 'BitNet sidecar unavailable' });
      }
      result = await bitnetChat({
        messages: [{ role: 'user', content: userQuery }],
        maxTokens,
        temperature,
        taskClass,
      });
      lane = 'bitnet';
    } else {
      const o = await ollamaChat({
        messages: [{ role: 'user', content: userQuery }],
        maxTokens,
        temperature,
      });
      result = { ...o, quantization_bits: 4, memory_mb: null };
      lane = 'baseline';
    }

    const latencyMs = Date.now() - started;
    res.json({
      ok: true,
      content: result.content || result.response,
      response: result.content || result.response,
      model: result.model,
      lane,
      task_class: taskClass,
      latency_ms: result.latency_ms ?? latencyMs,
      quantization_bits: result.quantization_bits ?? (lane === 'bitnet' ? 1.58 : 4),
      memory_mb: result.memory_mb ?? null,
      prompt_tokens: result.prompt_tokens ?? null,
      completion_tokens: result.completion_tokens ?? null,
      stub_mode: result.stub_mode ?? false,
    });
  } catch (e) {
    res.status(e.statusCode || 500).json({ ok: false, error: e.message || String(e) });
  }
});

app.post('/api/research/bitnet/record-batch', (req, res) => {
  const runs = Array.isArray(req.body?.runs) ? req.body.runs : [];
  const recorded = [];
  for (const run of runs) {
    recorded.push(
      recordBenchmarkRun({
        runType: req.body.run_type || 'benchmark',
        lane: run.lane,
        taskClass: run.task_class,
        promptId: run.prompt_id,
        modelId: run.model_id,
        latencyMs: run.latency_ms,
        qualityScore: run.quality_score,
        hallucinationFlag: run.hallucination_flag,
        responsePreview: run.response_preview,
        quantizationBits: run.quantization_bits,
        memoryMb: run.memory_mb,
        baselineLatencyMs: run.baseline_latency_ms,
        baselineQualityScore: run.baseline_quality_score,
      }),
    );
  }
  res.json({ ok: true, recorded: recorded.length, runs: recorded });
});

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
  const started = Date.now();
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
    const body = { ...req.body, exploration: true, product_id: productId };
    const morphicPolicy = resolveMorphicPolicy({
      ...body,
      task_type: body.task_type || 'exploration',
    });
    const productTemp = resolveTemperature(req, {
      endpointDefault: Number(process.env.OLLAMA_EXPLORATION_TEMPERATURE || 0.15),
      productFallback: productId,
    });
    const temperature = applyProfileTemperature(productTemp, morphicPolicy);
    const maxTokens = applyInferenceDepth(body, req.body.max_tokens ?? 3000, morphicPolicy);
    const useEnsemble = ensembleEnabled(body, productId, req);
    const ensembleMode = useEnsemble ? resolveEnsembleMode(body, req) : null;

    let continuity;
    let result;
    let source;
    let ensembleMeta = null;

    async function explorationChat(msgs) {
      if (useHosted) {
        const o = await ollamaChat({ messages: msgs, maxTokens, temperature });
        return { content: o.content, model: o.model, _source: 'hosted-ollama-exploration' };
      }
      const g = await groqChat({
        apiKey: groqKey,
        messages: msgs,
        maxTokens,
        temperature,
      });
      return { content: g.content, model: g.model, _source: 'groq-exploration' };
    }

    if (useEnsemble) {
      const collapsed = await runPslaEnsembleCollapse({
        body,
        req,
        userQuery,
        ownerId: ownerId || 'global',
        productId,
        morphicPolicy,
        mode: ensembleMode,
        maxTokens,
        temperature,
        chatFn: async ({ messages: msgs }) => explorationChat(msgs),
      });
      continuity = collapsed.continuity;
      result = { content: collapsed.content, model: collapsed.model };
      source = collapsed.source;
      ensembleMeta = collapsed.ensemble;
    } else {
      continuity = assembleContinuity(body, userQuery, ownerId || 'global', morphicPolicy);
      const messages = buildExplorationChatMessages(body, continuity.rag.text);
      const r = await explorationChat(messages);
      result = { content: r.content, model: r.model };
      source = r._source;
    }

    recordChatSample({
      productId,
      cadence: continuity.cadence.cadence,
      morphicDimension: morphicPolicy.dimension,
      morphicLabel: morphicPolicy.label,
      profileKey: morphicPolicy.profileKey,
      inferenceAxes: morphicPolicy.axes,
      ensemble: Boolean(ensembleMeta),
      ensembleStrategy: ensembleMeta?.strategy,
      disagreement: ensembleMeta?.disagreement,
      latencyMs: Date.now() - started,
      ragChunks: continuity.rag.chunks.length,
      temperature,
      source,
    });

    res.json({
      success: true,
      content: result.content,
      response: result.content,
      model: result.model,
      source,
      rag_used: continuity.rag.chunks.length > 0,
      cadence: continuity.cadence.cadence,
      product: 'psla-exploration',
      temperature,
      morphic_resonance: morphicPolicy.dimension,
      morphic_label: morphicPolicy.label,
      inference_profile: morphicPolicy.axes,
      inference_profile_key: morphicPolicy.profileKey,
      inference_source: morphicPolicy.source,
      ensemble: ensembleMeta,
      processing_time_ms: Date.now() - started,
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

mountMindGamesPlugin(app);

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
  console.log(
    `  Morphic resonance: ${process.env.MORPHIC_RESONANCE || 1.58} (interval inference policy)`,
  );
  console.log(
    `  PSLA ensemble: opt-in (default mode=${process.env.ENSEMBLE_DEFAULT_MODE || 'cheap'}, auto_all_psla=${process.env.ENSEMBLE_PSLA_COLLAPSE === 'true'})`,
  );
  console.log(
    `  BitNet lane: enabled=${BITNET_ENABLED} url=${process.env.BITNET_BASE_URL || 'http://127.0.0.1:8120'}`,
  );
  console.log('  Mind Games plugin: /api/plugins/mind-games (strengths, progress, achievements)');
});
