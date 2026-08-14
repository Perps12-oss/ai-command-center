---
name: logfire-observability
description: Use before any Logfire or OpenTelemetry instrumentation in ai-command-center. Constrains the upstream logfire skills to ACC's telemetry firewall. Triggers on: add logfire, add tracing, add observability, instrument, spans, metrics, or OTel exporter changes.
---

# Logfire / OpenTelemetry (ACC constraint wrapper)

**Read this before invoking `logfire-instrumentation`, `logfire-query`, or
`logfire-ui`** (installed from `logfire@claude-plugins-official`, Pydantic,
v0.1.4).

## Why this wrapper exists

The upstream `logfire-instrumentation` skill is explicitly maximalist — its own
description says to "send as much useful telemetry as possible" and "maximize
observability". **That directly conflicts with ACC Invariant 9 (telemetry
firewall).** Where the two disagree, ACC wins. Use the upstream skill for
mechanics (SDK wiring, auto-instrumentation, exporter config); do **not** adopt
its default breadth.

## ACC governance deference

Local tooling under `.claude/` — **not** Level-1/2 authority (`CLAUDE.md` →
Authority). Higher authority wins:
`PROJECT_CONSTITUTION_V4.md` → `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md`
→ architecture + contracts → **Accepted** ADRs → `origin/main`.

Constitutional Pre-Flight under `docs/audits/` before implementing
(`acc-preflight`). Never writes to `docs/governance/IMPLEMENTATION_GUIDE.md`.

## Telemetry firewall — what may not be exported

Never place in a span, log record, metric label, or exception attribute:

- Prompt text, completion text, or any model input/output
- Secrets, API keys, tokens, or any part of them
- File contents, user documents, clipboard, or filesystem paths containing a
  username
- Anything read out of `keyring` (see `secrets-management`)

Auto-instrumentation is the main leak vector: `httpx`/`aiohttp` instrumentors
can capture request and response bodies and full URLs with query strings.
**Explicitly disable body capture** rather than relying on defaults, and audit
what an instrumentor emits before enabling it.

Safe to export: durations, counts, status codes, error *types*, queue depth,
model *identifier*, token *counts*. The shape of the work, never its content.

## Sending data off-host is an architecture decision

Pointing an exporter at Logfire's cloud, or any non-local endpoint, moves ACC
data off the host. That is not an implementation detail:

- It engages **host platform supremacy** (Inv 13) and the telemetry firewall.
- Do it only via `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md` with an
  accepted ADR (next free: **ADR-024**).
- Default to a **local** OTLP endpoint (`http://localhost:4317`) with a
  collector the user controls.

If asked to "just add Logfire", implement local-only and say plainly that cloud
export needs an ADR.

## Existing stack

ACC already depends on `opentelemetry-api`, `opentelemetry-sdk` and an exporter.
Logfire is an OTel-compatible layer on top — **do not add a second, parallel
telemetry pipeline** (Inv 11, single source of truth; Inv 12, non-circumvention).
Instrument through the existing provider, or replace it wholesale under an ADR;
do not run both.

## Async and UI constraints

- Exporters must not block the event loop; use the batching processor and never
  force-flush inside a request path.
- Shutdown must flush with a **bounded** timeout (Art. XVII, `.result()` timeout
  rule) — an unbounded `force_flush()` will hang shutdown when no collector is
  listening.
- No instrumentation inside UI callbacks that could exceed a frame budget.

## Review checklist

- [ ] No prompt/completion/secret/file content in any span or log
- [ ] Auto-instrumentation body capture explicitly disabled
- [ ] Exporter endpoint is local unless an accepted ADR says otherwise
- [ ] No second telemetry pipeline alongside the existing OTel provider
- [ ] Flush on shutdown is time-bounded
