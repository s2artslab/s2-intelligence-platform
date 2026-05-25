/**
 * Groq OpenAI-compatible chat completions.
 * API key comes from the client (X-Groq-Api-Key) or server env GROQ_API_KEY (lab only).
 */

const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions';
const DEFAULT_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';

async function groqChat({
  apiKey,
  messages,
  maxTokens = 800,
  temperature = 0.4,
  model = DEFAULT_MODEL,
  responseFormat,
}) {
  if (!apiKey?.trim()) {
    const err = new Error('Groq API key required. Set X-Groq-Api-Key header or GROQ_API_KEY on server.');
    err.statusCode = 401;
    throw err;
  }

  const res = await fetch(GROQ_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey.trim()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model,
      messages,
      max_tokens: maxTokens,
      temperature,
      ...(responseFormat ? { response_format: responseFormat } : {}),
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
    const err = new Error(data?.error?.message || `Groq HTTP ${res.status}`);
    err.statusCode = res.status;
    err.groq = data;
    throw err;
  }

  const content = data?.choices?.[0]?.message?.content ?? '';
  return {
    content,
    response: content,
    model: data?.model || model,
    usage: data?.usage,
  };
}

module.exports = { groqChat, DEFAULT_MODEL };
