# Strategic Gap Matrix — Phase 0 Baseline

**Status:** PHASE 0 DELIVERABLE — baseline for the Strategic Runtime & Architecture Completion Program (snapshot 2026-08-14; **not** live implementation status). Wave 5 close-out: [`WAVE_5_FULL_SYSTEM_VERIFICATION.md`](WAVE_5_FULL_SYSTEM_VERIFICATION.md).  
**Date:** 2026-08-14  
**Baseline:** `origin/main` @ `2f6c88b`  
**Program:** [`docs/governance/STRATEGIC_RUNTIME_PROGRAM.md`](../governance/STRATEGIC_RUNTIME_PROGRAM.md)  
**Rule:** Exists ≠ Wired ≠ Authoritative. This matrix is evidence, not a license to skip Gates 1–3.

Effort column uses the program envelope (Small / Medium / Large). Hours remain **97–167** at program level until Gate 2.

---

## How to read

For every stream: **Spec → ADR → implementation → tests → runtime evidence** must be traced. “Missing decision” means Gate 2 is not closed for the remaining work, even if a parent ADR is Accepted.

---

## Stream A — ADR-021 Explainability

| Field | Answer |
|-------|--------|
| **Documented requirement** | Primary explainability is a **Decision Record** (Evidence + Policy + Receipts + Verification), not model CoT. [`ADR-021_EXPLAINABILITY.md`](../architecture/adr/ADR-021_EXPLAINABILITY.md) Council Decision + Section 9 M1–M5. |
| **Current implementation** | `DecisionRecord` dataclass exists ([`domain/decision_record.py`](../../ai_command_center/domain/decision_record.py)). Topics `decision.record.updated` / `autonomy.score.updated` in [`topics.py`](../../ai_command_center/core/events/topics.py). AppState projects records ([`app_state.py`](../../ai_command_center/core/app_state.py) `decision_record`). Orchestrator emits **only** on awaiting-approval and replan-stuck (`_publish_decision_and_autonomy` in [`execution_orchestrator_service.py`](../../ai_command_center/services/execution_orchestrator_service.py)). `TruthBoundary` is live on orchestration verification ([`truth_boundary.py`](../../ai_command_center/orchestration/verification/truth_boundary.py), [`execution_truth.py`](../../ai_command_center/orchestration/verification/execution_truth.py)). Receipts / Evidence UI exist. Brain Inspector projects state, not CoT. |
| **Architectural conflict** | Section 9 M2 says populate records on execution steps; live path omits ordinary success/failure. Empty `receipt`/`verification` dicts on escalate-only publishes can look like “no evidence” even when receipts exist elsewhere. LLM narrative must not become SoT (already rejected as Proposal A). |
| **Missing decision (Gate 2)** | Must DecisionRecord emit on ordinary success and failure? Required evidence keys? Historical inspectability store vs AppState latest-only? Threshold for “missing evidence represented as missing”? |
| **Dependencies** | Receipts, SecurityTiers, ADR-018/019 observations, TruthBoundary, Stream B (shared publish helper). |
| **Implementation surface** | Domain (done), orchestrator emission, AppState/timeline/receipt join, Evidence / Approvals / Mission Control projection, optional DecisionCard. |
| **Verification surface** | `tests/test_decision_autonomy_domain.py`; need tests: emit on success/failure; records reference real receipts; explanation cannot fabricate facts; missing evidence explicit; historical inspectability. |
| **Estimated effort** | Small–Medium |
| **Trace** | Spec ADR-021 §9–10 → partial code → tests for domain only → runtime evidence only on escalate paths. |

---

## Stream B — ADR-022 Autonomy

