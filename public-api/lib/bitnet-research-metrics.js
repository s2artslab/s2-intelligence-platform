/**
 * Research metrics for BitNet vs 4-bit comparison (S² Research ingest).
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MAX_RUNS = Number(process.env.BITNET_RESEARCH_MAX_RUNS || 2000);
const DATA_DIR = process.env.BITNET_RESEARCH_DATA_DIR || path.join(__dirname, '..', 'data');
const RUNS_FILE = path.join(DATA_DIR, 'bitnet-research-runs.jsonl');

function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
}

function recordBenchmarkRun(run) {
  ensureDataDir();
  const row = {
    id: run.id || crypto.randomUUID(),
    ts: run.ts || new Date().toISOString(),
    run_type: run.runType || run.run_type || 'single',
    lane: run.lane || 'bitnet',
    task_class: run.taskClass || run.task_class || '',
    prompt_id: run.promptId || run.prompt_id || '',
    model_id: run.modelId || run.model_id || '',
    baseline_model_id: run.baselineModelId || run.baseline_model_id || '',
    quantization_bits: run.quantizationBits ?? run.quantization_bits ?? null,
    latency_ms: run.latencyMs ?? run.latency_ms ?? null,
    baseline_latency_ms: run.baselineLatencyMs ?? run.baseline_latency_ms ?? null,
    memory_mb: run.memoryMb ?? run.memory_mb ?? null,
    baseline_memory_mb: run.baselineMemoryMb ?? run.baseline_memory_mb ?? null,
    prompt_tokens: run.promptTokens ?? run.prompt_tokens ?? null,
    completion_tokens: run.completionTokens ?? run.completion_tokens ?? null,
    quality_score: run.qualityScore ?? run.quality_score ?? null,
    baseline_quality_score: run.baselineQualityScore ?? run.baseline_quality_score ?? null,
    rag_chunks: run.ragChunks ?? run.rag_chunks ?? 0,
    hallucination_flag: Boolean(run.hallucinationFlag ?? run.hallucination_flag),
    voice_consistency_score: run.voiceConsistencyScore ?? run.voice_consistency_score ?? null,
    response_preview: String(run.responsePreview || run.response_preview || '').slice(0, 400),
    claims_class: {
      bitnet_quantization: 'E',
      morphic_158d: 'M',
    },
    gateway_version: process.env.npm_package_version || '0.1.0',
  };
  fs.appendFileSync(RUNS_FILE, `${JSON.stringify(row)}\n`, 'utf8');
  trimRunsFile();
  return row;
}

function trimRunsFile() {
  if (!fs.existsSync(RUNS_FILE)) return;
  const lines = fs.readFileSync(RUNS_FILE, 'utf8').split('\n').filter(Boolean);
  if (lines.length <= MAX_RUNS) return;
  const kept = lines.slice(lines.length - MAX_RUNS);
  fs.writeFileSync(RUNS_FILE, `${kept.join('\n')}\n`, 'utf8');
}

function readRecentRuns(limit = 100) {
  if (!fs.existsSync(RUNS_FILE)) return [];
  const lines = fs.readFileSync(RUNS_FILE, 'utf8').split('\n').filter(Boolean);
  return lines
    .slice(-limit)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean)
    .reverse();
}

function summarizeRuns(runs) {
  const avg = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null);

  const bitnetRuns = runs.filter((r) => r.lane === 'bitnet');
  const baselineRuns = runs.filter((r) => r.lane === 'baseline' || r.lane === 'hosted-ollama');

  return {
    total_runs: runs.length,
    bitnet_runs: bitnetRuns.length,
    baseline_runs: baselineRuns.length,
    avg_bitnet_latency_ms: avg(bitnetRuns.map((r) => r.latency_ms).filter(Number.isFinite)),
    avg_baseline_latency_ms: avg(
      baselineRuns.map((r) => r.latency_ms ?? r.baseline_latency_ms).filter(Number.isFinite),
    ),
    avg_bitnet_quality: avg(bitnetRuns.map((r) => r.quality_score).filter(Number.isFinite)),
    avg_baseline_quality: avg(
      baselineRuns.map((r) => r.baseline_quality_score ?? r.quality_score).filter(Number.isFinite),
    ),
    hallucination_rate: runs.length
      ? runs.filter((r) => r.hallucination_flag).length / runs.length
      : null,
    updated_at: new Date().toISOString(),
  };
}

function getResearchStatus(bitnetHealth = {}) {
  const recent = readRecentRuns(200);
  return {
    bitnet_enabled: process.env.BITNET_ENABLED === 'true',
    bitnet_health: bitnetHealth,
    summary: summarizeRuns(recent),
    recent_runs: recent.slice(0, 25),
    data_file: RUNS_FILE,
    claims_register: {
      bitnet_158_bit: 'E — operational when BITNET_ENABLED and sidecar healthy',
      morphic_158d: 'M — unrelated to weight quantization',
    },
  };
}

module.exports = {
  recordBenchmarkRun,
  readRecentRuns,
  summarizeRuns,
  getResearchStatus,
  RUNS_FILE,
};
