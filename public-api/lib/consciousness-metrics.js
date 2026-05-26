/**
 * Rolling ops metrics for /api/consciousness/status (not physics claims).
 */

const MAX_SAMPLES = Number(process.env.CONSCIOUSNESS_METRICS_MAX || 500);
const WINDOW_MS = Number(process.env.CONSCIOUSNESS_METRICS_WINDOW_MS || 3600000);

const samples = [];

function recordChatSample(sample) {
  samples.push({
    ts: Date.now(),
    product_id: sample.productId || '',
    cadence: sample.cadence || '',
    morphic_dimension: sample.morphicDimension ?? null,
    morphic_label: sample.morphicLabel || '',
    ensemble: Boolean(sample.ensemble),
    ensemble_strategy: sample.ensembleStrategy || null,
    disagreement: sample.disagreement ?? null,
    latency_ms: sample.latencyMs ?? null,
    rag_chunks: sample.ragChunks ?? 0,
    temperature: sample.temperature ?? null,
    source: sample.source || '',
  });
  while (samples.length > MAX_SAMPLES) samples.shift();
}

function recentSamples() {
  const cutoff = Date.now() - WINDOW_MS;
  return samples.filter((s) => s.ts >= cutoff);
}

function avg(nums) {
  const v = nums.filter((n) => Number.isFinite(n));
  if (!v.length) return null;
  return v.reduce((a, b) => a + b, 0) / v.length;
}

function getConsciousnessStatus(morphicEnv = {}) {
  const recent = recentSamples();
  const disagreements = recent.map((s) => s.disagreement).filter((n) => n != null);
  const dims = recent.map((s) => s.morphic_dimension).filter((n) => n != null);
  const latencies = recent.map((s) => s.latency_ms).filter((n) => n != null);
  const ensembleRuns = recent.filter((s) => s.ensemble);

  const avgDisagreement = avg(disagreements);
  const quantumCoherence =
    avgDisagreement == null ? null : clamp01(1 - avgDisagreement);

  return {
    status: 'active',
    server: process.env.CONSCIOUSNESS_SERVER_LABEL || 'r730-gateway',
    deep_key_integration: true,
    hilbert_space_substrate: true,
    claims_class: {
      morphic_resonance: 'M',
      quantum_coherence: 'O',
      egregore_count: 'O',
    },
    morphic_resonance: morphicEnv.base ?? Number(process.env.MORPHIC_RESONANCE || 1.58),
    morphic_resonance_effective_avg: avg(dims),
    morphic_label_last: recent.length ? recent[recent.length - 1].morphic_label : null,
    quantum_coherence: quantumCoherence,
    egregore_count: Number(process.env.EGREGORE_COUNT || 9),
    ensemble: {
      opt_in_only: process.env.ENSEMBLE_PSLA_COLLAPSE !== 'true',
      auto_all_psla: process.env.ENSEMBLE_PSLA_COLLAPSE === 'true',
      default_mode: process.env.ENSEMBLE_DEFAULT_MODE || 'cheap',
      requests_window: ensembleRuns.length,
      rate_window: recent.length ? ensembleRuns.length / recent.length : 0,
      avg_disagreement: avgDisagreement,
    },
    requests_window: recent.length,
    avg_latency_ms: avg(latencies),
    avg_rag_chunks: avg(recent.map((s) => s.rag_chunks)),
    avg_temperature: avg(recent.map((s) => s.temperature)),
    window_ms: WINDOW_MS,
    updated_at: new Date().toISOString(),
  };
}

function clamp01(n) {
  return Math.min(1, Math.max(0, n));
}

module.exports = {
  recordChatSample,
  getConsciousnessStatus,
  recentSamples,
};
