/**
 * Proxy PDF/image processing to S2 Document Intelligence (public tunnel).
 * Enables PSLA web clients without calling localhost:5000 from the browser.
 */

const DEFAULT_DOC_INTEL =
  process.env.DOCUMENT_INTELLIGENCE_URL ||
  process.env.S2_DOCUMENT_INTELLIGENCE_URL ||
  'https://document-intelligence.s2artslab.com';

async function docIntelHealth(baseUrl = DEFAULT_DOC_INTEL) {
  const root = baseUrl.replace(/\/$/, '');
  try {
    const res = await fetch(`${root}/health`, { signal: AbortSignal.timeout(8000) });
    return { ok: res.ok, status: res.status, url: root };
  } catch (e) {
    return { ok: false, error: e.message, url: root };
  }
}

async function processPdfProxy({ bytes, filename, baseUrl = DEFAULT_DOC_INTEL }) {
  const root = baseUrl.replace(/\/$/, '');
  const form = new FormData();
  const blob = new Blob([bytes], { type: 'application/pdf' });
  form.append('file', blob, filename || 'document.pdf');
  form.append('enable_ocr', 'true');

  const res = await fetch(`${root}/process/pdf`, {
    method: 'POST',
    body: form,
    signal: AbortSignal.timeout(120000),
  });

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const err = new Error(data?.detail || data?.message || `Doc-intel HTTP ${res.status}`);
    err.statusCode = res.status;
    throw err;
  }

  const documentId = data.document_id || data.documentId;
  const payload = data.data || data;
  const extracted = extractTextFromPayload(payload);
  return {
    success: true,
    extractedText: extracted,
    documentId: payload?.document_id || payload?.documentId || null,
  };
}

function extractTextFromPayload(payload) {
  if (!payload || typeof payload !== 'object') return '';
  const parts = [];
  const pages = payload.pages;
  if (Array.isArray(pages)) {
    for (const page of pages) {
      const blocks = page?.blocks;
      if (!Array.isArray(blocks)) continue;
      for (const block of blocks) {
        const t = block?.text;
        if (t && String(t).trim()) parts.push(String(t).trim());
      }
    }
  }
  if (parts.length > 0) return parts.join('\n\n');
  return String(payload.text || payload.extracted_text || '').trim();
}

module.exports = {
  DEFAULT_DOC_INTEL,
  docIntelHealth,
  processPdfProxy,
};
