/**
 * Ollama chat API (native /api/chat) for hosted S² inference.
 */

const DEFAULT_BASE = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';
const DEFAULT_MODEL = process.env.OLLAMA_MODEL || 's2-ake';
const LORA_MODEL = process.env.OLLAMA_LORA_MODEL || 's2-ake-lora';
const PREFER_LORA = process.env.OLLAMA_PREFER_LORA === 'true';
const DEFAULT_TEMPERATURE = Number(process.env.OLLAMA_TEMPERATURE || 0.2);
const DEFAULT_TOP_P = Number(process.env.OLLAMA_TOP_P || 0.85);
const DEFAULT_REPEAT_PENALTY = Number(process.env.OLLAMA_REPEAT_PENALTY || 1.12);

async function ollamaTags(baseUrl = DEFAULT_BASE) {
  const root = baseUrl.replace(/\/$/, '');
  const res = await fetch(`${root}/api/tags`, { signal: AbortSignal.timeout(8000) });
  if (!res.ok) return { ok: false, models: [] };
  const data = await res.json();
  const names = (data?.models || []).map((m) => m.name || '');
  return { ok: true, models: names };
}

function modelAvailable(names, want) {
  const prefix = want.split(':')[0];
  return names.some((n) => n === want || n.startsWith(`${prefix}:`));
}

async function resolveModel(baseUrl = DEFAULT_BASE) {
  const { ok, models } = await ollamaTags(baseUrl);
  if (!ok) return DEFAULT_MODEL;

  if (PREFER_LORA && modelAvailable(models, LORA_MODEL)) {
    return LORA_MODEL;
  }
  if (modelAvailable(models, DEFAULT_MODEL)) {
    return DEFAULT_MODEL;
  }
  if (modelAvailable(models, LORA_MODEL)) {
    return LORA_MODEL;
  }
  return models[0]?.split(':')[0] || DEFAULT_MODEL;
}

async function ollamaChat({
  messages,
  maxTokens = 800,
  temperature = DEFAULT_TEMPERATURE,
  topP = DEFAULT_TOP_P,
  repeatPenalty = DEFAULT_REPEAT_PENALTY,
  model,
  baseUrl = DEFAULT_BASE,
}) {
  const root = baseUrl.replace(/\/$/, '');
  const useModel = model || (await resolveModel(baseUrl));

  const res = await fetch(`${root}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: useModel,
      messages,
      stream: false,
      options: {
        temperature,
        top_p: topP,
        repeat_penalty: repeatPenalty,
        num_predict: maxTokens,
      },
    }),
  });

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const err = new Error(data?.error || `Ollama HTTP ${res.status}`);
    err.statusCode = res.status >= 500 ? 503 : res.status;
    err.ollama = data;
    throw err;
  }

  const content = (data?.message?.content ?? '').trim();
  return {
    content,
    response: content,
    model: data?.model || useModel,
  };
}

async function ollamaHealth(baseUrl = DEFAULT_BASE) {
  try {
    const { ok, models } = await ollamaTags(baseUrl);
    if (!ok) return { ok: false, models: [] };
    const active = await resolveModel(baseUrl);
    return {
      ok: true,
      models,
      hasConfiguredModel: modelAvailable(models, DEFAULT_MODEL) || modelAvailable(models, LORA_MODEL),
      hasLoraModel: modelAvailable(models, LORA_MODEL),
      activeModel: active,
      preferLora: PREFER_LORA,
    };
  } catch (e) {
    return { ok: false, error: e.message, models: [] };
  }
}

module.exports = {
  ollamaChat,
  ollamaHealth,
  resolveModel,
  DEFAULT_BASE,
  DEFAULT_MODEL,
  LORA_MODEL,
  DEFAULT_TEMPERATURE,
  DEFAULT_TOP_P,
  DEFAULT_REPEAT_PENALTY,
};
