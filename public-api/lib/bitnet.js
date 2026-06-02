/**
 * BitNet b1.58 sidecar client (experimental 1.58-bit inference lane).
 * Sidecar HTTP API — see scripts/bitnet-sidecar-server.py
 */

const DEFAULT_BASE = process.env.BITNET_BASE_URL || 'http://127.0.0.1:8120';
const DEFAULT_MODEL = process.env.BITNET_MODEL || 'bitnet-b1.58-2B-4T';
const DEFAULT_TIMEOUT_MS = Number(process.env.BITNET_TIMEOUT_MS || 120000);
const ENABLED = process.env.BITNET_ENABLED === 'true';

async function bitnetHealth(baseUrl = DEFAULT_BASE) {
  const root = baseUrl.replace(/\/$/, '');
  try {
    const res = await fetch(`${root}/health`, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = await res.json();
    return {
      ok: Boolean(data?.ok),
      model: data?.model || DEFAULT_MODEL,
      quantization: data?.quantization || 'w1.58a8',
      backend: data?.backend || 'bitnet.cpp',
      stub_mode: Boolean(data?.stub_mode),
      ...data,
    };
  } catch (e) {
    return { ok: false, error: e.message, enabled: ENABLED };
  }
}

async function bitnetGenerate({
  prompt,
  messages,
  maxTokens = 256,
  temperature = 0.2,
  taskClass = '',
  egregoreId = '',
  baseUrl = DEFAULT_BASE,
  timeoutMs = DEFAULT_TIMEOUT_MS,
}) {
  const root = baseUrl.replace(/\/$/, '');
  const body = {
    prompt: prompt || '',
    messages: messages || [],
    max_tokens: maxTokens,
    temperature,
    task_class: taskClass,
    egregore_id: egregoreId || undefined,
  };

  const res = await fetch(`${root}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const err = new Error(data?.error || `BitNet HTTP ${res.status}`);
    err.statusCode = res.status >= 500 ? 503 : res.status;
    err.bitnet = data;
    throw err;
  }

  const content = (data?.response || data?.content || '').trim();
  return {
    content,
    response: content,
    model: data?.model || DEFAULT_MODEL,
    latency_ms: data?.latency_ms ?? null,
    prompt_tokens: data?.prompt_tokens ?? null,
    completion_tokens: data?.completion_tokens ?? null,
    memory_mb: data?.memory_mb ?? null,
    quantization_bits: data?.quantization_bits ?? 1.58,
    task_class: taskClass,
    egregore_id: egregoreId || data?.egregore_id || null,
    stub_mode: Boolean(data?.stub_mode),
  };
}

async function bitnetChat({
  messages,
  maxTokens = 256,
  temperature = 0.2,
  taskClass = '',
  egregoreId = '',
  baseUrl = DEFAULT_BASE,
}) {
  const { getProfile } = require('./egregore-registry');
  const { egregoreBitnetPrompt } = require('./egregore-bitnet-prompt');
  const profile = egregoreId ? getProfile(egregoreId) : null;
  const lastUser = [...(messages || [])].reverse().find((m) => m?.role === 'user');
  const userText = lastUser ? String(lastUser.content || '').trim() : '';

  let prompt;
  if (egregoreId && userText) {
    prompt = egregoreBitnetPrompt(egregoreId, userText, profile || {});
    const systemParts = (messages || [])
      .filter((m) => m?.role === 'system' && m?.content)
      .map((m) => String(m.content).trim());
    if (systemParts.length) {
      prompt = `${systemParts.join('\n\n')}\n\n${prompt}`;
    }
  } else {
    prompt = messages
      .map((m) => {
        const role = m?.role === 'assistant' ? 'Assistant' : m?.role === 'system' ? 'System' : 'User';
        return `${role}: ${String(m?.content || '').trim()}`;
      })
      .filter(Boolean)
      .join('\n');
  }

  return bitnetGenerate({
    prompt,
    messages,
    maxTokens,
    temperature,
    taskClass,
    egregoreId,
    baseUrl,
  });
}

module.exports = {
  bitnetHealth,
  bitnetGenerate,
  bitnetChat,
  DEFAULT_BASE,
  DEFAULT_MODEL,
  DEFAULT_TIMEOUT_MS,
  ENABLED,
};
