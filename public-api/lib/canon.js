/**
 * Layer 1 — Canon (invariance). Loads curated doctrine from S2_CANON_DIR.
 */

const fs = require('fs');
const path = require('path');

const CANON_DIR =
  process.env.S2_CANON_DIR ||
  resolveDefaultCanonDir();

function resolveDefaultCanonDir() {
  const candidates = [
    path.join(__dirname, '..', 'canon'),
    path.join(__dirname, '..', '..', '..', 's2-research', 'canon'),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return candidates[0];
}

let _entries = null;

function parseFrontmatter(raw) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/.exec(raw);
  if (!match) return { meta: {}, body: raw.trim() };
  const meta = {};
  for (const line of match[1].split(/\r?\n/)) {
    const m = /^([a-zA-Z0-9_.-]+):\s*(.+)$/.exec(line.trim());
    if (m) meta[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
  return { meta, body: match[2].trim() };
}

function walkMarkdown(dir, base = '') {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const rel = base ? `${base}/${name}` : name;
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      out.push(...walkMarkdown(full, rel));
    } else if (/\.md$/i.test(name) && name.toLowerCase() !== 'readme.md') {
      const raw = fs.readFileSync(full, 'utf8');
      const { meta, body } = parseFrontmatter(raw);
      if (body.length < 8) continue;
      out.push({
        id: meta.id || rel.replace(/\.md$/i, '').replace(/\//g, '.'),
        text: body,
        layer: 'canon',
        source: rel,
        stable: meta.stable === 'true' || meta.stable === true,
        concept_tags: String(meta.tags || '')
          .replace(/^\[|\]$/g, '')
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        discourse_role: 'axiom',
      });
    }
  }
  return out;
}

function loadCanonEntries() {
  if (_entries !== null) return _entries;
  _entries = walkMarkdown(CANON_DIR);
  console.log(`[canon] loaded ${_entries.length} entries from ${CANON_DIR}`);
  return _entries;
}

/** Compact constitutional block for system prompt (token-budgeted). */
function canonPromptBlock(opts = {}) {
  const maxChars = opts.maxChars ?? Number(process.env.CANON_MAX_CHARS || 1200);
  const entries = loadCanonEntries();
  if (!entries.length) return '';

  const stable = entries.filter((e) => e.stable !== false);
  const parts = [];
  let total = 0;
  for (const e of stable.length ? stable : entries) {
    const block = e.text.length > 280 ? `${e.text.slice(0, 277)}…` : e.text;
    const line = `• ${block}`;
    if (total + line.length > maxChars) break;
    parts.push(line);
    total += line.length;
  }
  if (!parts.length) return '';
  return parts.join('\n');
}

function canonStatus() {
  const entries = loadCanonEntries();
  return {
    available: entries.length > 0,
    entryCount: entries.length,
    canonDir: CANON_DIR,
  };
}

function reloadCanon() {
  _entries = null;
  return loadCanonEntries();
}

module.exports = {
  CANON_DIR,
  loadCanonEntries,
  canonPromptBlock,
  canonStatus,
  reloadCanon,
};
