/**
 * Three-axis inference profiles (Precision / Context / Synthesis) + Depth.
 * Public morphic_resonance (1.58–1.618) remains the user-facing bias dial;
 * task profiles map axes to decoupled gateway knobs.
 */

const {
  INTERVAL_START,
  INTERVAL_END,
  INTERVAL_WIDTH,
  resolveMorphicDimension,
  intervalPosition,
} = require('./morphic-dimension');

/** @typedef {{ precision: number, context: number, synthesis: number, depth: number }} AxisValues */

/** Base profiles (0–100). Keys match task_type / detectProfile(). */
const TASK_PROFILES = {
  legal: { precision: 95, context: 90, synthesis: 30, depth: 65 },
  coding: { precision: 75, context: 85, synthesis: 50, depth: 80 },
  computation: { precision: 75, context: 85, synthesis: 50, depth: 80 },
  debug: { precision: 75, context: 85, synthesis: 50, depth: 80 },
  analysis: { precision: 85, context: 75, synthesis: 45, depth: 70 },
  strategy: { precision: 65, context: 70, synthesis: 70, depth: 75 },
  exploration: { precision: 65, context: 70, synthesis: 70, depth: 75 },
  philosophy: { precision: 70, context: 55, synthesis: 95, depth: 85 },
  consciousness: { precision: 70, context: 55, synthesis: 95, depth: 85 },
  creativity: { precision: 55, context: 45, synthesis: 95, depth: 70 },
  synthesis: { precision: 65, context: 60, synthesis: 90, depth: 80 },
  default: { precision: 70, context: 65, synthesis: 65, depth: 65 },
};

/** Morphic dimension → internal profile key (public dial → task posture). */
const MORPHIC_PROFILE_HINTS = {
  legal: 'legal',
  coding: 'coding',
  debug: 'debug',
  computation: 'computation',
  analysis: 'analysis',
  strategy: 'strategy',
  exploration: 'exploration',
  philosophy: 'philosophy',
  consciousness: 'consciousness',
  creativity: 'creativity',
  synthesis: 'synthesis',
};

function clamp(n, lo, hi) {
  return Math.min(hi, Math.max(lo, n));
}

function clampAxis(n) {
  return clamp(Math.round(n), 0, 100);
}

function readExplicitProfile(body = {}) {
  const raw = body.inference_profile ?? body.inferenceProfile;
  if (!raw || typeof raw !== 'object') return null;
  const out = {};
  for (const key of ['precision', 'context', 'synthesis', 'depth']) {
    if (raw[key] != null) {
      const v = Number(raw[key]);
      if (Number.isFinite(v)) out[key] = clampAxis(v);
    }
  }
  return Object.keys(out).length ? out : null;
}

