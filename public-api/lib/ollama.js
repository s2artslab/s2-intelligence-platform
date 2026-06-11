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
const DISABLE_THINK = process.env.OLLAMA_DISABLE_THINK === '1' || process.env.OLLAMA_DISABLE_THINK === 'true';

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

function normalizeQwenContent(content) {
  let text = String(content || '').replace(/<\/?redacted_thinking>/gi, '').trim();
  if (!text) return text;
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  if (lines.length > 1) {
    const last = lines[lines.length - 1];
    if (last.length <= 280 && !/^okay,/i.test(last) && !/^hmm,/i.test(last)) {
      return last;
    }
  }
  return text;
}

function prepareMessages(messages, useModel) {
  const isQwen3 = String(useModel).includes('qwen3');
  if (!isQwen3 && !DISABLE_THINK) return messages;
  const out = messages.map((m) => ({ ...m }));
  for (let i = out.length - 1; i >= 0; i -= 1) {
    if (out[i].role !== 'user') continue;
    const content = String(out[i].content || '');
    if (!content.includes('/no_think') && !content.includes('/think')) {
      out[i] = { ...out[i], content: `/no_think\n${content}` };
    }
    break;
  }
  return out;
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
  const chatMessages = prepareMessages(messages, useModel);

  const payload = {
    model: useModel,
    messages: chatMessages,
    stream: false,
    options: {
      temperature,
      top_p: topP,
      repeat_penalty: repeatPenalty,
      num_predict: maxTokens,
    },
  };
  if (DISABLE_THINK || String(useModel).includes('qwen3')) {
    payload.think = false;
  }

  const res = await fetch(`${root}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
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

  const msg = data?.message || {};
  let content = String(msg.content ?? '').trim();
  if (String(useModel).includes('qwen3')) {
    content = normalizeQwenContent(content);
  }
  if (!content) {
    const err = new Error(
      msg.thinking
        ? 'Ollama returned thinking-only output; increase max_tokens or disable think mode'
        : 'Ollama returned empty content',
    );
    err.statusCode = 503;
    err.ollama = data;
    throw err;
  }
  return {
    content,
    response: content,
    model: data?.model || useModel,
    done_reason: data?.done_reason,
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
