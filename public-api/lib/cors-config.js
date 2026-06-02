/**
 * CORS for browser clients (PSLA web on psla.s2artslab.com, etc.).
 * When nginx terminates TLS and adds CORS, set BEHIND_NGINX_CORS=true to avoid duplicate headers.
 */

const DEFAULT_ALLOWED_ORIGINS = [
  'https://psla.s2artslab.com',
  'https://s2artslab.com',
  'https://www.s2artslab.com',
  'https://app.s2artslab.com',
  'http://localhost',
  'http://127.0.0.1',
];

function parseAllowedOrigins() {
  const raw = (process.env.CORS_ORIGIN || '').trim();
  if (!raw || raw === '*') {
    return { allowAll: raw === '*', origins: DEFAULT_ALLOWED_ORIGINS };
  }
  const list = raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  return { allowAll: false, origins: list.length ? list : DEFAULT_ALLOWED_ORIGINS };
}

function buildCorsMiddleware() {
  if (process.env.BEHIND_NGINX_CORS === 'true') {
    return (_req, _res, next) => next();
  }

  const { allowAll, origins } = parseAllowedOrigins();
  const allowed = new Set(origins);

  return (req, res, next) => {
    const origin = req.headers.origin;
    if (req.method === 'OPTIONS') {
      if (origin && (allowAll || allowed.has(origin) || isLocalDev(origin))) {
        res.setHeader('Access-Control-Allow-Origin', allowAll ? '*' : origin);
        res.setHeader('Vary', 'Origin');
        res.setHeader(
          'Access-Control-Allow-Methods',
          'GET, POST, PUT, DELETE, OPTIONS',
        );
        res.setHeader(
          'Access-Control-Allow-Headers',
          [
            'Content-Type',
            'Authorization',
            'X-Groq-Api-Key',
            'X-User-Id',
            'X-Owner-Id',
            'X-S2-Inference',
            'X-S2-Product-Id',
          ].join(', '),
        );
        res.setHeader('Access-Control-Max-Age', '86400');
      }
      return res.sendStatus(204);
    }

    if (origin && (allowAll || allowed.has(origin) || isLocalDev(origin))) {
      res.setHeader('Access-Control-Allow-Origin', allowAll ? '*' : origin);
      if (!allowAll) res.setHeader('Vary', 'Origin');
    }
    next();
  };
}

function isLocalDev(origin) {
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
}

module.exports = { buildCorsMiddleware, DEFAULT_ALLOWED_ORIGINS };
