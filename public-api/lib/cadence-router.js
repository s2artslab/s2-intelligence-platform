/**
 * Layer 3 — Cadence (register). Resolves inference register from request context.
 */

const CADENCE_OVERLAYS = {
  legal: `CADENCE: legal compression. Numbered steps, deadlines, traps. No synthesis padding before substance.`,
  philosophy: `CADENCE: philosophical interpretive. Hold tension; do not premature unity.`,
  mystical: `CADENCE: symbolic / mythic interpretive. Sparse, precise; no decorative spirituality.`,
  systems: `CADENCE: systems architecture. Components, boundaries, failure modes.`,
  relational: `CADENCE: relational asymmetric. Directional; withhold false mutual validation.`,
  strategic: `CADENCE: strategic escalation. Stakes, options, commitment points.`,
  instructional: `CADENCE: instructional. Steps, checks, one focus at a time.`,
  synthesis: `CADENCE: synthesis. Integrate only after frames are named.`,
};

/**
 * @param {object} body - gateway request body
 * @returns {{ cadence: string, overlay: string, adapterHint: string }}
 */
function resolveCadence(body = {}) {
  if (body.cadence && CADENCE_OVERLAYS[body.cadence]) {
    return {
      cadence: body.cadence,
      overlay: CADENCE_OVERLAYS[body.cadence],
      adapterHint: `ake-${body.cadence === 'legal' ? 'legal' : body.cadence}`,
    };
  }

  const ctx = String(body.context || 'general').toLowerCase();
  const product = String(body.product_id || body.productId || '').toLowerCase();
  const text = [
    body.text,
    body.user_message,
    body.case_context,
    body.caseContext,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (
    ctx === 'legal' ||
    product.includes('psla') ||
    product.includes('prose') ||
    product.includes('pro-se') ||
    body.government_defendant_focus ||
    body.governmentDefendantFocus
  ) {
    return { cadence: 'legal', overlay: CADENCE_OVERLAYS.legal, adapterHint: 'ake-legal' };
  }

  if (/rule 12|motion to dismiss|qualified immunity|filing deadline/i.test(text)) {
    return { cadence: 'legal', overlay: CADENCE_OVERLAYS.legal, adapterHint: 'ake-legal' };
  }

  if (/architecture|deploy|pipeline|gateway|api\b/i.test(text)) {
    return {
      cadence: 'systems',
      overlay: CADENCE_OVERLAYS.systems,
      adapterHint: 'ake-systems',
    };
  }

  if (/deep key|ninefold|symbolic|threshold|egregore/i.test(text)) {
    return {
      cadence: 'philosophy',
      overlay: CADENCE_OVERLAYS.philosophy,
      adapterHint: 'ake-philosophy',
    };
  }

  if (body.exploration || product.includes('exploration')) {
    return {
      cadence: 'strategic',
      overlay: CADENCE_OVERLAYS.strategic,
      adapterHint: 'ake-strategic',
    };
  }

  return {
    cadence: 'synthesis',
    overlay: CADENCE_OVERLAYS.synthesis,
    adapterHint: 'ake',
  };
}

module.exports = { resolveCadence, CADENCE_OVERLAYS };
