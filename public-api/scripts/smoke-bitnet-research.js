#!/usr/bin/env node
/**
 * Smoke test BitNet research lane (no live sidecar required if stub running).
 */
process.env.BITNET_ENABLED = 'true';

const assert = require('assert');
const {
  resolveInferenceLane,
  normalizeTaskClass,
  bitnetLaneBlocked,
} = require('../lib/inference-lane-router');
const { summarizeRuns } = require('../lib/bitnet-research-metrics');

assert.strictEqual(
  resolveInferenceLane({ task_class: 'summary', context: 'general' }, { get: () => '' }),
  'bitnet',
);
assert.strictEqual(
  resolveInferenceLane({ context: 'legal', task_class: 'summary' }, { get: () => '' }),
  null,
);
assert.strictEqual(bitnetLaneBlocked({ context: 'legal' }), 'legal_context');
assert.strictEqual(normalizeTaskClass({ taskClass: 'routing' }, {}), 'routing');

const summary = summarizeRuns([
  { lane: 'bitnet', latency_ms: 29, quality_score: 0.72 },
  { lane: 'baseline', latency_ms: 120, quality_score: 0.81 },
]);
assert.strictEqual(summary.bitnet_runs, 1);
assert.strictEqual(summary.baseline_runs, 1);

console.log('smoke:bitnet OK');
