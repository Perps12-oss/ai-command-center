# ADR-025: Goose Pattern Adoption (Stream F — Gate 2)

**Status:** Accepted — Adopt/Adapt/Reject table below (no Goose code, no Goose SoT, no Goose UI)
**Date:** 2026-08-14
**Deciders:** Owner (Gate 2), per `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md`
**Related:** Inv 13 (ARI — externals are capabilities), Rule 2 (no globals), Rule 3 (EventBus), `arch_lint.py`
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md` (Gate 2 decision on a Class B research proposal)
**Proposal:** [`IP_F_GOOSE_PATTERN_ADOPTION.md`](../proposals/IP_F_GOOSE_PATTERN_ADOPTION.md)
**Research:** [`legacy_goose_expedition_report.md`](../../../research/repositories/exp-001-goose/notes/legacy_goose_expedition_report.md)
**Close-out record:** [`GOOSE_PATTERN_ADOPTION_RECORD.md`](../proposals/GOOSE_PATTERN_ADOPTION_RECORD.md)
**Gate 3 (Section 9 plan):** §9 — Wave 4 Adapt rows F1–F4 (docs only; Gate 4 code not authorized until this section is on `main`)

---

## 1. Problem

Does anything in the Goose expedition strengthen ACC's own architecture, without ACC becoming Goose-compatible, adopting Goose as a runtime, or copying patterns that conflict with ExecutionAuthority / no-globals / EventBus rules?

## 2. Decision

**ACCEPT** the Adopt/Adapt/Reject table from IP-F, with its one open row resolved (MCP bundled as SoT — IP-F listed this preliminarily as "Adapt/Reject per ADR"; this ADR is that ADR, and resolves it to **Reject**). Every other row matches IP-F's preliminary categorization; wording below is tightened for clarity but not changed in substance.

| Goose pattern | ACC equivalent | Decision | Notes |
|---|---|---|---|
| Provider-types crate split | `runtime/` + domain contracts | **Adapt** | Structural discipline only; no Goose provider code copied |
| Package/crate boundary discipline | `arch_lint.py` | **Adapt** | ACC already has the enforcement mechanism; adopt the discipline it encodes, not new tooling |
| Per-session cancellation / creation locks | run_id cancellation on orchestrator | **Adapt** (if missing) | Verify current orchestrator coverage before implementing; do not duplicate if already present |
| Bounded LRU actor cache | AppState / service caches | **Adapt**, bounds mandatory | Any cache adopted from this pattern must have an explicit bound; unbounded caches are not in scope |
| Electron desktop / Goose Serve | ACC Tk UI + host OS | **Reject** | No third-party embedded console; ACC UI stays what it is |
| Global config / OnceCell managers | Forbidden globals | **Reject** | Directly conflicts with Rule 2 (no globals) |
| Agent loop as product identity | ExecutionAuthority pipeline | **Reject** | ACC's identity is ExecutionAuthority/receipts/TruthBoundary, not an agent-loop UX |
| MCP bundled as SoT | ExternalCapabilityBridge as capability | **Reject** | MCP (or any external bridge) is a capability under ARI, never a source of truth |

## 3. Scope of "Adapt"

"Adapt" authorizes **pattern adoption**, not code import. Each Adapt row above requires its own Gate 3 Section 9 plan naming the specific ACC file(s) touched, before any implementation — this ADR does not pre-authorize code. Implementation happens in Wave 4 (per `STRATEGIC_RUNTIME_PROGRAM.md`), after Streams A–C runtime contracts are stable, consistent with IP-F's stated dependency preference.

## 4. Remains authoritative / unchanged

Workspace State, canonical runtime, ExecutionAuthority, TruthBoundary, receipts, governance, privacy, and `PERFORMANCE_CONSTITUTION.md` are all unaffected. Goose remains an external reference repository — never a runtime dependency, never a SoT.

## 5. Invalid if

- Any `provider_sdk` live-wire shadows AppState.
- A third-party console (Electron or otherwise) is embedded.
- ACC persistence is replaced by, or modeled directly on, Goose session storage.
- A Reject-row pattern (global config, agent-loop-as-identity, MCP-as-SoT, Electron UI) appears in a PR under any name.

## 6. Tests

Per adopted (Adapt) pattern: arch-lint import-boundary rules, cancellation-token tests, cache-bound tests, as applicable to that specific pattern. No "Goose compatibility" suite — compatibility with Goose is explicitly not a goal.

## 7. Next step

`GOOSE_PATTERN_ADOPTION_RECORD.md` reflects this table as the Accepted decision. Gate 3 Section 9 plans for all four Adapt rows are in **§9** (F1–F4). Gate 4 product code is authorized only against §9 after this file is on `main`. Reject rows remain closed.

---

## 8. Wave 4 sequence (binding for Gate 4)

Adapt rows are implemented **sequentially** within Wave 4:

```text
F1 (arch_lint package discipline)
  → F2 (runtime / domain provider-contract discipline)
  → F3 (cancel / creation-lock verify-or-fill)
  → F4 (bounded LRU caches)