| Field | Answer |
|-------|--------|
| **Documented requirement** | Composite AutonomyScore (Policy × Evidence × Verification × Execution). Policy gates remain hard. No logprob-primary autonomy. WRITE_DESTROY always HITL. [`ADR-022_CONFIDENCE_AND_AUTONOMY.md`](../architecture/adr/ADR-022_CONFIDENCE_AND_AUTONOMY.md). |
| **Current implementation** | `AutonomyScore.compute` with default `threshold=0.6` ([`autonomy_score.py`](../../ai_command_center/domain/autonomy_score.py)). SecurityTier / `require_approval` / PermissionService / BrainRuntime 60s deny live. Score published only with DecisionRecord on two escalate paths; component values are **heuristic constants** (e.g. `policy_confidence=0.2` if hard block else `0.9`), not derived from WM/receipts/TruthBoundary. Score does **not** authorize or deny execution — approval still comes from step flags / tiers. |
| **Architectural conflict** | Autonomy must not become a second intake beside ExecutionAuthority (ADR-006). Recent integrity work (canonical intake, receipts, scheduler) makes a parallel “auto-execute because score is high” path invalid. LOW/MEDIUM/HIGH risk bands in the program brief are **not** in the ADR yet. |
| **Missing decision (Gate 2)** | Exact escalation bands and numeric thresholds. Whether aggregate `< threshold` **blocks** execution or only requests approval. Policy override rules. Timeout/denial mapping. Ordinary-path scoring. |
| **Dependencies** | ADR-004, ADR-021 records, ADR-019 stuck/replan, ExecutionAuthority, receipts. |
| **Implementation surface** | Domain (done), orchestrator/BrainRuntime gate, Approvals UI projection, audit trail, **no new execute API**. |
| **Verification surface** | Domain unit tests exist. Need: deterministic thresholds, escalate/deny/timeout, no EA bypass, receipt correctness, audit trail. |
| **Estimated effort** | Medium |
| **Trace** | Spec ADR-022 §9–10 → domain + unused-as-authority score → tests domain-only → runtime not using score as gate. |

---

## Stream C — ADR-023 Model Strategy

| Field | Answer |
|-------|--------|
| **Documented requirement** | Brain independent of vendor models. Quality tiers are **settings**, not architecture. Degrade (more HITL, narrower plans, fail closed) when weak/unavailable. No `critical = gpt-4o`. [`ADR-023_MODEL_STRATEGY.md`](../architecture/adr/ADR-023_MODEL_STRATEGY.md). |
| **Current implementation** | `ModelRouterService` wired; `model_tier_map` in settings schema/migration; Ollama + OpenAI HTTP services; `model.selected` telemetry. Defaults collapse tiers to local (`DEFAULT_MODEL_TIER_MAP` / `llama3.2:3b` historically). Context over-budget downgrade map exists in docs/router. [`MODEL_ORCHESTRATION.md`](../architecture/MODEL_ORCHESTRATION.md) M1 complete; M2 budget influence / M3–M4 local-only + telemetry-never-gates-authority incomplete vs Section 9. |
| **Architectural conflict** | Program wants task → capability → selection → execute → verify → fallback as **infrastructure**. Router today is settings-shaped static map, not capability-requirement matching or health/cost/latency policy. Must not let the model own routing (Inv 13 / ARI). |
| **Missing decision (Gate 2)** | Capability metadata schema; health/cost constraints as settings vs code; sequential M2–M4 acceptance; whether fallback is router-owned or orchestrator-owned. |
| **Dependencies** | Provider adapters, SettingsSnapshot, ContextManager (Inv 6), ADR-019 replan quality optional. |
| **Implementation surface** | Registry, router policy, degrade modes, telemetry reason codes — **no Brain branching on vendor names**. |
| **Verification surface** | `tests/test_model_tier_map.py`, `test_model_router_dispatch.py`, settings tests. Missing: local-only replan/destroy (no cloud required), telemetry never gates authority. |
| **Estimated effort** | Medium |
| **Trace** | Spec ADR-023 §10 → M1 settings live → partial tests → runtime still local-default undifferentiated tiers. |

---

## Stream D — EventBus isolation / tiered dispatch

| Field | Answer |
|-------|--------|
| **Documented requirement** | Historical Phase 5 plan + PERFORMANCE_CONSTITUTION budgets (sync handler &lt;5 ms, queue depth &lt;100). Isolation previously required **measured contention + owner**. Program now commits to the pipeline; **Stage 1 is still measurement**. |
| **Current implementation** | `EventBus(..., async_dispatch=True)` single `event-dispatch` thread ([`application.py`](../../ai_command_center/application.py)). Policy: `DispatchTier` SYNC_CRITICAL vs ASYNC_ELIGIBLE ([`dispatch_policy.py`](../../ai_command_center/core/events/dispatch_policy.py)). Metrics: `dispatch_queue_depth`, `dropped_events`, `get_handler_metrics()`, per-topic publish counts ([`event_bus.py`](../../ai_command_center/core/event_bus.py)). Backpressure: telemetry may drop; SYNC_CRITICAL can invoke inline when full. `tiered_dispatch_policy.py` / `async_dispatch_queue.py` **not on main**. Branch `cursor/phase5-async-eventbus-744e` **ABANDONED**. |
| **Architectural conflict** | Multi-pool FIFO vs single-queue ordering. Isolation tests on the abandoned branch would break current FIFO. Do not merge that branch. UI/critical vs runtime vs background topology is a **hypothesis**, not an accepted ADR. |
| **Missing decision (Gate 2)** | After a Performance Investigation Report: isolate or not; if yes, topology and ordering guarantees; shutdown; priority inversion policy. |
| **Dependencies** | Art. VII/XII, PERFORMANCE_CONSTITUTION, existing R4b queue, UIQueue (no ≤100 ms polling). |
| **Implementation surface** | First: instrumentation + load tests. Then smallest isolation **if justified**. |
| **Verification surface** | `tests/test_eventbus_dispatch_queue.py`, `test_eventbus_shutdown.py`, `test_eventbus_async_adapters.py`, **`tests/test_eventbus_stage1_contention.py`**. Stage 1 report: [`EVENTBUS_STAGE1_CONTENTION_REPORT.md`](EVENTBUS_STAGE1_CONTENTION_REPORT.md) — isolation **not** unlocked. Windows ARM64 GUI soak still required for UI budgets (PERF Art. V). |
| **Estimated effort** | Medium (measurement + maybe isolation) |
| **Trace** | Spec Phase 5 / PERF constitution → R4b live, pools absent → dispatch tests exist → **Stage 1 contention report 2026-08-16: no isolation ADR**. |

