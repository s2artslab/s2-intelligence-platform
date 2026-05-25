/**
 * Per-product sampling defaults when clients omit temperature.
 * PSLA = cold (record-grounded legal). Strategist / Sharayah = warm (creative strategy).
 */

const PRODUCT_TEMPERATURE = {
  'psla-hosted': 0.12,
  'psla-exploration': 0.15,
  strategist: 0.72,
  'sharayah-strategist': 0.72,
  sharayah: 0.72,
};

function productIdFrom(req, fallback = '') {
  return String(
    req.get('X-S2-Product-Id') ||
      req.body?.product_id ||
      req.body?.productId ||
      fallback,
  )
    .trim()
    .toLowerCase();
}

function temperatureForProduct(productId) {
  const product = String(productId || '').trim().toLowerCase();
  if (!product) return null;
  if (Object.prototype.hasOwnProperty.call(PRODUCT_TEMPERATURE, product)) {
    return PRODUCT_TEMPERATURE[product];
  }
  if (product.startsWith('psla')) return PRODUCT_TEMPERATURE['psla-hosted'];
  if (product.includes('strategist') || product.includes('sharayah')) {
    return PRODUCT_TEMPERATURE.strategist;
  }
  return null;
}

function resolveTemperature(req, { endpointDefault = 0.2, productFallback = '' } = {}) {
  if (req.body?.temperature != null && req.body?.temperature !== '') {
    const explicit = Number(req.body.temperature);
    if (Number.isFinite(explicit) && explicit >= 0 && explicit <= 2) return explicit;
  }
  const fromProduct = temperatureForProduct(productIdFrom(req, productFallback));
  if (fromProduct != null) return fromProduct;
  return endpointDefault;
}

module.exports = {
  PRODUCT_TEMPERATURE,
  productIdFrom,
  temperatureForProduct,
  resolveTemperature,
};
