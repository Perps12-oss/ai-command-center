# Governance Correction — Stale UCGS Contract Requirement `COMMAND_ROUTED_VERSION`

**Type:** Governance-artifact correction. **No runtime code changed.**
**Scope:** one line removed from `ucgs.profiles/ai-command-center.yaml` `contract_lock.required_fields`.
**Approved by:** repository owner, in-session, with explicit instruction not to bypass UCGS,
relocate contracts, or invent the field.

---

## Correction to the record

The blocking report initially described `COMMAND_ROUTED_VERSION` as having **never existed**
in the repository. **That was wrong**, and the corrected finding is stronger.

`COMMAND_ROUTED_VERSION = "1.0"` was a **real, live contract** that was **deliberately
retired**.

---

## Evidence

Retired in `8002c72` — *"Cursor/state authority migration 6a56 (#80)"*, 2026-07-20, which
**is** an ancestor of `59262fe` (`git merge-base --is-ancestor` → YES).

That commit removed it coherently across the whole surface:

| File | Removed |
|------|---------|
| `ai_command_center/core/contracts.py` | `COMMAND_ROUTED_VERSION = "1.0"` and the `"command_routed": (COMMAND_ROUTED_VERSION,)` entry in `SUPPORTED_VERSIONS` |
| `scripts/verify_contracts.py` | the import, the `contract_version` assertion, and the reporting line |
| `ai_command_center/services/command_router_service.py` | usage |
| `ai_command_center/core/context_manager.py` | usage |
| `tests/test_multi_agent.py`, `tests/test_supervised_agent_demo.py` | usage |

Current state at `59262fe` / `3709325`:

- `contracts.py` — 0 occurrences
- `verify_contracts.py` — 0 occurrences
- `command.routed` topic — **does not exist** (`core/events/topics.py`)
- `CommandRouterService` docstring: *"Pure command classifier library… does not publish
  decision events. Decision-making for typed UI_COMMAND is owned by
  ExecutionAuthorityService."*
- Only remaining reference repo-wide: `ucgs.profiles/ai-command-center.yaml:95`
  (plus historical design docs and untracked IDE/mypy caches, which are not authorities)

**Conclusion:** the retirement was complete; the UCGS profile was simply not updated in that
commit. The requirement outlived its contract by ~3 weeks and blocked **every** subsequent
change to `contracts.py` — it only surfaces when a `contract_lock` file is touched, which is
why it lay dormant until Phase B.

---

## Why this is a repair, not a weakening

1. **No currently valid contract loses enforcement.** `CONTEXT_BUNDLE_VERSION`,
   `OLLAMA_SERVICE_API_VERSION` and `SUPPORTED_VERSIONS` remain required. Only the field
   naming a retired contract is removed.
2. **The authoritative contract gate is unchanged.** `scripts/verify_contracts.py` — which
   the repository treats as the contract gate — already reflects the post-migration surface
   (`execution.authority.decision: runtime intake`) and passes.
3. **`contract_lock.files` is untouched.** `contracts.py` and `context_manager.py` remain
   locked, and `contract_unversioned_change` still fires on unversioned edits.
4. **Nothing was invented.** No placeholder constant was added to satisfy the rule.
5. **No contract was relocated to evade the gate.** The Phase B contracts stay in
   `contracts.py`, their correct home (Inv 11).
6. **Inv 11 restored.** Two governance sources disagreed about the contract surface; they now
   agree.

Article VI (Gate Preservation) is not engaged: a gate protecting a **retired** contract is
not a passed gate being removed. The enforcement semantics for every live contract are
byte-identical.

---

## Verification

| Check | Before | After |
|-------|--------|-------|
| `verify_contracts.py` | PASS (exit 0) | PASS (exit 0) |
| `verify_constitution.py` | PASS | PASS |
| `arch_lint.py --baseline` | OK (4 baselined) | OK (4 baselined) |
| UCGS on a `contracts.py` change | **FAIL S4 `block_merge`** | PASS |
| `contract_unversioned_change` still fires | yes | yes (unchanged) |

---

## Deliberately NOT corrected here

`pipeline.canonical` in the same profile still describes the **pre-ADR-006** architecture:

```yaml
- "UI → CommandRouter → ContextManager → OllamaService → Response"
- "UI → CommandRouter → ObsidianService → NoteRepository"
```

…and `eventbus_bypass.remediation` still says *"Restore canonical UI → CommandRouter →
Service flow."* Both are architectural fossils: `CommandRouterService` is a classifier
library and the live intake is `ExecutionAuthorityService`.

**Left untouched by owner instruction.** Recorded as a Phase C item —
`docs/audits/PHASE_C_BACKLOG_GOVERNANCE_FOSSILS.md`. The owner's direction is to identify
governance-layer fossils **systematically** rather than fix them opportunistically.
