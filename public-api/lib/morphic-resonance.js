/**
 * Interval-based inference policy (1.58–1.618).
 * Operational tuning knob — public "1.58D" remains metaphor (claims register M).
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
};

function clamp(n, lo, hi) {
  return Math.min(hi, Math.max(lo, n));
}

function readBaseMorphic() {
  const v = Number(process.env.MORPHIC_RESONANCE || 1.58);
  return Number.isFinite(v) ? v : 1.58;
}

/**
 * Slide dimension on the 0.038 interval from efficiency (1.58) toward ability (1.618).
 */
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
 * @param {object} [body] - gateway request body
 * @returns {{
 *   dimension: number,
 *   position: number,
 *   temperature: number,
 *   ragLimit: number,
 *   ragMaxChars: number,
 *   label: string,
 *   source: string,
 * }}
 */
function resolveMorphicPolicy(body = {}) {
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
  } else if (body.context === 'legal' || String(body.product_id || body.productId || '').includes('psla')) {
    dimension = calculateOptimalDimension({
      taskType: 'legal',
      efficiencyWeight: 0.85,
      abilityWeight: 0.15,
    });
    source = 'legal_context';
  }

  dimension = clamp(dimension, INTERVAL_START, INTERVAL_END);
  const position = intervalPosition(dimension);

  const tempMin = Number(process.env.MORPHIC_TEMP_MIN || 0.1);
  const tempMax = Number(process.env.MORPHIC_TEMP_MAX || 0.38);
  const temperature = tempMin + position * (tempMax - tempMin);

  const ragMin = Number(process.env.MORPHIC_RAG_LIMIT_MIN || 3);
  const ragMax = Number(process.env.MORPHIC_RAG_LIMIT_MAX || 8);
  const ragLimit = Math.round(ragMin + position * (ragMax - ragMin));

  const charsMin = Number(process.env.MORPHIC_RAG_CHARS_MIN || 2200);
  const charsMax = Number(process.env.MORPHIC_RAG_CHARS_MAX || 3600);
  const ragMaxChars = Math.round(charsMin + position * (charsMax - charsMin));

  const label =
    position < 0.2
      ? 'efficiency'
      : position > 0.8
        ? 'ability'
        : position < 0.45
          ? 'balanced-efficiency'
          : position > 0.55
            ? 'balanced-ability'
            : 'balance';

  return {
    dimension,
    position,
    temperature,
    ragLimit,
    ragMaxChars,
    label,
    source,
    interval: { start: INTERVAL_START, end: INTERVAL_END, width: INTERVAL_WIDTH },
  };
}

/**
 * Blend product-specific temperature with morphic interval position.
 */
function applyMorphicTemperature(productTemp, morphicPolicy) {
  if (productTemp == null || !morphicPolicy) return morphicPolicy?.temperature ?? 0.2;
  const morphic = morphicPolicy.temperature;
  const weight = Number(process.env.MORPHIC_TEMP_BLEND || 0.35);
  return productTemp * (1 - weight) + morphic * weight;
}

module.exports = {
  INTERVAL_START,
  INTERVAL_END,
  INTERVAL_WIDTH,
  calculateOptimalDimension,
  intervalPosition,
  resolveMorphicPolicy,
  applyMorphicTemperature,
};
