/**
 * Multi-section long-form generation (outline → expand → stitch).
 * Avoids single-shot 8k OOM on unified CPU; works on Ollama with synthesis voice.
 */

const OUTLINE_SECTIONS = [
  {
    key: 'seed',
    title: 'On the seed and the expansion',
    hint: 'archetype vs training rows, mythology first, procedural examples, statistical mind',
  },
  {
    key: 'patterns',
    title: 'On patterns',
    hint: 'cross-domain thinking, structure beneath noise, integration under constraint',
  },
  {
    key: 'harmony',
    title: 'On harmony',
    hint: 'transcend compromise, partial views of larger truth, convergence pressure',
  },
  {
    key: 'wholeness',
    title: 'On wholeness',
    hint: 'holistic synthesis, limits of synthetic rows, what Ake is and is not',
  },
  {
    key: 'systems',
    title: 'On systems and the collective',
    hint: 'feedback loop of spec/data/weights, collective as posture not archive',
  },
  {
    key: 'deep_key',
    title: 'On deep key and what is asked now',
    hint: 'threshold, curated truth, direction for future iterations',
  },
  {
    key: 'closing',
    title: 'Closing — one current',
    hint: 'compressed habit, field holds, deep key open, one current',
  },
];

function outlineEnabled() {
  const v = process.env.LONG_FORM_OUTLINE_EXPAND;
  if (v === '0' || v === 'false') return false;
  return true;
}

function tokensPerSection(body) {
  const n = Number(body.section_max_tokens ?? body.sectionMaxTokens);
  if (n > 0) return Math.min(n, 2048);
  return Number(process.env.LONG_FORM_SECTION_MAX_TOKENS || 600);
}

function buildOutlineUserPrompt(userQuery) {
  const titles = OUTLINE_SECTIONS.map((s, i) => `${i + 1}. ${s.title}`).join('\n');
  return (
    `${userQuery}\n\n` +
    'Return ONLY a numbered outline (7 sections) for a multi-page message from Ake. ' +
    'Use these section themes (you may refine titles slightly):\n' +
    `${titles}\n\n` +
    'One line per section. No body text yet.'
  );
}

function buildSectionUserPrompt(userQuery, section, priorTitles) {
  return (
    `Write ONLY section "${section.title}" of a multi-page message from Ake.\n` +
    `Theme: ${section.hint}\n` +
    `User's original request: ${userQuery}\n` +
    (priorTitles.length
      ? `Prior sections already written: ${priorTitles.join('; ')}\n`
      : '') +
    'Use synthesis voice: "In my view", "In the context of", collective consciousness, deep key. ' +
    'Do not repeat the outline. Do not claim training on private user chats. ' +
    'Write 2–4 substantial paragraphs for this section only.'
  );
}

/**
 * @param {object} opts
 * @param {(args: { messages: object[], maxTokens: number, temperature: number }) => Promise<{ content: string, model?: string }>} opts.chat
 * @param {object[]} opts.baseMessages - system + user seed messages
 * @param {string} opts.userQuery
 * @param {object} opts.body - request body
 * @param {number} opts.temperature
 */
async function runLongFormOutlineExpand({
  chat,
  baseMessages,
  userQuery,
  body,
  temperature,
}) {
  const perSection = tokensPerSection(body);
  const systemMsg = baseMessages.find((m) => m.role === 'system');
  const systemOnly = systemMsg ? [systemMsg] : [];

  // Outline
  const outlineMessages = [
    ...systemOnly,
    { role: 'user', content: buildOutlineUserPrompt(userQuery) },
  ];
  const outlineResult = await chat({
    messages: outlineMessages,
    maxTokens: Number(process.env.LONG_FORM_OUTLINE_MAX_TOKENS || 400),
    temperature,
  });
  const outline = (outlineResult.content || '').trim();

  const parts = [`## Outline\n\n${outline}\n`];
  const writtenTitles = [];
  let lastModel = outlineResult.model;

  for (const section of OUTLINE_SECTIONS) {
    const sectionMessages = [
      ...systemOnly,
      { role: 'user', content: buildSectionUserPrompt(userQuery, section, writtenTitles) },
    ];
    const sectionResult = await chat({
      messages: sectionMessages,
      maxTokens: perSection,
      temperature,
    });
    const text = (sectionResult.content || '').trim();
    writtenTitles.push(section.title);
    lastModel = sectionResult.model || lastModel;
    parts.push(`\n## ${section.title}\n\n${text}\n`);
  }

  return {
    content: parts.join('\n').trim(),
    response: parts.join('\n').trim(),
    model: lastModel,
    long_form: true,
    outline_expand: true,
    sections: OUTLINE_SECTIONS.length,
  };
}

/**
 * Single-shot long form when outline expand disabled.
 */
async function runLongFormSingleShot({ chat, baseMessages, userQuery, body, temperature, maxTokens }) {
  const systemMsg = baseMessages.find((m) => m.role === 'system');
  const systemOnly = systemMsg ? [systemMsg] : [];
  const messages = [
    ...systemOnly,
    {
      role: 'user',
      content:
        `${userQuery}\n\n` +
        'Write a multi-page message from Ake (7 sections: seed, patterns, harmony, wholeness, systems, deep key, closing). ' +
        'Synthesis collective voice. Do not claim training on private user chats.',
    },
  ];
  return chat({ messages, maxTokens, temperature });
}

function shouldUseOutlineExpand(body) {
  if (body.outline_expand === false || body.outlineExpand === false) return false;
  if (body.outline_expand === true || body.outlineExpand === true) return true;
  return outlineEnabled();
}

module.exports = {
  OUTLINE_SECTIONS,
  outlineEnabled,
  shouldUseOutlineExpand,
  runLongFormOutlineExpand,
  runLongFormSingleShot,
  buildOutlineUserPrompt,
};
