# Slack + Forge Operator Knowledge (Deep Key)

## Mission interface

S² operators conduct the ecosystem from **Slack** (Ninefold Studio `#s2-ecosystem`) and **Forge** — not from a local IDE. The control plane worker routes to hosted Ake Qwen on r730, Forge autofix/workspace MCP, Cloudflare/GitHub native ops, web search, and RAG.

## Thread-first rule

Agent memory binds to Slack threads. Reply in a thread on beta alerts so `/s2forge chat`, issue numbers, and autofix PRs stay in one session. Direct messages use one long-lived session per operator.

## Commands

- `/s2` or DM — chat with Ake (hosted Qwen or BYOK Groq)
- `/s2forge chat|fix|edit|repo` — beta triage, autofix PR, workspace edit, repo context
- `/s2status` — health snapshot
- `/s2focus set` — shared ecosystem focus for all stewards
- `/s2playbook` — operator playbook
- `/mcp` — Cloudflare Builds, GitHub Actions, browser render, web search

## Shipping loop

Beta alert in channel → thread reply → set repo → forge chat (creates GitHub issue) → forge fix (PR) → GitHub webhook notifies same Slack thread on PR merge → deploy per app runbook.

## Retrieval

Hosted gateway applies RAG over S² knowledge chunks. Control plane augments with web search (Brave or DuckDuckGo) when questions need fresh external facts. S²-specific answers should come from RAG; operators should publish docs to the knowledge ingest API after architecture changes.

## Proactive ops

Cron posts morning digest to `#s2-ecosystem` and health-change alerts every six hours when hosted Ake, Forge, RAG, or tokens degrade.

## Stewards

Operator allowlist uses `OPERATOR_ALLOWLIST` and `STEWARD_ALLOWLIST` on the worker. `/s2whoami` returns Slack user ID for onboarding stewards.

## Forge as workshop

`/s2forge edit s2artslab/repo task description` invokes Forge workspace MCP (14 tools). Visual review at forge.s2artslab.com. GitHub remains source of truth; human merges PRs.
