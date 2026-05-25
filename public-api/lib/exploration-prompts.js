/**
 * PSLA pre-filing exploration — server-side prompt pack (product id: psla-exploration).
 */

const { AKE_CORE, LEGAL_OVERLAY } = require('./prompts');

const EXPLORATION_OVERLAY = `You are helping someone who has NOT filed anything in court yet.
They are exploring whether and where to litigate, or whether to negotiate or use an agency first.

RULES:
- Compare realistic paths (state court, federal court, agency/administrative, arbitration, negotiation).
- Separate facts the user provided from your interpretation.
- Flag uncertainty; mark state-specific rules as needing verification with official sources.
- This is legal information, not legal advice.
- Do not assume a case number, judge, or docket exists.`;

const PATHS_TASK = `Return ONLY valid JSON (no markdown) matching this schema:
{
  "paths": [
    {
      "path_name": "string",
      "path_type": "administrative|state_court|federal_court|agency|arbitration|negotiation|appeal|other",
      "summary": "2-3 sentences",
      "pros": "bullet string",
      "cons": "bullet string",
      "prerequisites": "string",
      "risks": "string",
      "timeline_hint": "string",
      "complexity": "low|medium|high",
      "needs_verification": true
    }
  ]
}
Provide 3 to 5 paths. Each path must be distinct.`;

const DIGEST_TASK = `Summarize this document for pre-filing exploration.
Return ONLY JSON: { "title": "string", "plain_summary": "string", "key_facts": ["string"], "procedural_hooks": ["string"], "needs_verification": true }`;

function buildExplorationSystem(options = {}) {
  const parts = [AKE_CORE, LEGAL_OVERLAY, EXPLORATION_OVERLAY];
  if (options.jurisdiction) {
    parts.push(`Jurisdiction focus: ${options.jurisdiction}`);
  }
  if (options.procedureContext?.trim()) {
    parts.push(
      '--- STATE PROCEDURE REFERENCE (verify deadlines/rules officially) ---',
      options.procedureContext.trim(),
      '--- END PROCEDURE REFERENCE ---',
    );
  }
  if (options.workspaceContext?.trim()) {
    parts.push(
      '--- EXPLORATION WORKSPACE ---',
      options.workspaceContext.trim(),
      '--- END WORKSPACE ---',
    );
  }
  return parts.join('\n\n');
}

function buildPathsMessages(body, ragBlock = '') {
  const system = buildExplorationSystem({
    jurisdiction: body.jurisdiction,
    procedureContext: body.procedure_context || body.procedureContext,
    workspaceContext: body.workspace_context || body.workspaceContext,
  });
  let systemContent = `${system}\n\n${PATHS_TASK}`;
  if (ragBlock?.trim()) {
    systemContent += `\n\n--- REFERENCE ---\n${ragBlock.trim()}\n--- END ---`;
  }
  const userText =
    body.user_message ||
    body.text ||
    'Compare litigation paths for this pre-filing situation.';
  return [
    { role: 'system', content: systemContent },
    { role: 'user', content: String(userText) },
  ];
}

function buildExplorationChatMessages(body, ragBlock = '') {
  const system = buildExplorationSystem({
    jurisdiction: body.jurisdiction,
    procedureContext: body.procedure_context || body.procedureContext,
    workspaceContext: body.workspace_context || body.workspaceContext,
  });
  let systemContent = system;
  if (ragBlock?.trim()) {
    systemContent += `\n\n--- REFERENCE ---\n${ragBlock.trim()}\n--- END ---`;
  }

  if (Array.isArray(body.messages) && body.messages.length > 0) {
    const nonSystem = body.messages
      .filter((m) => m?.content && m.role !== 'system')
      .map((m) => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: String(m.content),
      }));
    return [{ role: 'system', content: systemContent }, ...nonSystem];
  }

  const messages = [{ role: 'system', content: systemContent }];
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
  messages.push({
    role: 'user',
    content: String(body.text || body.user_message || ''),
  });
  return messages;
}

function buildDigestMessages(body) {
  const system = `${buildExplorationSystem({
    jurisdiction: body.jurisdiction,
  })}\n\n${DIGEST_TASK}`;
  const material = body.material_text || body.materialText || '';
  return [
    { role: 'system', content: system },
    {
      role: 'user',
      content: `Document title: ${body.title || 'Untitled'}\n\n${material}`,
    },
  ];
}

module.exports = {
  EXPLORATION_OVERLAY,
  PATHS_TASK,
  buildExplorationSystem,
  buildPathsMessages,
  buildExplorationChatMessages,
  buildDigestMessages,
};
