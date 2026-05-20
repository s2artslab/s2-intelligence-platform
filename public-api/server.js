#!/usr/bin/env node
/**
 * S² Intelligence Public API (port 3010 by default)
 *
 * Thin server: assembles egregore / legal context, runs inference on **the user's Groq key**.
 * Clients send:  Header: X-Groq-Api-Key: gsk_...
 * Lab fallback:  env GROQ_API_KEY (optional; not for production multi-tenant)
 */

const express = require('express');
const cors = require('cors');
const { groqChat } = require('./lib/groq');
const { systemPromptForEgregore } = require('./lib/prompts');

const PORT = Number(process.env.PORT || 3010);
const LAB_GROQ_KEY = process.env.GROQ_API_KEY || '';

const app = express();
app.use(
  cors({
    origin: process.env.CORS_ORIGIN || true,
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Groq-Api-Key', 'X-User-Id'],
  }),
);
app.use(express.json({ limit: '2mb' }));

function resolveGroqKey(req) {
  const header =
    req.get('X-Groq-Api-Key') ||
    req.get('x-groq-api-key') ||
    req.body?.groq_api_key;
  const key = (header || LAB_GROQ_KEY || '').trim();
  return key || null;
}

function buildMessagesFromBody(body) {
  if (Array.isArray(body.messages) && body.messages.length > 0) {
    return body.messages.map((m) => ({
      role: m.role || 'user',
      content: m.content || '',
    }));
  }

  const egregoreId = body.egregore_id || body.egregore || 'ake';
  const context = body.context || 'legal';
  const system = systemPromptForEgregore(egregoreId, context);
  const userText = body.text || body.user_message || '';

  const messages = [{ role: 'system', content: system }];
  if (Array.isArray(body.history)) {
    for (const h of body.history) {
      if (h?.content) {
        messages.push({
          role: h.role === 'assistant' ? 'assistant' : 'user',
          content: String(h.content),
        });
      }
    }
  }
  messages.push({ role: 'user', content: userText });
  return messages;
}

app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 's2-intelligence-public-api', port: PORT });
});

app.get('/api/public/capability', (req, res) => {
  const hasKey = Boolean(resolveGroqKey(req));
  res.json({
    rag_available: false,
    system_prompt_available: true,
    groq_configured: hasKey,
    user_groq_required: !LAB_GROQ_KEY,
    message: hasKey
      ? 'Ready — inference uses your Groq API key.'
      : 'Add your Groq API key in app Settings (or X-Groq-Api-Key header).',
  });
});

async function handleChat(req, res) {
  try {
    const apiKey = resolveGroqKey(req);
    const messages = buildMessagesFromBody(req.body);
    const maxTokens = req.body.max_tokens ?? 800;
    const temperature = req.body.temperature ?? 0.4;

    const result = await groqChat({
      apiKey,
      messages,
      maxTokens,
      temperature,
    });

    res.json({
      success: true,
      content: result.content,
      response: result.response,
      model: result.model,
      source: 'groq',
      processing_time_ms: null,
    });
  } catch (e) {
    const status = e.statusCode || 500;
    res.status(status).json({
      success: false,
      error: e.message,
      content: '',
    });
  }
}

app.post('/api/ai/chat', handleChat);
app.post('/api/public/chat', handleChat);
app.post('/api/public/chat-with-context', handleChat);

app.listen(PORT, () => {
  console.log(`S² Intelligence Public API listening on http://0.0.0.0:${PORT}`);
  console.log(
    LAB_GROQ_KEY
      ? 'Lab GROQ_API_KEY set — clients may omit X-Groq-Api-Key'
      : 'User Groq keys required (X-Groq-Api-Key) — no server key configured',
  );
});
