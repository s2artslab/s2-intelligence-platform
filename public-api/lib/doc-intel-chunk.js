/**
 * Chunk document-intel extracted text for RAG ingest.
 */

const { chunkPlainText, appendPrivateChunks, appendCollectiveChunk } = require('./knowledge-ingest');

function ingestExtractedDocument({
  text,
  filename,
  productId,
  ownerId,
  matterId,
  collective = false,
  namespaces,
}) {
  const chunks = chunkPlainText(text);
  if (!chunks.length) {
    throw new Error('No chunkable text in document');
  }

  const defaultNs = namespaces || (productId ? [`product:${productId}`, 's2-canon'] : ['s2-canon']);
  if (matterId || (ownerId && !collective)) {
    const items = chunks.map((t, i) => ({
      id: `doc:${filename || 'pdf'}:${i}`,
      text: t,
      namespaces: matterId ? [`matter:${matterId}`, ...defaultNs] : defaultNs,
      concept_tags: ['document', filename || 'pdf'],
      source: filename || 'document.pdf',
    }));
    return appendPrivateChunks({ ownerId, matterId, chunks: items });
  }

  const results = [];
  for (let i = 0; i < chunks.length; i += 1) {
    results.push(
      appendCollectiveChunk({
        id: `doc:${filename || 'pdf'}:${i}`,
        text: chunks[i],
        namespaces: defaultNs,
        concept_tags: ['document', filename || 'pdf'],
        source: filename || 'document.pdf',
      }),
    );
  }
  return { ingested: results.length, collective: true, files: results };
}

module.exports = { ingestExtractedDocument, chunkPlainText };
