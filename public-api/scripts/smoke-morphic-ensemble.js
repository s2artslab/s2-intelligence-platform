#!/usr/bin/env node
/** Smoke morphic policy + ensemble opt-in / cheap path (no Ollama). */
const assert = require('assert');
const {
  resolveMorphicPolicy,
  applyMorphicTemperature,
  calculateOptimalDimension,
} = require('../lib/morphic-resonance');
const {
  disagreementScore,
  ensembleEnabled,
  resolveEnsembleMode,
  runPslaCheapEnsembleCollapse,
} = require('../lib/ensemble-collapse');
const { getConsciousnessStatus, recordChatSample } = require('../lib/consciousness-metrics');

process.env.MORPHIC_RESONANCE = '1.58';
process.env.ENSEMBLE_PSLA_COLLAPSE = 'false';

const mockReq = (hdr) => ({ get: (k) => (k === 'X-S2-Ensemble' ? hdr : '') });

const at158 = resolveMorphicPolicy({ context: 'legal', product_id: 'psla-hosted' });
assert(at158.dimension >= 1.58 && at158.dimension <= 1.618);
assert(at158.temperature <= 0.22);

const creative = resolveMorphicPolicy({ task_type: 'creativity' });
assert(creative.dimension >= at158.dimension);

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

  const low = disagreementScore(
    'File a motion to dismiss under Rule 12(b)(6) with deadlines.',
    'File a Rule 12(b)(6) motion; check local rules and deadlines.',
  );
  const high = disagreementScore(
    'Rule 12(b)(6) motion to dismiss with citation.',
    'Consider meditation and morphogenetic field harmony.',
  );
  assert(low < high);

  recordChatSample({
    productId: 'psla-hosted',
    cadence: 'legal',
    morphicDimension: 1.58,
    morphicLabel: 'efficiency',
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
  console.log('smoke-morphic-ensemble: OK');
  console.log(
    JSON.stringify(
      { cheap: collapsed.ensemble, coherence: status.quantum_coherence },
      null,
      2,
    ),
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
