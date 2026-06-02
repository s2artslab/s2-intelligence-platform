/** BitNet prompt shell — must match scripts/build-bitnet-egregore-dataset.py */

function egregoreBitnetPrompt(egregoreId, question, profile = {}) {
  const cap = String(egregoreId || 'assistant')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
  const designation = profile.designation || profile.specialty || cap;
  const q = String(question || '').trim();
  return (
    `Egregore: ${cap} (${designation})\n` +
    `Task: compact\n` +
    `Reply in under 80 words.\n\n` +
    `User: ${q}\n` +
    `${cap}:`
  );
}

module.exports = { egregoreBitnetPrompt };
