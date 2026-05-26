#!/usr/bin/env node
/**
 * Build data/retrieval-index.json from canon + knowledge + discourse index.
 * Usage: node scripts/build-retrieval-index.js
 */
const fs = require('fs');
const path = require('path');

process.chdir(path.join(__dirname, '..'));

const outPath =
  process.env.S2_RETRIEVAL_INDEX || path.join(__dirname, '..', 'data', 'retrieval-index.json');

const { reloadIndex, loadAllChunks, indexStatus } = require('../lib/retrieval-index');

reloadIndex();
const chunks = loadAllChunks();
const status = indexStatus();

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(
  outPath,
  JSON.stringify(
    {
      generated_at: new Date().toISOString(),
      chunk_count: chunks.length,
      by_layer: status.byLayer,
      chunks,
    },
    null,
    2,
  ),
  'utf8',
);

console.log(`Wrote ${chunks.length} chunks → ${outPath}`);