---

## Stream E — Knowledge Federation

| Field | Answer |
|-------|--------|
| **Documented requirement** | ADR-020: World Model + MemoryGraph are canonical; summaries/indexes are derived. Historical Phase 8b treated vectors as product; that **unified SoT/vectors program is abandoned**. UCGS `scope_embeddings` S5 forbids embedding/vector DB strings without phase enablement ([`ucgs.profiles/ai-command-center.yaml`](../../ucgs.profiles/ai-command-center.yaml)). |
| **Current implementation** | WM + MemoryGraph + conversation repo live. `FederationService` is **wired** in [`service_factory.py`](../../ai_command_center/core/service_factory.py) as a read-only query view (`federation.query.request` → `federation.query.result`) with provenance pointers. Vectors remain out of scope (UCGS `scope_embeddings` S5). Entity `embedding_vector` BLOB column exists but is not read or written by federation. `FEATURE_VECTOR_SEARCH` remains a flag only. |
| **Architectural conflict** | “Vector DB contains it, therefore ACC knows it” vs ADR-020 SoT. Entity embedding column is a latent dual-SoT risk. Federation type-not-in-factory is Exists ≠ Wired. |
| **Missing decision (Gate 2)** | Knowledge/Memory SoT layering (Authoritative State → Projection → Index → Search → Context Assembly). Whether to live-wire read-only FederationService. Whether vector index is allowed as **derived** retrieval (requires ADR-024+ and UCGS profile change). Freshness/invalidation/provenance. |
| **Dependencies** | ADR-020, ADR-015, Inv 11, ContextManager, UCGS, Stream C (embeddings as capability not authority). |
| **Implementation surface** | SoT ADR first; then federation interface, indexing pipeline, embedding **abstraction**, retrieval, invalidation, provenance — **not** Chromadb/Pinecone as SoT. |
| **Verification surface** | `tests/test_federation.py` including `federation_m1` cases: stale/deleted source, duplicates, provenance, rebuild-from-registry, factory READY, read-only query. |
| **Estimated effort** | Medium–Large |
| **Trace** | Spec ADR-020 + abandoned Phase 8b → WM/Memory live, federation unwired, vectors gated → tests without factory → no SoT-for-index ADR. |

---

## Stream F — Goose pattern adoption

| Field | Answer |
|-------|--------|
| **Documented requirement** | Class B research only. Ask which patterns strengthen **this** architecture. Integration Proposal + ADR before code. Expedition: [`legacy_goose_expedition_report.md`](../../research/repositories/exp-001-goose/notes/legacy_goose_expedition_report.md). |
| **Current implementation** | ACC already has domain packages, EventBus, provider HTTP adapters, `arch_lint.py`, ARI/`runtime/` providers. No Goose runtime, no Electron console, no Goose session SoT. |
| **Architectural conflict** | Goose `AgentManager` globals / session storage vs ACC no-global-state and ExecutionAuthority. Copying Goose agent loop would violate Workspace OS + Inv 13. |
| **Missing decision (Gate 2)** | Adopt / Adapt / Reject table signed by owner. Candidate Adapt (from expedition, not yet decided): package export discipline; provider-types split; cancellation tokens per run; bounded caches. Candidate Reject: Goose as SoT, embedded third-party console, global config, logprob/CoT autonomy. |
| **Dependencies** | Streams A–C runtime contracts should be stable first (dependency graph). ARI, Inv 13. |
| **Implementation surface** | Selective pattern ports only; **Goose Pattern Adoption Record**. |
| **Verification surface** | Arch-lint / tests per adopted pattern. No “Goose compatibility” suite. |
| **Estimated effort** | Small |
| **Trace** | Spec IMPLEMENTATION_GUIDE Queue 2 → research notes → **no ACC code from Goose** → no ADR. |

