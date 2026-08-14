# ADR-025: Goose Pattern Adoption (Stream F — Gate 2)

**Status:** Accepted — Adopt/Adapt/Reject table below (no Goose code, no Goose SoT, no Goose UI)
**Date:** 2026-08-14
**Deciders:** Owner (Gate 2), per `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md`
**Related:** Inv 13 (ARI — externals are capabilities), Rule 2 (no globals), Rule 3 (EventBus), `arch_lint.py`
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md` (Gate 2 decision on a Class B research proposal)
**Proposal:** [`IP_F_GOOSE_PATTERN_ADOPTION.md`](../proposals/IP_F_GOOSE_PATTERN_ADOPTION.md)
**Research:** [`legacy_goose_expedition_report.md`](../../../research/repositories/exp-001-goose/notes/legacy_goose_expedition_report.md)
**Close-out record:** [`GOOSE_PATTERN_ADOPTION_RECORD.md`](../proposals/GOOSE_PATTERN_ADOPTION_RECORD.md)

---

## 1. Problem

Does anything in the Goose expedition strengthen ACC's own architecture, without ACC becoming Goose-compatible, adopting Goose as a runtime, or copying patterns that conflict with ExecutionAuthority / no-globals / EventBus rules?

## 2. Decision

**ACCEPT** the Adopt/Adapt/Reject table as drafted in IP-F, unedited:

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

`GOOSE_PATTERN_ADOPTION_RECORD.md` is updated (this same change) to reflect this table as the Accepted decision. Each Adapt row gets its own Gate 3 Section 9 plan when its Wave (4) is reached — none are implemented as part of this Gate 2 closure.

---

## References

- `docs/architecture/proposals/IP_F_GOOSE_PATTERN_ADOPTION.md`
- `docs/architecture/proposals/GOOSE_PATTERN_ADOPTION_RECORD.md`
- `research/repositories/exp-001-goose/notes/legacy_goose_expedition_report.md`
- `scripts/arch_lint.py`
- `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md`
