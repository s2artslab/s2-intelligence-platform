/**
 * Layer 4 — Reflection jobs. Integrate session without auto-closing tensions.
 */

const { upsertTension, appendEpisodic } = require('./tension-store');

const OPEN_MARKERS =
  /\b(unresolved|remains open|still unclear|open question|tension between|not yet|without resolving)\b/i;

/**
 * Heuristic reflection — no extra LLM call. Extracts candidate open threads.
 * @param {{ ownerId: string, userText: string, assistantText: string, sessionId?: string }} input
 */
function reflectSessionHeuristic(input) {
  const ownerId = input.ownerId || 'global';
  const combined = `${input.userText || ''}\n${input.assistantText || ''}`;
  const created = [];

  if (OPEN_MARKERS.test(combined)) {
    const snippet = combined.replace(/\s+/g, ' ').trim().slice(0, 240);
    const t = upsertTension(ownerId, {
      statement: `Open thread (heuristic): ${snippet}`,
      status: 'open',
      linked_threads: input.sessionId ? [input.sessionId] : [],
      append_note: 'reflection-heuristic',
    });
    created.push(t.id);
  }

  const userQs = (input.userText || '').match(/[^.!?]*\?+/g);
  if (userQs?.length) {
    const lastQ = userQs[userQs.length - 1].trim().slice(0, 200);
    if (lastQ.length > 12) {
      const t = upsertTension(ownerId, {
        statement: `User question unsettled: ${lastQ}`,
        status: 'open',
        linked_threads: input.sessionId ? [input.sessionId] : [],
      });
      created.push(t.id);
    }
  }

  if (input.userText || input.assistantText) {
    appendEpisodic(
      ownerId,
      `Session: user=${(input.userText || '').slice(0, 120)} | assistant=${(input.assistantText || '').slice(0, 120)}`,
    );
  }

  return { created, mode: 'heuristic' };
}

/**
 * Schedule post-chat reflection (non-blocking).
 */
function scheduleReflection(input) {
  if (process.env.S2_REFLECTION_ON_CHAT === 'false') {
    return;
  }
  setImmediate(() => {
    try {
      reflectSessionHeuristic(input);
    } catch (e) {
      console.warn('[reflection]', e.message);
    }
  });
}

module.exports = { reflectSessionHeuristic, scheduleReflection };
