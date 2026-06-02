/**
 * Route specialist tasks to BitNet 1.58-bit lane; synthesis on 4-bit/Ollama.
 * Supports explicit lane: hosted | bitnet | auto
 */

const { ENABLED: BITNET_ENABLED } = require('./bitnet');
const { hasBitnetAdapter, normalizeId } = require('./egregore-registry');

/** Task classes eligible for compact BitNet lane (not legal/synthesis/long-form). */
const BITNET_TASK_CLASSES = new Set([
  'summary',
  'summarize',
  'classification',
  'classify',
  'routing',
  'route',
  'tagging',
  'tag',
  'compact',
  'cheap_qa',
  'qa_short',
]);

function normalizeTaskClass(body = {}, req) {
  const fromHeader = (req?.get?.('X-S2-Task-Class') || req?.get?.('x-s2-task-class') || '').trim();
  const fromLane = (req?.get?.('X-S2-Inference-Lane') || req?.get?.('x-s2-inference-lane') || '').trim();
  const raw =
    body.task_class ||
    body.taskClass ||
    fromHeader ||
    (fromLane === 'compact' || fromLane === 'bitnet' ? 'compact' : '');
  return String(raw || '').toLowerCase().replace(/\s+/g, '_');
}

function wantsBitnetLane(body = {}, req) {
  const mode = (req?.get?.('X-S2-Inference') || body.inference || '').toLowerCase();
  if (mode === 'bitnet' || mode === 'compact' || mode === '1.58') return true;

  const lane = (req?.get?.('X-S2-Inference-Lane') || body.inference_lane || body.inferenceLane || '').toLowerCase();
  if (lane === 'bitnet' || lane === 'compact' || lane === '1.58') return true;

  const taskClass = normalizeTaskClass(body, req);
  if (BITNET_TASK_CLASSES.has(taskClass)) return true;

  if (body.use_bitnet === true || body.useBitnet === true) return true;
  return false;
}

function bitnetLaneBlocked(body = {}) {
  const context = String(body.context || '').toLowerCase();
  if (context === 'legal') return 'legal_context';
  if (body.long_form === true || body.longForm === true) return 'long_form';
  const egregoreId = normalizeId(body.egregore_id || body.egregore || 'ake');
  const voice = String(body.voice_mode || body.voiceMode || '').toLowerCase();
  // Ake synthesis stays on 4-bit; user egregores may use 1.58-bit with persona
  if (voice === 'synthesis' && egregoreId === 'ake') return 'synthesis_voice';
  if (body.ensemble === true || body.ensemble_mode) return 'ensemble';
  return null;
}

function resolveExplicitLane(body = {}, req) {
  const raw = (
    req?.get?.('X-S2-Inference-Lane') ||
    body.inference_lane ||
    body.inferenceLane ||
    ''
  )
    .toLowerCase()
    .trim();
  if (raw === 'hosted' || raw === 'ollama' || raw === '4bit' || raw === '4-bit') return 'hosted';
  if (raw === 'bitnet' || raw === 'compact' || raw === '1.58') return 'bitnet';
  if (raw === 'auto') return 'auto';
  return null;
}

/**
 * @returns {'bitnet'|'hosted'|null} null = default hosted routing
 */
function resolveInferenceLane(body = {}, req) {
  if (!BITNET_ENABLED) return null;

  const explicit = resolveExplicitLane(body, req);
  if (explicit === 'hosted') return null;
  if (explicit === 'bitnet') {
    const blocked = bitnetLaneBlocked(body);
    return blocked ? null : 'bitnet';
  }

  const egregoreId = normalizeId(body.egregore_id || body.egregore || 'ake');
  if (explicit === 'auto' && hasBitnetAdapter(egregoreId)) {
    const blocked = bitnetLaneBlocked(body);
    if (!blocked) return 'bitnet';
  }

  if (!wantsBitnetLane(body, req)) return null;
  const blocked = bitnetLaneBlocked(body);
  if (blocked) return null;
  return 'bitnet';
}

module.exports = {
  BITNET_TASK_CLASSES,
  normalizeTaskClass,
  wantsBitnetLane,
  bitnetLaneBlocked,
  resolveExplicitLane,
  resolveInferenceLane,
};
