/**
 * Assembles Layer 1–5 context for gateway chat.
 */

const { canonPromptBlock, canonStatus } = require('./canon');
const { retrieveContext } = require('./rag');
const { resolveCadence } = require('./cadence-router');
const { tensionPromptBlock, memoryStatus } = require('./memory/tension-store');
const { resolveNamespaces } = require('./rag-namespaces');

/**
 * @param {object} body - request body
 * @param {string} userQuery
 * @param {string} ownerId
 * @param {object} morphicPolicy
 * @param {object} req - optional Express request
 */
async function assembleContinuity(body, userQuery, ownerId, morphicPolicy, req = null) {
  const cadence = resolveCadence(body);
  const tension = tensionPromptBlock(ownerId, {});
  const ragLimit =
    body.rag_limit ?? morphicPolicy?.ragLimit ?? Number(process.env.RAG_LIMIT || 5);
  const ragMaxChars =
    body.rag_max_chars ?? morphicPolicy?.ragMaxChars ?? Number(process.env.RAG_MAX_CHARS || 3000);

  const egregoreId = body.egregore_id || body.egregore || null;
  const namespaces = resolveNamespaces(body, req);
  const matterId = body.matter_id || body.matterId || null;

  const rag = await retrieveContext(userQuery, {
    limit: ragLimit,
    maxChars: ragMaxChars,
    cadence: cadence.cadence,
    tensionIds: tension.tensionIds,
    egregoreId,
    namespaces,
    ownerId: ownerId || null,
    matterId,
  });

  const canon = canonPromptBlock();

  return {
    cadence,
    canonBlock: canon,
    tensionBlock: tension.text,
    tensionIds: tension.tensionIds,
    rag,
    namespaces,
    status: {
      canon: canonStatus(),
      memory: memoryStatus(),
    },
  };
}

module.exports = { assembleContinuity };
