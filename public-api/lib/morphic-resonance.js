/**
 * Backward-compatible morphic policy API.
 * Delegates knob resolution to inference-profile.js (decoupled axes).
 */

const {
  resolveInferenceProfile,
  applyProfileTemperature,
} = require('./inference-profile');

/**
 * @param {object} [body]
 * @returns {import('./inference-profile').resolveInferenceProfile extends (...args: any[]) => infer R ? R : never}
 */
function resolveMorphicPolicy(body = {}) {
  return resolveInferenceProfile(body);
}

/** @deprecated Use applyProfileTemperature */
function applyMorphicTemperature(productTemp, morphicPolicy) {
  return applyProfileTemperature(productTemp, morphicPolicy);
}

module.exports = {
  resolveMorphicPolicy,
  applyMorphicTemperature,
  applyProfileTemperature,
  resolveInferenceProfile,
};
