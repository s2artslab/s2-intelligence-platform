/**
 * PSLA ensemble collapse — opt-in; default cheap path (1 LLM + general RAG).
 * Full dual-LLM available via ensemble_mode: "full" (lab / explicit only).
 */

const { assembleContinuity } = require('./continuity');
const { buildGatewayMessages, resolveVoiceMode } = require('./prompts');
const { buildExplorationChatMessages } = require('./exploration-prompts');

function tokenSet(text) {
  return new Set(
    String(text || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length > 3),
  );
}

/**
 * Jaccard distance on content tokens (0 = identical, 1 = disjoint).
 */
function disagreementScore(a, b) {
  const sa = tokenSet(a);
  const sb = tokenSet(b);
  if (!sa.size && !sb.size) return 0;
  let inter = 0;
  for (const t of sa) {
    if (sb.has(t)) inter += 1;
  }
  const union = sa.size + sb.size - inter || 1;
  return 1 - inter / union;
}

function isPslaProduct(productId) {
  const p = String(productId || '').toLowerCase();
  return p.includes('psla') || p.includes('pro-se') || p.includes('prose');
}

function headerEnsemble(req) {
  if (!req?.get) return '';
  return String(req.get('X-S2-Ensemble') || req.get('x-s2-ensemble') || '').trim().toLowerCase();
}

/**
 * Production default: off. Opt in per request (body or header).
 * Env ENSEMBLE_PSLA_COLLAPSE=true only forces opt-in for all PSLA (lab legacy).
 */
function ensembleEnabled(body, productId, req) {
  if (body.ensemble === false || body.ensemble_collapse === false) return false;
  if (!isPslaProduct(productId)) return false;

  const hdr = headerEnsemble(req);
  if (hdr === 'false' || hdr === '0' || hdr === 'off') return false;

  if (body.ensemble === true || body.ensemble_collapse === true) return true;

  const mode = String(body.ensemble_mode || body.ensembleMode || body.ensemble || '').toLowerCase();
  if (mode === 'cheap' || mode === 'full' || mode === 'dual') return true;

  if (hdr === 'true' || hdr === '1' || hdr === 'cheap' || hdr === 'full' || hdr === 'dual') {
    return true;
  }

  if (process.env.ENSEMBLE_PSLA_COLLAPSE === 'true') return true;

  return false;
}

/** @returns {'cheap'|'full'} */
function resolveEnsembleMode(body, req) {
  const mode = String(body.ensemble_mode || body.ensembleMode || body.ensemble || '').toLowerCase();
  if (mode === 'full' || mode === 'dual') return 'full';

  const hdr = headerEnsemble(req);
  if (hdr === 'full' || hdr === 'dual') return 'full';

  if (process.env.ENSEMBLE_DEFAULT_MODE === 'full') return 'full';
  return 'cheap';
}

function buildPathMessages(body, userQuery, ownerId, context, morphicPolicy) {
  const pathBody = {
    ...body,
    context,
    rag_limit: body.rag_limit ?? morphicPolicy.ragLimit,
    rag_max_chars: body.rag_max_chars ?? morphicPolicy.ragMaxChars,
  };
  const continuity = assembleContinuity(pathBody, userQuery, ownerId, morphicPolicy);
  const messages = pathBody.exploration
    ? buildExplorationChatMessages(pathBody, continuity.rag.text)
    : buildGatewayMessages(pathBody, continuity.rag.text, {
        canonBlock: continuity.canonBlock,
        tensionBlock: continuity.tensionBlock,
        cadenceOverlay: continuity.cadence.overlay,
      });
  return { messages, continuity };
}

function collapseContent({
  legalText,
  generalText,
  disagreement,
  productId,
  threshold,
  holdThreshold,
  generalLabel,
}) {
  let content;
  let strategy;

  if (disagreement < threshold) {
    content = legalText;
    strategy = 'collapse_legal_agree';
  } else if (disagreement >= holdThreshold && productId.includes('exploration')) {
    content = [
      '**Legal frame (procedural):**',
      legalText.trim(),
      '',
      `**${generalLabel}:**`,
      generalText.trim(),
      '',
      '_These frames diverge — verify jurisdiction, deadlines, and facts before acting. Deep Key: hold the threshold, do not flatten._',
    ].join('\n');
    strategy = 'threshold_hold_dual';
  } else if (disagreement >= holdThreshold) {
    content = [
      legalText.trim(),
      '',
      '---',
      '',
      '_Note: A broader reading of your question differs on emphasis. If procedure and substance conflict, prioritize court deadlines and local rules._',
    ].join('\n');
    strategy = 'legal_with_tension_note';
  } else {
    content = legalText;
    strategy = 'collapse_legal_primary';
  }

  return { content, strategy };
}

/**
 * One LLM call (legal). General "path" = retrieved chunks only — no second inference.
 */
