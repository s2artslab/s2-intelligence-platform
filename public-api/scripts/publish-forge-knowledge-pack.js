#!/usr/bin/env node
/**
 * Forge / CI: publish a knowledge pack to the S² gateway ingest API.
 *
 * Usage:
 *   node scripts/publish-forge-knowledge-pack.js --pack ./knowledge-pack.json
 *   node scripts/publish-forge-knowledge-pack.js --app s2forge --readme ./README.md
 *
 * Env: S2_GATEWAY_URL, KNOWLEDGE_INGEST_KEY
 */
const fs = require('fs');
const path = require('path');
const { chunkPlainText } = require('../lib/knowledge-ingest');

function parseArgs(argv) {
  const out = { pack: null, app: null, readme: null };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--pack') out.pack = argv[++i];
    else if (argv[i] === '--app') out.app = argv[++i];
    else if (argv[i] === '--readme') out.readme = argv[++i];
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv);
  const base = process.env.S2_GATEWAY_URL || 'http://127.0.0.1:3010';
  const key = process.env.KNOWLEDGE_INGEST_KEY || process.env.STRATEGIST_HUB_API_KEY || '';

  let pack;
  if (args.pack) {
    pack = JSON.parse(fs.readFileSync(args.pack, 'utf8'));
  } else if (args.app && args.readme) {
    const text = fs.readFileSync(args.readme, 'utf8');
    const chunks = chunkPlainText(text).map((t, i) => ({
      id: `${args.app}:readme:${i}`,
      text: t,
      concept_tags: [args.app, 'readme'],
    }));
    pack = {
      product_id: args.app,
      chunks,
    };
  } else {
    console.error('Provide --pack file or --app + --readme');
    process.exit(1);
  }

  const res = await fetch(`${base.replace(/\/$/, '')}/api/internal/knowledge/publish-pack`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(key ? { 'X-API-Key': key } : {}),
    },
    body: JSON.stringify(pack),
  });

  const data = await res.json();
  if (!res.ok) {
    console.error(data);
    process.exit(1);
  }
  console.log(JSON.stringify(data, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