function queryText(body = {}) {
  return [
    body.text,
    body.user_message,
    body.userMessage,
    body.case_context,
    body.caseContext,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

/**
 * Resolve task profile key from request context (before morphic bias).
 */
function detectProfileKey(body = {}) {
  const task = String(body.task_type || body.taskType || '').toLowerCase();
  if (task && TASK_PROFILES[task]) return task;
  if (task && MORPHIC_PROFILE_HINTS[task]) return MORPHIC_PROFILE_HINTS[task];

  const ctx = String(body.context || 'general').toLowerCase();
  const product = String(body.product_id || body.productId || '').toLowerCase();

  if (
    ctx === 'legal' ||
    product.includes('psla') ||
    product.includes('prose') ||
    product.includes('pro-se') ||
    body.government_defendant_focus ||
    body.governmentDefendantFocus
  ) {
    return 'legal';
  }

  const text = queryText(body);
  if (/rule 12|motion to dismiss|qualified immunity|filing deadline|§\s*\d/i.test(text)) {
    return 'legal';
  }

  if (
    /debug|stack trace|error:|exception|traceback|undefined is not|typeerror|syntaxerror/i.test(
      text,
    )
  ) {
    return 'debug';
  }

  if (
    /```|function\s+\w+|const\s+\w+\s*=|import\s+|def\s+\w+|npm run|git diff|pull request/i.test(
      text,
    )
  ) {
    return 'coding';
  }

  if (/architecture|deploy|pipeline|gateway|api\b|infra/i.test(text)) {
    return 'coding';
  }

  if (/deep key|ninefold|symbolic|threshold|egregore|philosoph/i.test(text)) {
    return 'philosophy';
  }

  if (body.exploration || product.includes('exploration')) {
    return 'exploration';
  }

  if (/brainstorm|creative|ideate|imagine|what if/i.test(text)) {
    return 'creativity';
  }

  return 'default';
}

/**
 * Layer morphic interval position as a user bias on top of the task profile.
 * Low position → efficiency (+precision, −context/synthesis).
 * High position → ability (−precision, +context/synthesis).
 */
function applyMorphicBias(axes, position, profileKey = 'default') {
  const efficiencyBias = (0.5 - position) * 20;
  const expansive = ['philosophy', 'consciousness', 'creativity', 'synthesis'].includes(profileKey);
  const retrievalHeavy = ['legal', 'coding', 'debug', 'computation', 'analysis'].includes(profileKey);
  const synthesisScale = expansive ? 0.25 : 1;
  const contextScale = retrievalHeavy ? 0.35 : 0.6;
  return {
    precision: clampAxis(axes.precision + efficiencyBias),
    context: clampAxis(axes.context - efficiencyBias * contextScale),
    synthesis: clampAxis(axes.synthesis - efficiencyBias * synthesisScale),
    depth: clampAxis(axes.depth - efficiencyBias * 0.3),
  };
}

function mergeAxes(base, override) {
  if (!override) return { ...base };
  return {
    precision: override.precision ?? base.precision,
    context: override.context ?? base.context,
    synthesis: override.synthesis ?? base.synthesis,
    depth: override.depth ?? base.depth,
  };
}

function axesToKnobs(axes) {
  const tempMin = Number(process.env.MORPHIC_TEMP_MIN || 0.1);
  const tempMax = Number(process.env.MORPHIC_TEMP_MAX || 0.38);

  const ragMin = Number(process.env.MORPHIC_RAG_LIMIT_MIN || 3);
  const ragMax = Number(process.env.MORPHIC_RAG_LIMIT_MAX || 12);

  const charsMin = Number(process.env.MORPHIC_RAG_CHARS_MIN || 2200);
  const charsMax = Number(process.env.MORPHIC_RAG_CHARS_MAX || 4800);

  const precisionFrac = axes.precision / 100;
  const contextFrac = axes.context / 100;
  const synthesisFrac = axes.synthesis / 100;

  let temperature = tempMin + (1 - precisionFrac) * (tempMax - tempMin);
  temperature += (synthesisFrac - 0.5) * 0.08;
  temperature = clamp(temperature, tempMin, tempMax);

  const ragLimit = Math.round(ragMin + contextFrac * (ragMax - ragMin));
  const ragMaxChars = Math.round(charsMin + contextFrac * (charsMax - charsMin));

  const tempBlendWeight = clamp(
    Number(process.env.MORPHIC_TEMP_BLEND_MIN || 0.2) +
      precisionFrac * Number(process.env.MORPHIC_TEMP_BLEND_SPAN || 0.3),
    0,
    1,
  );

  const depthMultiplier = clamp(
    Number(process.env.INFERENCE_DEPTH_MULT_MIN || 0.75) +
      (axes.depth / 100) * Number(process.env.INFERENCE_DEPTH_MULT_SPAN || 0.5),
    0.5,
    1.5,
  );

  const label =
    precisionFrac >= 0.85 && contextFrac >= 0.75
      ? 'grounded'
      : synthesisFrac >= 0.85
        ? 'expansive'
        : contextFrac >= 0.8
          ? 'retrieval-heavy'
          : precisionFrac >= 0.8
            ? 'efficiency'
            : synthesisFrac >= 0.75
              ? 'balanced-ability'
              : 'balance';

  return {
    temperature,
    ragLimit,
    ragMaxChars,
    tempBlendWeight,
    depthMultiplier,
    label,
  };
}

/**
 * @param {object} [body]
 * @returns {{
 *   dimension: number,
 *   position: number,
 *   temperature: number,
 *   ragLimit: number,
 *   ragMaxChars: number,
 *   tempBlendWeight: number,
 *   depthMultiplier: number,
 *   label: string,
 *   source: string,
 *   profileKey: string,
 *   axes: AxisValues,
 *   interval: { start: number, end: number, width: number },
 * }}
 */
function resolveInferenceProfile(body = {}) {
  const morphic = resolveMorphicDimension(body);
  const position = intervalPosition(morphic.dimension);

  const profileKey = detectProfileKey(body);
  const baseAxes = { ...TASK_PROFILES[profileKey] };
  let axes = applyMorphicBias(baseAxes, position, profileKey);

  const explicit = readExplicitProfile(body);
  let source = explicit ? 'inference_profile' : `profile:${profileKey}`;
  if (explicit) {
    axes = mergeAxes(axes, explicit);
  }

  if (morphic.source === 'request' && !explicit) {
    source = `morphic:${source}`;
  } else if (morphic.source === 'env' && !explicit && profileKey === 'default') {
    source = 'env';
  }

  const knobs = axesToKnobs(axes);

  return {
    dimension: morphic.dimension,
    position,
    ...knobs,
    source,
    profileKey,
    axes,
    interval: { start: INTERVAL_START, end: INTERVAL_END, width: INTERVAL_WIDTH },
    morphicSource: morphic.source,
  };
}

/**
 * Blend product temperature with profile-derived temperature.
 */
function applyProfileTemperature(productTemp, profile) {
  if (productTemp == null || !profile) return profile?.temperature ?? 0.2;
  const profileTemp = profile.temperature;
  const weight = profile.tempBlendWeight ?? Number(process.env.MORPHIC_TEMP_BLEND || 0.35);
  return productTemp * weight + profileTemp * (1 - weight);
}

/**
 * Apply depth axis when client did not set an explicit max_tokens budget.
 */
function applyInferenceDepth(body = {}, baseMaxTokens, profile) {
  const explicit = body.max_tokens ?? body.maxTokens;
  if (explicit != null && explicit !== '') {
    return Number(explicit);
  }
  const mult = profile?.depthMultiplier ?? 1;
  return Math.round(Number(baseMaxTokens) * mult);
}

module.exports = {
  TASK_PROFILES,
  detectProfileKey,
  resolveInferenceProfile,
  applyProfileTemperature,
  applyInferenceDepth,
  axesToKnobs,
  applyMorphicBias,
};