async function runPslaCheapEnsembleCollapse({
  body,
  userQuery,
  ownerId,
  productId,
  morphicPolicy,
  maxTokens,
  temperature,
  chatFn,
}) {
  const threshold = Number(process.env.ENSEMBLE_DISAGREEMENT_THRESHOLD || 0.28);
  const holdThreshold = Number(process.env.ENSEMBLE_HOLD_THRESHOLD || 0.42);
  const generalMaxChars = Number(process.env.ENSEMBLE_CHEAP_GENERAL_MAX_CHARS || 1200);

  const started = Date.now();
  const [legalPath, generalPath] = await Promise.all([
    buildPathMessages(body, userQuery, ownerId, 'legal', morphicPolicy),
    buildPathMessages(body, userQuery, ownerId, 'general', morphicPolicy),
  ]);

  const legalResult = await chatFn({
    messages: legalPath.messages,
    maxTokens,
    temperature,
    path: 'legal',
  });

  const legalText = legalResult.content || legalResult.response || '';
  let generalText = (generalPath.continuity.rag.text || '').trim();
  if (generalText.length > generalMaxChars) {
    generalText = `${generalText.slice(0, generalMaxChars)}…`;
  }
  if (!generalText) {
    generalText =
      '(No general-context retrieval overlapped this query — legal path only.)';
  }

  const disagreement = disagreementScore(legalText, generalText);
  const { content, strategy } = collapseContent({
    legalText,
    generalText,
    disagreement,
    productId,
    threshold,
    holdThreshold,
    generalLabel: 'Broader reference (retrieved)',
  });

  return {
    content,
    model: legalResult.model,
    source: 'ensemble-collapse-cheap',
    ensemble: {
      mode: 'cheap',
      strategy,
      disagreement,
      latency_ms: Date.now() - started,
      paths: ['legal', 'general-rag'],
      inference_calls: 1,
      general_source: 'rag',
      legal_rag_chunks: legalPath.continuity.rag.chunks.length,
      general_rag_chunks: generalPath.continuity.rag.chunks.length,
    },
    continuity: legalPath.continuity,
    voiceMode: resolveVoiceMode(body),
  };
}

/** Two full LLM paths — lab / explicit ensemble_mode: full only. */
async function runPslaFullEnsembleCollapse({
  body,
  userQuery,
  ownerId,
  productId,
  morphicPolicy,
  maxTokens,
  temperature,
  chatFn,
}) {
  const threshold = Number(process.env.ENSEMBLE_DISAGREEMENT_THRESHOLD || 0.28);
  const holdThreshold = Number(process.env.ENSEMBLE_HOLD_THRESHOLD || 0.42);

  const [legalPath, generalPath] = await Promise.all([
    buildPathMessages(body, userQuery, ownerId, 'legal', morphicPolicy),
    buildPathMessages(body, userQuery, ownerId, 'general', morphicPolicy),
  ]);

  const started = Date.now();
  const [legalResult, generalResult] = await Promise.all([
    chatFn({
      messages: legalPath.messages,
      maxTokens,
      temperature,
      path: 'legal',
    }),
    chatFn({
      messages: generalPath.messages,
      maxTokens,
      temperature,
      path: 'general',
    }),
  ]);

  const legalText = legalResult.content || legalResult.response || '';
  const generalText = generalResult.content || generalResult.response || '';
  const disagreement = disagreementScore(legalText, generalText);
  const { content, strategy } = collapseContent({
    legalText,
    generalText,
    disagreement,
    productId,
    threshold,
    holdThreshold,
    generalLabel: 'Broader frame',
  });

  return {
    content,
    model: legalResult.model || generalResult.model,
    source: 'ensemble-collapse-full',
    ensemble: {
      mode: 'full',
      strategy,
      disagreement,
      latency_ms: Date.now() - started,
      paths: ['legal', 'general'],
      inference_calls: 2,
      general_source: 'llm',
      legal_rag_chunks: legalPath.continuity.rag.chunks.length,
      general_rag_chunks: generalPath.continuity.rag.chunks.length,
    },
    continuity: legalPath.continuity,
    voiceMode: resolveVoiceMode(body),
  };
}

/**
 * @param {object} opts
 * @param {'cheap'|'full'} [opts.mode]
 * @param {Function} opts.chatFn
 */
async function runPslaEnsembleCollapse(opts) {
  const mode = opts.mode || resolveEnsembleMode(opts.body, opts.req);
  if (mode === 'full') {
    return runPslaFullEnsembleCollapse(opts);
  }
  return runPslaCheapEnsembleCollapse(opts);
}

module.exports = {
  disagreementScore,
  isPslaProduct,
  ensembleEnabled,
  resolveEnsembleMode,
  runPslaEnsembleCollapse,
  runPslaCheapEnsembleCollapse,
  runPslaFullEnsembleCollapse,
};