---

## Stream G — Cross-OS (final strategic gate — not in Waves 0–5)

| Field | Answer |
|-------|--------|
| **Documented requirement** | Historical Phase 9/11 platform plan. Program: ACC runs correctly across supported OS **without platform-specific contamination of core**. Adapters: Windows / macOS / Linux. |
| **Current implementation** | GUI `main.py` **Windows ARM64 only** (`is_arm64()`). Headless core runs on Linux CI with `APPDATA`. `platform_service.py` branches on `sys.platform`. `runtime_paths.py` win/darwin/linux. Hotkey: Windows/Linux keyboard backend; macOS getter returns **unsupported placeholder** ([`hotkey_provider.py`](../../ai_command_center/platform/hotkey_provider.py)). `platform/macos/hotkey_provider.py` `_start_tap()` is a **log stub**. Packaging: Windows-oriented; macOS/Linux deferred. |
| **Architectural conflict** | `if sys.platform` in core/platform service vs adapter pattern. ARM64 GUI gate vs Linux headless. `APPDATA` required even on Linux. |
| **Missing decision (Gate 2)** | **Deferred until Waves 0–5 close.** Supported SKU set; which features are adapter-optional (hotkey/tray); CI matrix; packaging. |
| **Dependencies** | Stable runtime (A–F). Platform interface design. |
| **Implementation surface** | Platform Interface + adapters; paths; process launch; hotkey/tray **as adapters**; notifications; capability discovery; packaging; platform CI. |
| **Verification surface** | Platform CI + packaging; core tests remain OS-agnostic. |
| **Estimated effort** | Separate major program (outside 97–167 h envelope) |
| **Trace** | Spec Phase 9 plan → Windows SKU live, others stub → tests skip/GUI → **gate remains closed**. |

---

## Stream X — macOS Hotkey (dropped)

| Field | Answer |
|-------|--------|
| **Disposition** | **Dropped** as a standalone strategic item. Not Queue 1. Not Stream G’s definition of done. |
| **Current implementation** | Placeholder + log-stub tap remain on disk as fossils. |
| **Rule** | Do not implement a fake CGEvent tap to “complete” a dropped milestone. If Cross-OS later needs hotkeys, they are an **adapter feature** under Stream G. |

---

## Cross-stream conflicts (must not be papered over)

| Conflict | Streams | Resolution rule |
|----------|---------|-----------------|
| Dual execution path | B vs ADR-006 | Autonomy never bypasses ExecutionAuthority |
| Explainability fiction | A vs TruthBoundary | Records cite receipts/WM; LLM text is non-authoritative |
| Model owns control flow | C vs Inv 13 | Router/settings choose; Brain contracts unchanged |
| Index as SoT | E vs ADR-020 | Vector/federation index is derived |
| Isolation vs FIFO | D vs R4b | Measurement + new ADR; do not merge abandoned branch |
| Goose as platform | F vs Inv 13 | Patterns only |
| Platform `if` in core | G | Adapters last |

---

## Program trace summary

| Stream | Spec | ADR | Code | Tests | Runtime evidence | Next gate |
|--------|------|-----|------|-------|------------------|-----------|
| A | ADR-021 §10–12 | Accepted | Gate 4 ordinary-path records | `-k decision_record` | Headless emit + projection | Gate 5 verification (GUI on Win ARM64) |
| B | ADR-022 §10–12 | Accepted | Gate 4 bands escalate-only | `-k autonomy_escalation` | Headless HITL not deny | Gate 5 |
| C | ADR-023 §10–12 | Accepted | M1–M4 on main | `-k model_degradation` / mix | Local-only replan/destroy | Gate 5 |
| D | PERF + IP-D | **No isolation ADR** | R4b single queue | Dispatch + Stage 1 harness | [`EVENTBUS_STAGE1_CONTENTION_REPORT.md`](EVENTBUS_STAGE1_CONTENTION_REPORT.md) — isolation not unlocked | Stage 2 blocked; GUI soak separate |
| E | ADR-024 | DEFER vectors | M1 FederationService wired | `-k federation_m1` | Factory READY, provenance | Gate 5 for M1; vectors still deferred |
| F | ADR-025 | Accepted Adopt/Adapt/Reject | None from Goose | N/A | N/A | Wave 4 Adapt Gate 3 |
| G | Phase 9 hist. | **Closed until Wave 6** | Windows SKU | Partial | Linux headless only | Remain gated |
| X | — | — | Stub fossils | Placeholder tests | Unsupported | **Dropped** |
