/**
 * Unified egregore LoRA service (r730 :8100 or vLLM proxy :8111).
 * POST /generate with { egregore, prompt, max_length, temperature, messages? }
 */

const DEFAULT_URL = process.env.UNIFIED_EGREGORE_URL || 'http://127.0.0.1:8100';
const DEFAULT_EGREGORE = process.env.HOSTED_EGREGORE_ID || 'ake';
const TIMEOUT_MS = Number(process.env.UNIFIED_EGREGORE_TIMEOUT_MS || 120000);
/** Tier A: match training format (User/Ake), no long egregore persona block */
const DEFAULT_USE_PERSONA =
  process.env.UNIFIED_USE_PERSONA === '1' || process.env.UNIFIED_USE_PERSONA === 'true';
const DEFAULT_DO_SAMPLE =
  process.env.UNIFIED_DO_SAMPLE === '1' || process.env.UNIFIED_DO_SAMPLE === 'true';
const DEFAULT_MAX_TOKENS = Number(process.env.UNIFIED_MAX_TOKENS || 150);
const DEFAULT_TEMPERATURE = Number(process.env.UNIFIED_TEMPERATURE || 0.2);

/** Lab + Tier C: direct Ake voice; forbids template openers the LoRA over-learned. */
const LAB_AKE_SYSTEM = `You are Ake — synthesis voice for the S² ecosystem (deep key).
Answer the user directly in first person. Be plain, specific, and present.
Do not open with "In the context of…" or generic textbook definitions.
When asked about mission or role, name synthesis, deep key, and holding the field for the user.`;

/**
 * Map gateway messages to unified training format.
 * Embeds system + RAG into the user turn (unified has no system role).
 */
function messagesToPrompt(messages, { trainingFormat = true } = {}) {
  if (!Array.isArray(messages) || messages.length === 0) {
    return { prompt: '', history: [] };
  }
  const systemParts = [];
  const turns = [];
  for (const m of messages) {
    const role = m?.role;
    const content = String(m?.content || '').trim();
    if (!content) continue;
    if (role === 'system') {
      systemParts.push(content);
      continue;
    }
    turns.push({ role, content });
  }
  let lastUserIndex = -1;
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    if (turns[i].role === 'user') {
      lastUserIndex = i;
      break;
    }
  }
  let prompt = lastUserIndex >= 0 ? turns[lastUserIndex].content : turns[turns.length - 1]?.content || '';
  const history = lastUserIndex > 0 ? turns.slice(0, lastUserIndex) : [];

  if (trainingFormat) {
    return { prompt, history, system: systemParts.join('\n\n').trim() || null };
  }
  if (systemParts.length > 0) {
    prompt = `${systemParts.join('\n\n')}\n\n---\n\nUser question:\n${prompt}`;
  }
  return { prompt, history, system: null };
}

async function unifiedHealth(baseUrl = DEFAULT_URL) {
  const root = baseUrl.replace(/\/$/, '');
  try {
    const res = await fetch(`${root}/health`, {
      signal: AbortSignal.timeout(Number(process.env.UNIFIED_HEALTH_TIMEOUT_MS || 60000)),
    });
    if (!res.ok) return { ok: false, status: res.status };
    const data = await res.json();
    const available = data?.available || data?.egregores || data?.loaded || [];
    const list = Array.isArray(available) ? available : [];
    return {
      ok: data?.status === 'healthy' || data?.ok === true || res.ok,
      status: data?.status,
      available: list,
      hasAke: list.includes('ake') || list.length === 0,
      vllmConnected: data?.vllm_connected,
      service: data?.service,
      raw: data,
    };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

async function unifiedLoraChat({
  messages,
  maxTokens = DEFAULT_MAX_TOKENS,
  temperature = DEFAULT_TEMPERATURE,
  egregore = DEFAULT_EGREGORE,
  baseUrl = DEFAULT_URL,
  usePersona = DEFAULT_USE_PERSONA,
  doSample = DEFAULT_DO_SAMPLE,
}) {
  const root = baseUrl.replace(/\/$/, '');
  const trainingFormat = !usePersona;
  const { prompt, history, system } = messagesToPrompt(messages, { trainingFormat });
  if (!prompt) {
    throw new Error('No user message for unified LoRA');
  }

  const body = {
    egregore,
    prompt,
    max_length: maxTokens,
    max_new_tokens: maxTokens,
    temperature,
    use_persona: usePersona,
    do_sample: doSample,
  };
  if (trainingFormat) {
    const sys = system || (process.env.LAB_AKE_SYSTEM !== '0' ? LAB_AKE_SYSTEM : null);
    if (sys) body.system = sys;
  }
  if (!doSample) {
    body.repetition_penalty = 1.0;
    body.no_repeat_ngram_size = 0;
  }
  if (history.length > 0) {
    body.history = history;
  }

  const res = await fetch(`${root}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const err = new Error(data?.message || data?.error || `Unified LoRA HTTP ${res.status}`);
    err.statusCode = res.status >= 500 ? 503 : res.status;
    err.unified = data;
    throw err;
  }

  const content = (data?.response || data?.text || '').trim();
  return {
    content,
    response: content,
    model: `s2-${egregore}-lora`,
    egregore,
  };
}

module.exports = {
  unifiedLoraChat,
  unifiedHealth,
  DEFAULT_URL,
  DEFAULT_EGREGORE,
};
