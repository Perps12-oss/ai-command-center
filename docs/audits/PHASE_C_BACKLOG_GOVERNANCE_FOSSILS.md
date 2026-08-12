# Phase C Backlog — Governance-Layer Architectural Fossils

**Status:** BACKLOG — record only. **Do not fix opportunistically.**
**Origin:** Phase B was blocked by a UCGS rule requiring a contract retired ~3 weeks earlier
(`docs/audits/UCGS_PROFILE_CORRECTION_COMMAND_ROUTED.md`).

**Owner direction:** *"We've now found evidence that the governance layer itself contains
architectural fossils, and we should systematically identify those rather than fixing them
opportunistically."*

---

## Why this needs a systematic pass, not point fixes

The `COMMAND_ROUTED_VERSION` fossil had three properties that make this class of defect
dangerous:

1. **Dormant.** It only evaluated when a `contract_lock` file changed, so it lay hidden for
   ~3 weeks and ~40 commits.
2. **Blocking when it woke.** `S4 / CRITICAL / block_merge` — it stopped legitimate work
   outright, and the obvious workarounds (bypass, relocate, invent the field) were all
   governance violations.
3. **Self-contradicting.** Two governance sources disagreed about the contract surface —
   `verify_contracts.py` (correct) vs the UCGS profile (stale) — an Inv 11 breach *inside the
   enforcement layer*.

A rule that encodes a retired architecture does not fail safe. It fails **loud and wrong**,
and pressures the next engineer toward a circumvention. Finding these by tripping over them
one at a time is the worst available strategy.

---

## Known fossils (confirmed, unfixed)

### F-1 — `pipeline.canonical` describes pre-ADR-006 architecture

`ucgs.profiles/ai-command-center.yaml:106-107`

```yaml
- "UI → CommandRouter → ContextManager → OllamaService → Response"
- "UI → CommandRouter → ObsidianService → NoteRepository"
```

**Reality:** `CommandRouterService` is a *"Pure command classifier library… does not publish
decision events. Decision-making for typed UI_COMMAND is owned by ExecutionAuthorityService"*
(its own docstring). The live path is
`UI → ExecutionAuthority → SingleGoalScheduler → Planner → ExecutionOrchestrator → tools →
receipt/truth`.

**Severity:** currently descriptive only — no rule keys off it. Risk is that a future rule
does, or that a reader treats it as authority.

### F-2 — `eventbus_bypass.remediation` instructs restoring a retired flow

`ucgs.profiles/ai-command-center.yaml:87` — *"Restore canonical UI → CommandRouter → Service
flow."*

**Severity:** actively misleading. This rule is `S4 / CRITICAL`, so an engineer who trips it
is told to restore an ADR-006-retired architecture. Worse than F-1: it is remediation advice
attached to a live blocking rule.

---

## Suggested scope for the Phase C pass

1. **Enumerate.** Every governance artifact that names a component, topic, or flow:
   `ucgs.profiles/*.yaml`, `.cursor/rules/*.mdc`, `scripts/verify_*.py`,
   `tests/arch_lint_baseline.json`, `docs/governance/*`.
2. **Cross-check each named symbol against repository truth** — does the component still
   exist, and does it still play that role? The `COMMAND_ROUTED_VERSION` case shows presence
   in *docs* is not evidence; only code is.
3. **Classify:** live / retired-but-referenced / never-existed.
4. **Prioritise by wake-up blast radius** — a dormant `S4` in a `contract_lock`-style rule
   outranks a stale doc sentence, because it will block work and invite circumvention.
5. **Add a meta-gate if cheap:** assert every symbol named in `contract_lock.required_fields`
   actually exists in at least one locked file. That single check would have caught this
   fossil at the moment it was created rather than 3 weeks later.

---

## Explicitly out of scope for Phase B

Neither F-1 nor F-2 was touched. Phase B's governance correction removed exactly one line —
the `required_fields` entry that blocked it — and nothing else.
