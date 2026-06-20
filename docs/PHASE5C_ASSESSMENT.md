# Phase 5C Assessment — Capability Gap Map

**Date:** 2026-06-18  
**Session telemetry:** `20260618T132909Z`  
**Verdict:** Architecture PASS · Stability PASS · **Usability FAIL**

---

## Capability gap map

| Area | Status | Priority |
|------|--------|----------|
| EventBus | Complete | Low |
| AppState | Complete | Low |
| Telemetry | Complete | Low |
| Ollama Chat | Working | Medium |
| Clipboard Actions | Broken | **Critical** |
| Note Search | Partial | **Critical** |
| Vault Setup UX | Broken | **Critical** |
| Intent Routing | Weak | **Critical** |
| Shell Commands | Partial | High |
| Browser Fallback | Too Aggressive | High |
| Memory Features | Unclear | Medium |
| Plugins | Fine | Low |
| V2 Brain Layer | Premature | Ignore |

---

## Telemetry evidence (session `20260618T132909Z`)

| Metric | Value | Implication |
|--------|-------|-------------|
| Command success rate | 11/17 (65%) | Critical paths failing |
| Avg latency | ~51s | HIGH friction driver |
| Hesitation rate | 50% | Palette UX noise during test; also discoverability |
| Context over budget | 0 | Context assembly OK when chat runs |
| Friction score | HIGH | Not daily-driver ready |

---

## Root causes

| ID | Cause | Evidence |
|----|-------|----------|
| RC-1 | `intent_router_too_weak` | Plain text → chat; `echo` without `>` misrouted; no `go settings` discoverability |
| RC-2 | `browser_fallback_overused` | No in-app browser code — likely **model output + OS search**, not EventBus. Mitigate via routing + system prompt guard |
| RC-3 | `clipboard_actions_broken` | Empty/missing clipboard still chats; summarizes history instead of error |
| RC-4 | `obsidian_onboarding_missing` | Vault field exists but undiscoverable; errors opaque |
| RC-5 | `capability_discoverability_low` | Prefix commands (`>`, `note:`, `go `) not surfaced in UX |
| RC-6 | `latency_high` | Local Ollama + model size; acceptable but hurts trust |

```yaml
phase5c_assessment:
  architecture:
    status: pass
  stability:
    status: pass
  usability:
    status: fail

root_causes:
  - intent_router_too_weak
  - browser_fallback_overused
  - clipboard_actions_broken
  - obsidian_onboarding_missing
  - capability_discoverability_low
  - latency_high

v2_readiness:
  status: not_ready
  blocker:
    - current_capabilities_not_trustworthy_yet
```

---

## Next sprint: `capability_completion`

**Goal:** Make existing capabilities trustworthy before any V2/brain work.

| # | Deliverable | Fixes | Gate |
|---|-------------|-------|------|
| 1 | Clipboard guard | Empty clipboard + “clipboard” in query → `chat.error`, no silent fallback | `verify_capability_clipboard.py` |
| 2 | Vault onboarding UX | Settings status banner, browse hint, validate path on save | manual + settings round-trip |
| 3 | Intent routing v2 | Prefix help; auto-`>` for obvious shell; `settings`/`chat` aliases → `go` | `verify_capability_routing.py` |
| 4 | Capability discoverability | Command box placeholder + `?` / help panel listing prefixes | manual |
| 5 | Memory feedback | `memory.stored` → visible chat system line; format hints on bad input | extends 5A path |
| 6 | Latency (optional) | Surface model label + “slow model” warning; document `llama3.2:3b` default | telemetry target &lt;15s |

**Out of scope this sprint:** V2 brain, agents, embeddings, packaging (5D).

```yaml
next_sprint:
  name: capability_completion
  goals:
    - fix_clipboard
    - fix_notes
    - improve_intent_routing
    - reduce_latency
    - expose_capabilities
```

---

## Phase 5C gate status

| Criterion | Result |
|-----------|--------|
| Core Loop ≥ 4 | **FAIL** (telemetry + manual) |
| Context ≥ 4 | **FAIL** |
| Failure Recovery ≥ 4 | **PASS** (Ollama down/up) |
| Scorecard recorded | **PENDING** |
| **Overall 5C** | **FAIL** — acceptable; findings drive sprint |

Re-run stress test after sprint items 1–4 before claiming 5C PASS.
