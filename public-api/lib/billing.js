/**
 * Hosted inference billing via S² billing worker.
 * - Subscribers: included (no per-call S2E debit).
 * - Everyone else on r730: pay-per-use S2E (buy credits, debit per prompt/generation).
 */

const BILLING_BASE = (process.env.BILLING_API_URL || '').replace(/\/$/, '');
const BILLING_KEY = process.env.BILLING_API_KEY || '';
const REQUIRE_BILLING = process.env.HOSTED_REQUIRE_BILLING === 'true';
const LAB_HOSTED_UNLOCK = process.env.LAB_HOSTED_UNLOCK === 'true';

async function billingFetch(path, { method = 'GET', body, params } = {}) {
  const url = new URL(`${BILLING_BASE}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v != null && v !== '') url.searchParams.set(k, String(v));
    }
  }
  const headers = { Accept: 'application/json' };
  if (BILLING_KEY) headers.Authorization = `Bearer ${BILLING_KEY}`;
  if (body) headers['Content-Type'] = 'application/json';

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000),
  });

  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {};
  }
  return { res, data };
}

/**
 * Charge S2E (or confirm subscription included) before r730 inference.
 */
async function verifyHostedEntitlement(ownerId, productId, options = {}) {
  if (LAB_HOSTED_UNLOCK) {
    return { ok: true, active: true, status: 'lab', accessPath: 'lab', charged: false };
  }
  if (!REQUIRE_BILLING) {
    return {
      ok: true,
      active: true,
      status: 'billing_not_required',
      accessPath: 'dev',
      charged: false,
    };
  }
  if (!ownerId?.trim()) {
    const err = new Error('X-Owner-Id required for r730 inference');
    err.statusCode = 401;
    throw err;
  }
  if (!BILLING_BASE) {
    const err = new Error('Billing API not configured (BILLING_API_URL)');
    err.statusCode = 503;
    throw err;
  }

  const egregoreId = options.egregoreId || options.egregore_id || 'ake';
  const chargeBody = {
    ownerId: ownerId.trim(),
    egregoreId,
    appId: options.appId || options.app_id,
    walletAddress: options.walletAddress || options.wallet_address,
    operation: options.operation,
    longForm: options.longForm === true || options.long_form === true,
    inferenceLane: options.inferenceLane || options.inference_lane,
    mediaKind: options.mediaKind || options.media_kind,
    idempotency: options.idempotency || options.idempotencyKey,
  };

  const charge = await billingFetch('/api/billing/inference/charge', {
    method: 'POST',
    body: chargeBody,
  });

  if (charge.res.ok && charge.data?.ok) {
    return {
      ok: true,
      active: true,
      accessPath: charge.data.accessPath,
      charged: charge.data.charged === true,
      s2eCharged: charge.data.s2eCharged || '0',
      balanceS2e: charge.data.balanceS2e,
      operationId: charge.data.operationId,
      egregoreId: charge.data.egregoreId || egregoreId,
    };
  }

  const err = new Error(
    charge.data?.error || 'S2E credits required for r730 inference — purchase S2E to continue',
  );
  err.statusCode = charge.res.status === 401 ? 401 : 402;
  err.s2eRequired = charge.data?.s2eRequired;
  err.balanceS2e = charge.data?.balanceS2e;
  err.catalog = charge.data?.catalog;
  err.operationId = charge.data?.operationId;
  throw err;
}

module.exports = { verifyHostedEntitlement, REQUIRE_BILLING, LAB_HOSTED_UNLOCK };
