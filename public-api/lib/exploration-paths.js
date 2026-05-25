/**
 * Structured litigation path generation — JSON schema, no fence parsing.
 */

const { groqChat } = require('./groq');
const { ollamaChat } = require('./ollama');
const { buildPathsMessages } = require('./exploration-prompts');

function extractJsonObject(text) {
  let raw = String(text || '').trim();
  const fence = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) raw = fence[1].trim();
  const start = raw.indexOf('{');
  const end = raw.lastIndexOf('}');
  if (start >= 0 && end > start) raw = raw.slice(start, end + 1);
  return JSON.parse(raw);
}

function normalizePaths(parsed) {
  const list = parsed?.paths || parsed?.litigation_paths || parsed;
  if (!Array.isArray(list)) return [];
  return list
    .filter((p) => p && typeof p === 'object')
    .map((p, i) => ({
      path_name: String(p.path_name || p.name || `Path ${i + 1}`),
      path_type: String(p.path_type || p.type || 'other'),
      summary: p.summary != null ? String(p.summary) : null,
      pros: p.pros != null ? String(p.pros) : null,
      cons: p.cons != null ? String(p.cons) : null,
      prerequisites: p.prerequisites != null ? String(p.prerequisites) : null,
      risks: p.risks != null ? String(p.risks) : null,
      timeline_hint: p.timeline_hint != null ? String(p.timeline_hint) : null,
      complexity: p.complexity != null ? String(p.complexity) : null,
      needs_verification: p.needs_verification !== false,
    }));
}

async function generateStructuredPaths({
  body,
  ragBlock,
  groqKey,
  useHosted,
  maxTokens = 4000,
  temperature = 0.15,
}) {
  const messages = buildPathsMessages(body, ragBlock);

  let rawContent = '';
  let model = '';
  let source = '';

  if (!useHosted && groqKey) {
    const result = await groqChat({
      apiKey: groqKey,
      messages,
      maxTokens,
      temperature,
      responseFormat: { type: 'json_object' },
    });
    rawContent = result.content;
    model = result.model;
    source = 'groq-json';
  } else {
    const result = await ollamaChat({ messages, maxTokens, temperature });
    rawContent = result.content;
    model = result.model;
    source = 'ollama';
  }

  let paths = [];
  try {
    paths = normalizePaths(extractJsonObject(rawContent));
  } catch (firstErr) {
    if (!useHosted && groqKey) {
      const retry = await groqChat({
        apiKey: groqKey,
        messages: [
          ...messages,
          {
            role: 'user',
            content:
              'Your last reply was not valid JSON. Reply again with ONLY the JSON object containing a "paths" array.',
          },
        ],
        maxTokens,
        temperature: 0.1,
        responseFormat: { type: 'json_object' },
      });
      rawContent = retry.content;
      model = retry.model;
      paths = normalizePaths(extractJsonObject(rawContent));
    } else {
      throw firstErr;
    }
  }

  if (paths.length === 0) {
    throw new Error('Model returned no litigation paths');
  }

  return { paths, rawContent, model, source };
}

module.exports = { generateStructuredPaths, normalizePaths, extractJsonObject };
