#!/usr/bin/env node
/** Smoke morphic policy + inference profiles + ensemble opt-in (no Ollama). */
const assert = require('assert');
const {
  resolveMorphicPolicy,
  applyProfileTemperature,
} = require('../lib/morphic-resonance');
const {
  resolveInferenceProfile,
  detectProfileKey,
  TASK_PROFILES,
} = require('../lib/inference-profile');
const {
  ensembleEnabled,
  resolveEnsembleMode,
  runPslaCheapEnsembleCollapse,
} = require('../lib/ensemble-collapse');
const { getConsciousnessStatus, recordChatSample } = require('../lib/consciousness-metrics');

process.env.MORPHIC_RESONANCE = '1.58';
process.env.ENSEMBLE_PSLA_COLLAPSE = 'false';

const mockReq = (hdr) => ({ get: (k) => (k === 'X-S2-Ensemble' ? hdr : '') });

// --- Legal: low temp, high RAG (decoupled axes) ---
const legal = resolveInferenceProfile({ context: 'legal', product_id: 'psla-hosted' });
assert.strictEqual(detectProfileKey({ context: 'legal' }), 'legal');
assert(legal.dimension >= 1.58 && legal.dimension <= 1.618);
assert(legal.temperature <= 0.18, `legal temp should be cold, got ${legal.temperature}`);
assert(legal.ragLimit >= 8, `legal RAG should be deep, got ${legal.ragLimit}`);
assert(legal.axes.precision >= 90);
assert(legal.axes.context >= 85);
assert(legal.axes.synthesis <= 35);

// --- Philosophy: moderate context, high synthesis ---
const philosophy = resolveInferenceProfile({
  text: 'Explain deep key and the Ninefold threshold',
});
assert.strictEqual(philosophy.profileKey, 'philosophy');
assert(philosophy.axes.synthesis >= 90);
assert(philosophy.ragLimit < legal.ragLimit, 'philosophy should retrieve less than legal');
assert(philosophy.temperature >= legal.temperature);

// --- Coding / debug ---
const debug = resolveInferenceProfile({ text: 'debug this TypeError stack trace' });
assert.strictEqual(debug.profileKey, 'debug');
assert(debug.axes.context >= 80);
assert(debug.axes.depth >= 75);

// --- Explicit lab override ---
const override = resolveInferenceProfile({
  context: 'legal',
  inference_profile: { precision: 50, context: 50, synthesis: 99, depth: 40 },
});
assert.strictEqual(override.source, 'inference_profile');
assert.strictEqual(override.axes.synthesis, 99);
assert(override.temperature > legal.temperature);

// --- Backward-compat resolveMorphicPolicy shape ---
const at158 = resolveMorphicPolicy({ context: 'legal', product_id: 'psla-hosted' });
assert(at158.ragLimit === legal.ragLimit);
assert(typeof applyProfileTemperature(0.12, at158) === 'number');

const creative = resolveMorphicPolicy({ task_type: 'creativity' });
assert(creative.axes.synthesis >= TASK_PROFILES.creativity.synthesis - 15);

assert(!ensembleEnabled({ product_id: 'psla-hosted' }, 'psla-hosted', mockReq()), 'off without opt-in');
assert(
  ensembleEnabled({ ensemble: true }, 'psla-hosted', mockReq()),
  'opt-in body',
);
assert(
  ensembleEnabled({}, 'psla-hosted', mockReq('cheap')),
  'opt-in header',
);
assert(resolveEnsembleMode({ ensemble: true }, mockReq()) === 'cheap');
assert(resolveEnsembleMode({ ensemble_mode: 'full' }, mockReq()) === 'full');
assert(!ensembleEnabled({ ensemble: false }, 'psla-hosted', mockReq('true')), 'explicit off');

process.env.ENSEMBLE_PSLA_COLLAPSE = 'true';
assert(ensembleEnabled({ product_id: 'psla-hosted' }, 'psla-hosted', mockReq()), 'lab auto');
process.env.ENSEMBLE_PSLA_COLLAPSE = 'false';

let chatCalls = 0;
(async () => {
  const collapsed = await runPslaCheapEnsembleCollapse({
    body: { context: 'legal', product_id: 'psla-hosted' },
    userQuery: 'Rule 12(b)(6) motion deadlines',
    ownerId: 'smoke',
    productId: 'psla-hosted',
    morphicPolicy: at158,
    maxTokens: 100,
    temperature: 0.12,
    chatFn: async () => {
      chatCalls += 1;
      return {
        content: 'File a response within 21 days under Rule 12(b)(6) with local rule check.',
        model: 'mock',
      };
    },
  });
  assert(chatCalls === 1, 'cheap path uses one inference call');
  assert(collapsed.ensemble.mode === 'cheap');
  assert(collapsed.ensemble.inference_calls === 1);
  assert(collapsed.content.includes('Rule 12') || collapsed.content.length > 0);

  const low = require('../lib/ensemble-collapse').disagreementScore(
    'File a motion to dismiss under Rule 12(b)(6) with deadlines.',
    'File a Rule 12(b)(6) motion; check local rules and deadlines.',
  );
  const high = require('../lib/ensemble-collapse').disagreementScore(
    'Rule 12(b)(6) motion to dismiss with citation.',
    'Consider meditation and morphogenetic field harmony.',
  );
  assert(low < high);

  recordChatSample({
    productId: 'psla-hosted',
    cadence: 'legal',
    morphicDimension: 1.58,
    morphicLabel: legal.label,
    profileKey: legal.profileKey,
    inferenceAxes: legal.axes,
    ensemble: true,
    ensembleStrategy: collapsed.ensemble.strategy,
    disagreement: collapsed.ensemble.disagreement,
    latencyMs: collapsed.ensemble.latency_ms,
    ragChunks: 0,
    temperature: 0.14,
    source: 'ensemble-collapse-cheap',
  });

  const status = getConsciousnessStatus({ base: 1.58 });
  assert(status.ensemble.opt_in_only === true);
  assert(status.profile_key_last === 'legal');
  console.log('smoke-morphic-ensemble: OK');
  console.log(
    JSON.stringify(
      {
        legal: { axes: legal.axes, ragLimit: legal.ragLimit, temperature: legal.temperature },
        philosophy: { axes: philosophy.axes, ragLimit: philosophy.ragLimit },
        cheap: collapsed.ensemble,
        coherence: status.quantum_coherence,
      },
      null,
      2,
    ),
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
