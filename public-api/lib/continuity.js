/**
 * Assembles Layer 1–5 context for gateway chat.
 */

const { canonPromptBlock, canonStatus } = require('./canon');
const { retrieveContext } = require('./rag');
const { resolveCadence } = require('./cadence-router');
const { tensionPromptBlock, memoryStatus } = require('./memory/tension-store');

/**
 * @param {object} body - request body
 * @param {string} userQuery
 * @param {string} ownerId
 */
function assembleContinuity(body, userQuery, ownerId) {
  const cadence = resolveCadence(body);
  const tension = tensionPromptBlock(ownerId, {});
  const ragLimit = body.rag_limit ?? Number(process.env.RAG_LIMIT || 5);
  const ragMaxChars = body.rag_max_chars ?? Number(process.env.RAG_MAX_CHARS || 3000);

  const rag = retrieveContext(userQuery, {
    limit: ragLimit,
    maxChars: ragMaxChars,
    cadence: cadence.cadence,
    tensionIds: tension.tensionIds,
  });

  const canon = canonPromptBlock();

  return {
    cadence,
    canonBlock: canon,
    tensionBlock: tension.text,
    tensionIds: tension.tensionIds,
    rag,
    status: {
      canon: canonStatus(),
      memory: memoryStatus(),
    },
  };
}

module.exports = { assembleContinuity };
