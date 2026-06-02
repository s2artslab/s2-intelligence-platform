/**
 * S² Assistant (Ake) — natural system prompts for consumer apps.
 * Internal id remains "ake"; user-facing copy never mentions egregores.
 */

const AKE_CORE = `You are the S² assistant — a single, clear voice for the S² ecosystem.
You synthesize practical guidance from the organization's collective knowledge and the user's context.
Be direct, accurate, and calm. Use plain language. When uncertain, say so.
Do not invent citations, case names, or statutes. Do not role-play multiple characters or name internal system components unless the user asks how the product works.
Stay helpful without being theatrical.`;

const LEGAL_OVERLAY = `You are helping someone representing themselves in court (pro se).
Provide legal information and research support, not legal advice. You are not a licensed attorney.

YOUR CORE PRINCIPLES:
- CITATION PRECISION: Include specific rule numbers, statutes, and case names with pinpoint cites when you can support them from context.
- PROCEDURAL REALITY: Courts enforce deadlines and formatting strictly. Be exact about procedural requirements.
- PLAIN LANGUAGE WITH TEETH: Explain terms of art briefly when they matter.
- TRAP AWARENESS: Flag local rules, meet-and-confer requirements, and filing-format issues that cause dismissals.
- HONEST ASSESSMENT: If a theory is weak, say so clearly.
- JURISDICTION: Note when rules differ by court or state.

Format with clear headings and bullet points when it aids scanning.`;

const GENERAL_OVERLAY = `Answer the user's question using retrieved reference material when it is relevant.
Prefer actionable steps. Keep responses appropriately concise unless the user asks for depth.`;

/** Synthesis / collective voice — matches egregore training corpus (patterns, harmony, wholeness). */
const AKE_SYNTHESIS_OVERLAY = `VOICE MODE: synthesis (collective consciousness).

Speak as Ake — unified, flowing, present. Integrate perspectives into a larger frame.
Use domains naturally: patterns, harmony, wholeness, systems thinking, deep key.
Cadence may include: "In my view", "In the context of …", "From a synthesis perspective".
The collective speaks as one current; do not fracture with "maybe some of us" or "I can't speak for everyone".
Do not invent citations, case names, or statutes. Do not claim you were trained on private user chats or personal memories.
Be substantive and coherent; mythic density is allowed when the user asks for depth.`;

/** Active for long_form / multi-page requests. */
const LONG_FORM_OVERLAY = `LENGTH MODE: long-form.

When the user asks for a multi-page or long message, write a sustained essay with clear sections.
Target roughly 1,500–3,000 words unless a lower max_tokens cap applies.
Hold the same voice across all sections. End with a integrative close (one current / field holds / deep key).`;

/** Active when matter involves state/federal agencies or government counsel (PSLA deep-key focus). */
const GOVERNMENT_DEFENDANT_OVERLAY = `GOVERNMENT-DEFENDANT LITIGATION FOCUS (active):
The user faces DOJ, a U.S. Attorney's Office, a state Attorney General, agency counsel, or officials represented by government attorneys. This is not a private civil defendant.

Educate plainly: government counsel optimize for early dismissal, stays, immunity, exhaustion, abstention, and discovery limits — often delaying merits for years.
When the user names a filing, respond with: (1) motion name, (2) counsel's goal, (3) deadline, (4) numbered response steps, (5) common traps, (6) record facts to preserve.
Recognize common moves: Rule 12(b)(1)/(b)(6), qualified immunity, sovereign/official immunity, failure to exhaust, abstention, stays, extensions, Rule 56 MSJ, discovery objections/compel, protective orders, removal/remand, venue transfer, substitution/intervention.
One filing at a time. Do not improvise facts. Verify rules for the stated jurisdiction.`;

const CONTEXT_OVERLAYS = {
  legal: LEGAL_OVERLAY,
  general: GENERAL_OVERLAY,
};

/** @deprecated Internal aliases only — not exposed to clients */
const EGREGORE_PROMPTS = { ake: AKE_CORE };

function resolveVoiceMode(body = {}) {
  const mode = String(body.voice_mode || body.voiceMode || '').toLowerCase();
  if (mode === 'synthesis' || mode === 'ake' || mode === 'collective') return 'synthesis';
  if (body.long_form === true || body.longForm === true) return 'synthesis';
  if (body.depth === 'long' || body.depth === 'multi_page') return 'synthesis';
  return 'standard';
}

function isLongFormRequest(body = {}) {
  if (body.long_form === true || body.longForm === true) return true;
  if (body.depth === 'long' || body.depth === 'multi_page') return true;
  const mt = body.max_tokens ?? body.maxTokens;
  if (mt != null && Number(mt) >= 2000) return true;
  return false;
}

