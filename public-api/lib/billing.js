/**
 * Hosted inference entitlement check via S² billing worker.
 */

const BILLING_BASE = (process.env.BILLING_API_URL || '').replace(/\/$/, '');
const BILLING_KEY = process.env.BILLING_API_KEY || '';
const REQUIRE_BILLING = process.env.HOSTED_REQUIRE_BILLING === 'true';
const LAB_HOSTED_UNLOCK = process.env.LAB_HOSTED_UNLOCK === 'true';

async function verifyHostedEntitlement(ownerId, productId) {
  if (LAB_HOSTED_UNLOCK) {
    return { ok: true, active: true, status: 'lab' };
  }
  if (!REQUIRE_BILLING) {
    return { ok: true, active: true, status: 'billing_not_required' };
  }
  if (!ownerId?.trim()) {
    const err = new Error('X-Owner-Id required for hosted inference');
    err.statusCode = 401;
    throw err;
  }
  if (!BILLING_BASE) {
    const err = new Error('Billing API not configured (BILLING_API_URL)');
    err.statusCode = 503;
    throw err;
  }

  const params = new URLSearchParams({ ownerId: ownerId.trim() });
  if (productId) params.set('productId', productId);

  const headers = { Accept: 'application/json' };
  if (BILLING_KEY) headers.Authorization = `Bearer ${BILLING_KEY}`;

  const res = await fetch(`${BILLING_BASE}/api/billing/status?${params}`, {
    headers,
    signal: AbortSignal.timeout(15000),
  });

  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {};
  }

  if (!res.ok) {
    const err = new Error(data?.error || `Billing status HTTP ${res.status}`);
    err.statusCode = res.status === 401 ? 401 : 503;
    throw err;
  }

  const active = data.active === true;
  if (!active) {
    const err = new Error('Active hosted subscription required');
    err.statusCode = 402;
    throw err;
  }

  return { ok: true, active: true, status: data.status || 'active', tier: data.tier };
}

module.exports = { verifyHostedEntitlement, REQUIRE_BILLING, LAB_HOSTED_UNLOCK };
