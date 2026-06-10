# S² Forge — app builder knowledge

S² Forge lets creators build networked apps and publish to the S² ecosystem catalog.

## AI contexts

- `guided_creation`, `guided_site_creation`, `guided_course_creation`, `workspace_code_editing`.
- Brand profiles and template hints shape system prompts.

## Knowledge pack export

When an app ships, publish a non-secret knowledge pack: README summary, user flows, API surface, support FAQs. Use `scripts/publish-forge-knowledge-pack.js` against the gateway ingest API.

## Rules

- Do not expose secrets, API keys, or private repo paths in collective RAG.
- Prefer actionable build steps over generic framework lectures.