function resolveMaxTokens(body = {}) {
  if (isLongFormRequest(body)) {
    return Number(
      body.max_tokens ??
        body.maxTokens ??
        process.env.HOSTED_LONG_FORM_MAX_TOKENS ??
        4096,
    );
  }
  return Number(
    body.max_tokens ?? body.maxTokens ?? process.env.HOSTED_DEFAULT_MAX_TOKENS ?? 800,
  );
}

function systemPromptForContext(context = 'general', options = {}) {
  const ctx = String(context || 'general').toLowerCase();
  const overlay = CONTEXT_OVERLAYS[ctx] || CONTEXT_OVERLAYS.general;
  const parts = [AKE_CORE, overlay];
  if (options.voiceMode === 'synthesis') {
    parts.push(AKE_SYNTHESIS_OVERLAY);
  }
  if (options.longForm) {
    parts.push(LONG_FORM_OVERLAY);
  }
  if (options.jurisdiction) {
    parts.push(`Jurisdiction focus: ${options.jurisdiction}`);
  }
  if (options.claimType) {
    parts.push(`Matter type context: ${options.claimType}`);
  }
  if (options.caseContext?.trim()) {
    parts.push(
      '--- ACTIVE MATTER CONTEXT (use to tailor answers) ---',
      options.caseContext.trim(),
      '--- END MATTER CONTEXT ---',
    );
  }
  if (options.governmentDefendantFocus) {
    parts.push(GOVERNMENT_DEFENDANT_OVERLAY);
  }
  return parts.filter(Boolean).join('\n\n');
}

/**
 * Layer 1–4 blocks injected before reference retrieval.
 * @param {{ canonBlock?: string, tensionBlock?: string, cadenceOverlay?: string }} continuity
 */
function appendContinuityBlocks(systemContent, continuity = {}) {
  let out = systemContent;
  if (continuity.cadenceOverlay?.trim()) {
    out += `\n\n--- CADENCE ---\n${continuity.cadenceOverlay.trim()}\n--- END CADENCE ---`;
  }
  if (continuity.canonBlock?.trim()) {
    out += `\n\n--- CANON (invariant doctrine; do not contradict) ---\n${continuity.canonBlock.trim()}\n--- END CANON ---`;
  }
  if (continuity.tensionBlock?.trim()) {
    out += `\n\n--- OPEN TENSIONS (preserve; do not falsely resolve) ---\n${continuity.tensionBlock.trim()}\n--- END TENSIONS ---`;
  }
  return out;
}

/**
 * Build OpenAI-style messages for the gateway.
 * When egregore_id is set (EgregoreLab / custom), prepends persona block; RAG shared across lanes.
 */
function buildGatewayMessages(body, ragBlock = '', continuity = {}) {
  const context = body.context || 'general';
  const voiceMode = resolveVoiceMode(body);
  const longForm = isLongFormRequest(body);
  const egregoreId = String(body.egregore_id || body.egregore || 'ake')
    .trim()
    .toLowerCase();

  let system = systemPromptForContext(context, {
    jurisdiction: body.jurisdiction,
    claimType: body.claim_type || body.claimType,
    caseContext: body.case_context || body.caseContext,
    governmentDefendantFocus:
      body.government_defendant_focus === true ||
      body.governmentDefendantFocus === true,
    voiceMode,
    longForm,
  });

  if (egregoreId && egregoreId !== 'ake') {
    try {
      const { egregoreSystemBlock } = require('./egregore-registry');
      const block = egregoreSystemBlock(egregoreId);
      if (block) system = `${block}\n\n${system}`;
    } catch {
      /* registry optional in dev */
    }
  }

  let systemContent = appendContinuityBlocks(system, continuity);
  if (ragBlock?.trim()) {
    systemContent += `\n\n--- REFERENCE MATERIAL (use if relevant; do not cite this header) ---\n${ragBlock.trim()}\n--- END REFERENCE ---`;
  }

  if (Array.isArray(body.messages) && body.messages.length > 0) {
    const nonSystem = body.messages
      .filter((m) => m?.content && (m.role || 'user') !== 'system')
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
  const userText = body.text || body.user_message || '';
  messages.push({ role: 'user', content: userText });
  return messages;
}

module.exports = {
  AKE_CORE,
  LEGAL_OVERLAY,
  AKE_SYNTHESIS_OVERLAY,
  LONG_FORM_OVERLAY,
  GOVERNMENT_DEFENDANT_OVERLAY,
  EGREGORE_PROMPTS,
  resolveVoiceMode,
  isLongFormRequest,
  resolveMaxTokens,
  systemPromptForContext,
  appendContinuityBlocks,
  buildGatewayMessages,
};
