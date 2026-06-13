/**
 * Ollama chat API (native /api/chat) for hosted S² inference.
 */

const DEFAULT_BASE = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';
const DEFAULT_MODEL = process.env.OLLAMA_MODEL || 's2-ake';
const LORA_MODEL = process.env.OLLAMA_LORA_MODEL || 's2-ake-lora';
const SLACK_MODEL = process.env.OLLAMA_SLACK_MODEL || '';
const PREFER_LORA = process.env.OLLAMA_PREFER_LORA === 'true';
const DEFAULT_TEMPERATURE = Number(process.env.OLLAMA_TEMPERATURE || 0.2);
const DEFAULT_TOP_P = Number(process.env.OLLAMA_TOP_P || 0.85);
const DEFAULT_REPEAT_PENALTY = Number(process.env.OLLAMA_REPEAT_PENALTY || 1.12);
const DISABLE_THINK = process.env.OLLAMA_DISABLE_THINK === '1' || process.env.OLLAMA_DISABLE_THINK === 'true';
const THINK_BUDGET = Number(process.env.OLLAMA_THINK_BUDGET || 256);

const THINKING_LINE =
  /^(okay[,!]?|hmm[,!]?|let me|the user|i need to|i should|given |wait[,!]|since |this is|i notice|i'll |my response|they want|checking|from the|looking at|the guidelines|the s² assistant)/i;

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

function isQwenModel(model) {
  const m = String(model || '').toLowerCase();
  return /qwen|s2-slack-ake|s2-qwen/.test(m);
}

/** Remove chain-of-thought that Qwen3 sometimes leaks into content when think=false. */
function stripVisibleThinking(text) {
  let t = String(text || '')
    .replace(/<\/?redacted_thinking>/gi, '')
    .replace(/[\s\S]*?<\/think>/gi, '')
    .trim();
  if (!t) return t;

  const paras = t.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
  const kept = paras.filter((p) => {
    const first = p.split('\n')[0] || '';
    if (THINKING_LINE.test(first)) return false;
    if (/\bthe user (asked|wants|is asking|said|sent)\b/i.test(p)) return false;
    if (/\b(let me check|i need to respond|my (job|role) is)\b/i.test(p)) return false;
    return true;
  });
  if (kept.length) return kept.join('\n\n');

  const lines = t.split('\n').map((l) => l.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    if (!THINKING_LINE.test(lines[i]) && !/\bthe user\b/i.test(lines[i])) {
      return lines[i];
    }
  }
  return '';
}

function prepareMessages(messages, useModel, hideThinking = false) {
  const isQwen3 = isQwenModel(useModel);
  if (!isQwen3 && !DISABLE_THINK && !hideThinking) return messages;

  const out = messages.map((m) => ({ ...m }));
  for (const m of out) {
    if (m.role === 'system') {
      const content = String(m.content || '');
      if (!content.includes('/no_think')) {
        m.content = `${content}\n/no_think`;
      }
      if (hideThinking && !/only your final/i.test(content)) {
        m.content +=
          '\nOutput ONLY your final reply. Never narrate reasoning, planning, or guidelines.';
      }
    }
  }
  for (let i = out.length - 1; i >= 0; i -= 1) {
    if (out[i].role !== 'user') continue;
    const content = String(out[i].content || '');
    // Slack separated-think path: /no_think on user text causes the model to echo it in reasoning.
    if (!hideThinking && !content.includes('/no_think') && !content.includes('/think')) {
      out[i] = { ...out[i], content: `/no_think\n${content}` };
    }
    break;
  }
  return out;
}

async function callOllama(root, payload) {
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
  return data;
}

function extractVisibleContent(data, { hideThinking, isQwen3 }) {
  const msg = data?.message || {};
  let content = String(msg.content ?? '').trim();
  // Never expose the thinking field — it is internal chain-of-thought.
  if (hideThinking && isQwen3) {
    content = stripVisibleThinking(content);
  } else if (isQwen3) {
    content = stripVisibleThinking(content);
  }
  return content;
}

async function ollamaChat({
  messages,
  maxTokens = 800,
  temperature = DEFAULT_TEMPERATURE,
  topP = DEFAULT_TOP_P,
  repeatPenalty = DEFAULT_REPEAT_PENALTY,
  model,
  baseUrl = DEFAULT_BASE,
  hideThinking = false,
}) {
  const root = baseUrl.replace(/\/$/, '');
  let useModel = model || (await resolveModel(baseUrl));
  if (hideThinking && SLACK_MODEL) {
    const { ok, models } = await ollamaTags(baseUrl);
    if (ok && modelAvailable(models, SLACK_MODEL)) {
      useModel = SLACK_MODEL;
    }
  }

  const isQwen3 = isQwenModel(useModel);
  const chatMessages = prepareMessages(messages, useModel, hideThinking);

  const basePayload = {
    model: useModel,
    messages: chatMessages,
    stream: false,
    options: {
      temperature,
      top_p: topP,
      repeat_penalty: repeatPenalty,
    },
  };

  const slackPath = hideThinking && Boolean(SLACK_MODEL);
  const slackThinkBudget = Number(process.env.OLLAMA_SLACK_THINK_BUDGET || 256);
  const useSeparatedThink = hideThinking && isQwen3 && !DISABLE_THINK;
  const thinkExtra = slackPath ? slackThinkBudget : THINK_BUDGET;
  const predictBudget = useSeparatedThink ? maxTokens + thinkExtra : maxTokens;

  let data;
  if (slackPath && isQwen3) {
    const slackOpts = {
      ...basePayload.options,
      temperature: Math.min(temperature, 0.35),
    };
    data = await callOllama(root, {
      ...basePayload,
      think: true,
      options: { ...slackOpts, num_predict: maxTokens + slackThinkBudget },
    });
    let content = extractVisibleContent(data, { hideThinking: true, isQwen3 });
    const firstLine = (content.split('\n')[0] || '').trim();
    if (!content || THINKING_LINE.test(firstLine)) {
      data = await callOllama(root, {
        ...basePayload,
        think: false,
        options: { ...slackOpts, num_predict: maxTokens + 48 },
      });
      content = extractVisibleContent(data, { hideThinking: true, isQwen3 });
    }
    if (!content) {
      const err = new Error('Slack fast path returned empty content');
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

  if (useSeparatedThink) {
    data = await callOllama(root, {
      ...basePayload,
      think: true,
      options: { ...basePayload.options, num_predict: predictBudget },
    });
    const content = extractVisibleContent(data, { hideThinking: true, isQwen3 });
    if (!content) {
      const err = new Error('Ollama returned empty visible content after think separation');
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

  const payload = {
    ...basePayload,
    options: { ...basePayload.options, num_predict: predictBudget },
  };
  if (DISABLE_THINK || isQwen3) {
    payload.think = false;
  }

  data = await callOllama(root, payload);
  const content = extractVisibleContent(data, { hideThinking, isQwen3 });
  if (!content) {
    const err = new Error(
      data?.message?.thinking
        ? 'Ollama returned thinking-only output; increase max_tokens or enable hideThinking'
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
      hasSlackModel: SLACK_MODEL ? modelAvailable(models, SLACK_MODEL) : false,
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
  stripVisibleThinking,
  DEFAULT_BASE,
  DEFAULT_MODEL,
  LORA_MODEL,
  DEFAULT_TEMPERATURE,
  DEFAULT_TOP_P,
  DEFAULT_REPEAT_PENALTY,
};