```

Do not start F2 until F1 acceptance is met (or F1 is proven already satisfied with tests). Do not start F4 until F3 is closed (covered or filled). Parallel Gate 4 PRs that touch the same surfaces are forbidden.

---

## 9. Gate 3 — Section 9 Implementation Plan (F1–F4)

Program Gate 3 (“Section 9 plan”). This does **not** reopen the §2 Adopt/Adapt/Reject decision. Depth follows the required Gate 3 fields (files, interfaces, migrations, tests, wiring, docs, acceptance, rollback). Each Adapt row has its own subsection — satisfying §3 “own Gate 3 plan” per row.

**Binding rules for all F\*:**

- Pattern adoption only — **no Goose code import**, no Goose dependency, no Goose compatibility suite.
- Inv 13 / ARI: externals remain capabilities; ACC remains SoT.
- Rule 2: no globals / OnceCell-style managers.
- Rule 3: EventBus only; no new service→service call edges.
- Invalid if any Reject-row pattern appears under another name (§5).

### F1 — Package / crate boundary discipline (`arch_lint.py`)

| Field | Plan |
|-------|------|
| **Work** | Formalize package-ownership rules already implied by ACC layout: extend `scripts/arch_lint.py` so illegal cross-package imports fail the ratchet (e.g. `runtime/` must not import `ui/` or peer `services/` modules; `domain/` must not import services/UI). Prefer new **rules** on the existing linter — no new tooling process, no Goose crate layout. |
| **Files** | `scripts/arch_lint.py`; `tests/arch_lint_baseline.json` (ratchet only for pre-existing violations); arch-lint unit tests under `tests/` (extend existing arch_lint fixtures if present, else add `tests/test_arch_lint_package_boundaries.py`). |
| **Interfaces** | None (static analysis). No new EventBus topics. |
| **Migrations** | None. Baseline may grow only for grandfathered violations discovered by new rules — new violations must not be baselined without owner note in the Gate 4 PR. |
| **Wiring** | CI / pre-commit already invoke `arch_lint.py --baseline tests/arch_lint_baseline.json`. No service wiring. |
| **Tests** | Synthetic fixtures: illegal `runtime`→`ui` and `domain`→`services` imports fail; legal composition-root and infra imports pass; baseline ratchet still green on clean tree. |
| **Docs** | This subsection; Adoption Record F1 Implementation → “§9 F1”. Optional one-line note in `docs/ARCHITECTURE_ENFORCEMENT.md` if a new rule id is introduced. |
| **Acceptance** | `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json` exits 0; new boundary rule(s) covered by unit tests; no new lint binary. |
| **Rollback** | Revert rule additions and baseline delta; leave prior R1–R5 behavior. |
| **Invalid if** | A second architecture linter is introduced; Goose packaging tools are vendored; Reject-row globals are “allowed” via lint exceptions. |

### F2 — Provider-types crate split (`runtime/` + domain contracts)

| Field | Plan |
|-------|------|
| **Work** | Encode structural ownership of agent-runtime providers: contracts live under `ai_command_center/runtime/` + domain dataclasses; HTTP/vendor adapters remain capabilities. Document and enforce (via F1 rules / allowlists) that UI and peer services do not import concrete provider modules except through the composition root / AppState projection path already used. **Do not** copy Goose provider code. **Do not** live-wire dormant `provider_sdk/`. |
| **Files** | `ai_command_center/runtime/__init__.py`; `runtime/provider_registry.py`; `runtime/agent_runtime_provider.py`; `runtime/providers/*.py`; domain contracts already used by providers (e.g. capability / session snapshots under `domain/`); `scripts/arch_lint.py` allowlists if needed; `docs/architecture/AGENT_RUNTIME_INTERFACE.md` (clarify ownership only — no ARI rewrite). |
| **Interfaces** | Existing provider registry / AppState provider snapshot paths. No new execute API. No new topics for F2. |
| **Migrations** | None. Do not migrate Goose session schemas. |
| **Wiring** | Composition root (`application.py` / `service_factory.py`) remains the only place that constructs providers for the live graph. EventBus for runtime signals stays as today. |
| **Tests** | Import-boundary tests from F1 covering `runtime/`; registry unit tests remain green; assert `provider_sdk` is **not** imported from `application.py` / `service_factory.py`. |
| **Docs** | This subsection; short ARI ownership note if missing; Adoption Record F2. |
| **Acceptance** | Live path uses `runtime/` providers only; arch_lint green; no Goose provider module on `sys.path` as a dependency; `provider_sdk` stays unwired. |
| **Rollback** | Revert lint/docs deltas; leave existing `runtime/` providers. |
| **Invalid if** | `provider_sdk` is registered in the factory; third-party console embedded; ACC persistence modeled on Goose sessions. |

### F3 — Per-session cancellation / creation locks (verify then fill)

| Field | Plan |
|-------|------|
| **Work** | **Step A — Verify:** inventory cancel coverage for chat/LLM (`UI_CHAT_CANCEL` → `CHAT_CANCELLED` / `LLM_CANCEL` in Ollama/OpenAI services), agent (`AGENT_CANCEL_REQUEST`), goal (`GOAL_CANCEL_REQUEST` / `GOAL_CANCELLED`), and orchestration **run_id** lifecycle in `ExecutionOrchestratorService` (`_runs` map). Document gaps in the Gate 4 PR description (or a short audit note under `docs/audits/` if coverage is incomplete). **Step B — Fill only gaps:** if orchestrator lacks run cancel / creation lock (prevent double-start of the same `run_id`), add EventBus-driven cancel handling and an in-service lock map keyed by `run_id` — **not** process globals / OnceCell. If coverage is already complete, Gate 4 for F3 is **tests + audit note only** (no duplicate machinery). |
| **Files** | Verify: `services/execution_orchestrator_service.py`; `services/ollama_service.py`; `services/openai_http_service.py`; `services/tool_executor_service.py` (cancel path); `ui/controller.py` cancel publishers; `core/events/topics.py`. Fill (only if needed): orchestrator cancel handler + tests under `tests/` (e.g. `tests/test_orchestrator_run_cancel.py`). |
| **Interfaces** | Prefer **existing** cancel topics. New topic only if a documented gap cannot use `LLM_CANCEL` / agent / goal cancel — must be justified in the Gate 4 PR and listed in `topics.py`. No service→service cancel calls. |
| **Migrations** | None. |
| **Wiring** | Orchestrator (or owning service) subscribes on EventBus; UI continues to publish cancel intents only. |
| **Tests** | Cancel mid-run stops further `tool.invoke` for that `run_id`; double-create same `run_id` is refused or coalesced; chat cancel still cancels LLM stream; no unbounded global registry. If “already covered,” tests prove each surface without new production code. |
| **Docs** | This subsection; Adoption Record F3 (Implementation = “covered by tests” or “orchestrator cancel filled”); optional `docs/audits/` gap note. |
| **Acceptance** | Written verify result on `main`; either gap filled with green tests or explicit “no code — coverage proven” with tests. |
| **Rollback** | Revert orchestrator cancel additions; leave pre-existing chat/agent/goal cancel. |
| **Invalid if** | OnceCell / module-level global cancel maps; Goose `CancellationToken` types imported; cancel bypasses EventBus. |

### F4 — Bounded LRU actor cache (AppState / service caches)

| Field | Plan |
|-------|------|
| **Work** | Apply the Goose “bounded LRU actor cache” **discipline** to ACC caches that hold per-run / per-actor working sets. Reference pattern already present: `orchestration/orchestration_registry.py` (`OrderedDict` + `_MAX_TRACKED_REQUESTS = 512`). Gate 4 must: (1) audit `ExecutionOrchestratorService._runs` and similar in-memory maps; (2) give every adopted cache an **explicit max size** and LRU/FIFO eviction; (3) leave unrelated bounded deques (UI sparklines, perf samples) alone unless they are unbounded today. Unbounded caches are **out of scope to keep** — they must gain a bound or be removed. |
| **Files** | Likely: `services/execution_orchestrator_service.py` (`_runs`); `orchestration/orchestration_registry.py` (model / keep bound); any other service map identified in the F4 audit. Tests: `tests/test_bounded_run_cache.py` (or extend orchestrator tests). |
| **Interfaces** | No new public API required. Eviction is internal. Optional telemetry count of evictions via existing telemetry path — must not gate authority. |
| **Migrations** | None. |
| **Wiring** | Cache lives inside the owning service / module; AppState remains projection-only (do not invent a second SoT cache in UI). |
| **Tests** | Insert past bound → oldest evicted; lookup after eviction misses; bound constant is named and > 0; concurrent cancel (F3) does not leak entries forever. |
| **Docs** | This subsection; Adoption Record F4. |
| **Acceptance** | Every Wave-4-touched actor/run cache has an explicit bound; tests prove eviction; `arch_lint` / constitution / UCGS still pass. |
| **Rollback** | Revert bound/eviction; do not leave a larger unbounded structure. |
| **Invalid if** | Unbounded “temporary” dict ships; cache becomes a SoT replacing receipts/WM; Goose session store is used as the cache backend. |

### Gate 4 exit criteria (Wave 4 Adapt complete)

Gate 4 for Stream F Adapt is **done** only when **all** of the following hold on `main`:

1. F1–F4 **Acceptance** rows are met (F3 may be “covered by tests” with no production diff).
2. No Goose package dependency; no Goose compatibility suite; no Reject-row pattern (§5).
3. `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json`, `python3 scripts/verify_constitution.py`, and `ucgs_runner` + `ucgs_ci_gate` pass; tests for touched surfaces are green.
4. [`GOOSE_PATTERN_ADOPTION_RECORD.md`](../proposals/GOOSE_PATTERN_ADOPTION_RECORD.md) Implementation and Verification columns are filled per Adapt row.
5. Inv 13 / Rule 2 / Rule 3 hold; `provider_sdk` is not live-wired.

**After Gate 4:** Gate 5 = Linux + Windows verification evidence; Gate 6 = Wave 4 close-out docs on `main` (unblocks opening Wave 6 / Stream G planning — does not auto-start Cross-OS code).

**Out of scope for §9 / Wave 4 Adapt:** Electron / Goose Serve; global config; agent-loop product identity; MCP-as-SoT; Stream D isolation; Stream E embeddings; copying Goose into `ai_command_center/`.

**Dependencies:** Streams A–C Gate 4 contracts are on `main` (Wave 5 closed). F1 before F2; F3 before F4.

---

## References

- `docs/architecture/proposals/IP_F_GOOSE_PATTERN_ADOPTION.md`
- `docs/architecture/proposals/GOOSE_PATTERN_ADOPTION_RECORD.md`
- `research/repositories/exp-001-goose/notes/legacy_goose_expedition_report.md`
- `scripts/arch_lint.py`
- `ai_command_center/runtime/`
- `ai_command_center/orchestration/orchestration_registry.py`
- `ai_command_center/services/execution_orchestrator_service.py`
- `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md`
- `docs/audits/PREFLIGHT_GATE3_ADR025_SECTION9.md`
