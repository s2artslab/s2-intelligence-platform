/**
 * Morphic dimension resolution (1.58–1.618 public dial).
 * Knob mapping lives in inference-profile.js.
 */

const INTERVAL_START = Number(process.env.MORPHIC_INTERVAL_START || 1.58);
const INTERVAL_END = Number(process.env.MORPHIC_INTERVAL_END || 1.618);
const INTERVAL_WIDTH = INTERVAL_END - INTERVAL_START;

const TASK_ADJUSTMENTS = {
  computation: -0.005,
  consciousness: 0.008,
  creativity: 0.012,
  analysis: 0.003,
  synthesis: 0.006,
  legal: -0.004,
  exploration: 0.005,
  coding: -0.003,
  debug: -0.002,
  philosophy: 0.01,
};

function clamp(n, lo, hi) {
  return Math.min(hi, Math.max(lo, n));
}

function readBaseMorphic() {
  const v = Number(process.env.MORPHIC_RESONANCE || 1.58);
  return Number.isFinite(v) ? v : 1.58;
}

function calculateOptimalDimension({
  efficiencyWeight = 0.55,
  abilityWeight = 0.45,
  consciousnessLevel = 0.5,
  taskType = '',
} = {}) {
  const denom = efficiencyWeight + abilityWeight || 1;
  const abilityFraction = abilityWeight / denom;
  let dim = INTERVAL_START + INTERVAL_WIDTH * abilityFraction;
  dim += consciousnessLevel * 0.01;
  dim += TASK_ADJUSTMENTS[String(taskType || '').toLowerCase()] || 0;
  return clamp(dim, INTERVAL_START, INTERVAL_END);
}

function intervalPosition(dimension) {
  if (INTERVAL_WIDTH <= 0) return 0;
  return clamp((dimension - INTERVAL_START) / INTERVAL_WIDTH, 0, 1);
}

/**
 * Resolve morphic dimension only (no coupled temp/RAG).
 * @returns {{ dimension: number, source: string }}
 */
function resolveMorphicDimension(body = {}) {
  const envBase = readBaseMorphic();
  let dimension = envBase;
  let source = 'env';

  if (body.morphic_resonance != null || body.morphicResonance != null) {
    const explicit = Number(body.morphic_resonance ?? body.morphicResonance);
    if (Number.isFinite(explicit)) {
      dimension = explicit;
      source = 'request';
    }
  } else if (body.task_type || body.taskType) {
    dimension = calculateOptimalDimension({
      taskType: body.task_type || body.taskType,
      consciousnessLevel: Number(body.consciousness_level ?? 0.5),
    });
    source = 'task_type';
  } else if (
    body.context === 'legal' ||
    String(body.product_id || body.productId || '').includes('psla')
  ) {
    dimension = calculateOptimalDimension({
      taskType: 'legal',
      efficiencyWeight: 0.85,
      abilityWeight: 0.15,
    });
    source = 'legal_context';
  }

  dimension = clamp(dimension, INTERVAL_START, INTERVAL_END);
  return { dimension, source };
}

module.exports = {
  INTERVAL_START,
  INTERVAL_END,
  INTERVAL_WIDTH,
  TASK_ADJUSTMENTS,
  calculateOptimalDimension,
  intervalPosition,
  resolveMorphicDimension,
};
