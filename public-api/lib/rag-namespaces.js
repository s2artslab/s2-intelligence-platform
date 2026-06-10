/**
 * Product → default RAG namespace resolution for ecosystem apps.
 * Namespaces: s2-canon, community, legal, media, wellness, learning, product:{id}
 */

const PRODUCT_DEFAULTS = {
  'pro-se-legal': ['s2-canon', 'legal', 'product:pro-se-legal'],
  'psla': ['s2-canon', 'legal', 'product:pro-se-legal'],
  'allies-and-artists': ['s2-canon', 'community', 'product:allies-and-artists'],
  'daoflow': ['s2-canon', 'community', 'product:daoflow'],
  's2-pantry': ['s2-canon', 'community', 'product:s2-pantry'],
  'tribe-mapper': ['s2-canon', 'community', 'product:allies-and-artists'],
  's2-learning-hub': ['s2-canon', 'learning', 'product:s2-learn'],
  's2-learn': ['s2-canon', 'learning', 'product:s2-learn'],
  s2forge: ['s2-canon', 'learning', 'product:s2forge'],
  's2forge': ['s2-canon', 'learning', 'product:s2forge'],
  innerpath: ['s2-canon', 'wellness', 'product:innerpath'],
  'innerpath-ai': ['s2-canon', 'wellness', 'product:innerpath'],
  pathworking: ['s2-canon', 'wellness', 'product:innerpath'],
  'pneuma-temple': ['s2-canon', 'wellness', 'product:temple'],
  temple: ['s2-canon', 'wellness', 'product:temple'],
  'soundscapes-biofeedback-audio': ['s2-canon', 'wellness', 'product:soundscapes'],
  soundscapes: ['s2-canon', 'wellness', 'product:soundscapes'],
  'vitalsync-health-wellness': ['s2-canon', 'wellness', 'product:vitalsync'],
  'volt-farm': ['s2-canon', 'wellness', 'media', 'product:volt-farm'],
  'ancestry-research-pro': ['s2-canon', 'learning', 'product:ancestry'],
  ancestry: ['s2-canon', 'learning', 'product:ancestry'],
  's2-research': ['s2-canon', 'learning', 'product:s2-research'],
  'vr-world-build': ['s2-canon', 'media', 'product:vr-world-build'],
  'piper-moxie': ['s2-canon', 'media', 'product:piper-moxie'],
  'ninefold-studio': ['s2-canon', 'media', 'learning', 'product:ninefold-studio'],
  's2-live-podcast': ['s2-canon', 'media', 'product:s2-live-podcast'],
  'entheo-news': ['s2-canon', 'media', 'product:entheo-news'],
  'my-music-desktop': ['s2-canon', 'learning', 'product:my-music-desktop'],
  's2artslab-web': ['s2-canon', 'community', 'product:s2artslab-web'],
};

function normalizeId(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/_/g, '-');
}

function uniq(list) {
  return [...new Set(list.filter(Boolean))];
}

function parseNamespaceList(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return uniq(raw.map((n) => String(n).trim()).filter(Boolean));
  if (typeof raw === 'string') {
    return uniq(
      raw
        .split(/[,;\s]+/)
        .map((n) => n.trim())
        .filter(Boolean),
    );
  }
  return [];
}

function resolveNamespaces(body = {}, req = null) {
  const explicit = parseNamespaceList(body.rag_namespaces || body.ragNamespaces);
  if (explicit.length) return explicit;

  const product = normalizeId(
    body.product_id ||
      body.productId ||
      body.appId ||
      body.app_id ||
      req?.get?.('X-S2-Product-Id') ||
      req?.get?.('x-s2-product-id'),
  );

  if (product && PRODUCT_DEFAULTS[product]) {
    return uniq([...PRODUCT_DEFAULTS[product], 's2-canon']);
  }

  const context = String(body.context || '').toLowerCase();
  if (context === 'legal') return ['s2-canon', 'legal', 'product:pro-se-legal'];

  return ['s2-canon', 'community'];
}

function chunkMatchesNamespaces(chunk, namespaces) {
  if (!namespaces?.length) return true;
  const chunkNs = chunk.namespaces || [];
  if (!chunkNs.length) {
    return namespaces.includes('s2-canon') || namespaces.includes('community');
  }
  return chunkNs.some((n) => namespaces.includes(n));
}

module.exports = {
  PRODUCT_DEFAULTS,
  resolveNamespaces,
  chunkMatchesNamespaces,
  normalizeId,
};
