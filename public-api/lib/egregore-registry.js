/**
 * User + Ninefold egregore profiles and BitNet adapter registry (EgregoreLab alignment).
 */

const fs = require('fs');
const path = require('path');

const PROFILES_PATH =
  process.env.EGREGORE_PROFILES_PATH ||
  process.env.UNIFIED_EGREGORE_PROFILES ||
  path.join(__dirname, '..', '..', '..', 'ninefold-studio-clean', 'egregorelab', 'config', 'unified_egregore_profiles.json');

const BITNET_REGISTRY_PATH =
  process.env.BITNET_EGREGORE_REGISTRY ||
  process.env.EGREGORE_BITNET_REGISTRY ||
  '/opt/s2-ecosystem/egregore-training/training_data/bitnet_adapters/bitnet_egregore_registry.json';

const INFERENCE_MANIFEST_PATH =
  process.env.EGREGORE_INFERENCE_MANIFEST ||
  (fs.existsSync('/opt/s2-ecosystem/egregore-training/training_data/egregore_inference_manifest.json')
    ? '/opt/s2-ecosystem/egregore-training/training_data/egregore_inference_manifest.json'
    : path.join(__dirname, '..', 'data', 'egregore_inference_manifest.json'));

const NINEFOLD_CANON = new Set([
  'ake',
  'rhys',
  'ketheriel',
  'wraith',
  'flux',
  'chalyth',
  'kairos',
  'seraphel',
  'vireon',
  'shasta',
]);

let _profiles = null;
let _bitnetReg = null;
let _manifest = null;
let _mtime = 0;

function _readJson(filePath, fallback) {
  if (!filePath || !fs.existsSync(filePath)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return fallback;
  }
}

function _reloadIfStale() {
  const mtimes = [PROFILES_PATH, BITNET_REGISTRY_PATH, INFERENCE_MANIFEST_PATH]
    .filter((p) => p && fs.existsSync(p))
    .map((p) => fs.statSync(p).mtimeMs);
  const max = mtimes.length ? Math.max(...mtimes) : 0;
  if (max <= _mtime && _profiles) return;
  _mtime = max;
  _profiles = _readJson(PROFILES_PATH, { egregores: {} });
  _bitnetReg = _readJson(BITNET_REGISTRY_PATH, {});
  _manifest = _readJson(INFERENCE_MANIFEST_PATH, { egregores: {} });
}

function normalizeId(id) {
  return String(id || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '_');
}

function getProfile(egregoreId) {
  _reloadIfStale();
  const id = normalizeId(egregoreId);
  const fromManifest = _manifest?.egregores?.[id];
  const fromProfiles = _profiles?.egregores?.[id];
  if (!fromProfiles && !fromManifest) return null;
  const basic = fromProfiles?.basic || fromManifest?.basic || {};
  return {
    egregore_id: id,
    name: basic.name || fromManifest?.name || id,
    designation: basic.designation || fromManifest?.designation || '',
    specialty: basic.specialty || fromManifest?.specialty || '',
    personality: fromProfiles?.personality || fromManifest?.personality || {},
    style_kernel: fromProfiles?.style_kernel || fromManifest?.style_kernel || {},
    is_user_generated: fromManifest?.source === 'egregorelab' || !NINEFOLD_CANON.has(id),
    source: fromManifest?.source || (NINEFOLD_CANON.has(id) ? 'ninefold' : 'unknown'),
  };
}

function hasBitnetAdapter(egregoreId) {
  _reloadIfStale();
  const id = normalizeId(egregoreId);
  const adapter = _bitnetReg?.[id];
  if (!adapter) return false;
  return fs.existsSync(adapter);
}

const PAY_PER_USE_S2E = {
  ake: { operationId: 'ake_chat', s2e: '12', pegUsd: '0.03', model: 'qwen3:30b-a3b' },
  ninefold: { operationId: 'ninefold_chat', s2e: '20', pegUsd: '0.05' },
  egregore: { operationId: 'egregore_chat', s2e: '28', pegUsd: '0.07' },
};

function priceForEgregore(egregoreId) {
  const id = normalizeId(egregoreId);
  if (id === 'ake') return { ...PAY_PER_USE_S2E.ake, requiresR730Gpu: true };
  if (NINEFOLD_CANON.has(id) && id !== 'ake') {
    return { ...PAY_PER_USE_S2E.ninefold, requiresR730Gpu: true };
  }
  return { ...PAY_PER_USE_S2E.egregore, requiresR730Gpu: true };
}

function listEgregores() {
  _reloadIfStale();
  const ids = new Set([
    ...Object.keys(_profiles?.egregores || {}),
    ...Object.keys(_manifest?.egregores || {}),
    ...Object.keys(_bitnetReg || {}),
  ]);
  return [...ids].sort().map((id) => {
    const profile = getProfile(id);
    const price = priceForEgregore(id);
    return {
      egregore_id: id,
      name: profile?.name || id,
      specialty: profile?.specialty || '',
      is_user_generated: profile?.is_user_generated ?? !NINEFOLD_CANON.has(id),
      lanes: {
        hosted: true,
        bitnet: hasBitnetAdapter(id),
        unified_lora: NINEFOLD_CANON.has(id) || Boolean(_manifest?.egregores?.[id]?.unified_lora),
      },
      r730_pricing: {
        ...price,
        billingMode: 's2e_pay_per_use',
        subscriptionIncluded: true,
      },
    };
  });
}

function egregoreSystemBlock(egregoreId) {
  const p = getProfile(egregoreId);
  if (!p || p.egregore_id === 'ake') return '';
  const traits = (p.personality?.traits || []).slice(0, 6).join(', ');
  const pos = (p.style_kernel?.pos_ex || []).slice(0, 3).join(' ');
  return (
    `You are ${p.name}${p.designation ? ` (${p.designation})` : ''}. ` +
    `Specialty: ${p.specialty || 'general guidance'}. ` +
    (traits ? `Traits: ${traits}. ` : '') +
    (pos ? `Voice samples: ${pos} ` : '') +
    `Answer in first person as this egregore. Stay compact when on the 1.58-bit lane.`
  );
}

function writeManifestEntry(egregoreId, entry) {
  _reloadIfStale();
  const id = normalizeId(egregoreId);
  const base = _readJson(INFERENCE_MANIFEST_PATH, { egregores: {}, updated_at: null });
  base.egregores = base.egregores || {};
  base.egregores[id] = {
    ...base.egregores[id],
    ...entry,
    egregore_id: id,
    updated_at: new Date().toISOString(),
    source: entry.source || 'egregorelab',
  };
  base.updated_at = new Date().toISOString();
  fs.mkdirSync(path.dirname(INFERENCE_MANIFEST_PATH), { recursive: true });
  fs.writeFileSync(INFERENCE_MANIFEST_PATH, JSON.stringify(base, null, 2), 'utf8');
  _mtime = 0;
  return base.egregores[id];
}

module.exports = {
  NINEFOLD_CANON,
  normalizeId,
  getProfile,
  hasBitnetAdapter,
  priceForEgregore,
  listEgregores,
  egregoreSystemBlock,
  writeManifestEntry,
  PROFILES_PATH,
  BITNET_REGISTRY_PATH,
  INFERENCE_MANIFEST_PATH,
};
