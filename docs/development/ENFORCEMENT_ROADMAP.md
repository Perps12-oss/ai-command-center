# Enforcement Roadmap

**Authority chain:** PROJECT_CONSTITUTION_V4.md → ARCHITECTURE_ENFORCEMENT.md → UCGS v5  
**Audit refs:** `scripts/verify_constitution.py`, `tools/ucgs_runner.py`, `.github/workflows/ucgs.yml`

---

## Objective

Progress from advisory governance (warn-only) to merge-blocking constitutional enforcement without blocking legitimate transformation velocity.

---

## Current Baseline (Stage 0)

| Mechanism | Behavior | Evidence |
|-----------|----------|----------|
| `verify_constitution.py` | File presence + duplicate doc heuristic | CI step in `ucgs.yml:27-28` |
| `ucgs_runner.py` | Layer/import analysis | `ucgs.config.yaml` profile `default` |
| `ucgs_ci_gate.py` | Verdict evaluation | `UCGS_ENFORCEMENT: warn` in CI |
| Git pre-commit | Warn via `tools/install_git_hooks.py` | Phase 1 |
| Cursor hooks | User-level UCGS on commit | `~/.cursor/hooks.json` |

**Gap:** No import-graph enforcement in constitution script; UCGS profile not `ai-command-center`.

---

## Stage 1 — Local Warn (CURRENT)

**Setting:** `enforcement_mode: warn` in `ucgs.config.yaml`

| Check | Action on FAIL |
|-------|----------------|
| UCGS S4/S5 | Print verdict; commit proceeds |
| Constitution missing files | CI fails (already) |
| Large commit S2 | Warn only |

**Exit criteria:** All contributors run `python tools/ucgs_runner.py` before architecture-sensitive PRs.

---

## Stage 2 — PR Enforcement (Target: Q3 2026)

**Changes:**

1. Switch `ucgs.config.yaml` → `profile: ai-command-center`
2. Add PR comment bot posting UCGS summary artifact
3. Expand `verify_constitution.py`:
   - Fail on UI importing `repositories/` or `db/`
   - Fail on `shell=True` outside allowlisted files
4. `enforcement_mode: warn` remains — FAIL visible but non-blocking

**Acceptance:**

- [ ] 4 consecutive PRs with UCGS artifact attached
- [ ] Zero undetected UI→repo imports in new code

---

## Stage 3 — CI Block (Active: Track 2 Stage 3)

**Changes:**

1. `.github/workflows/ucgs.yml` → `UCGS_ENFORCEMENT: block` ✓
2. Local optional: `enforcement_mode: block` in `ucgs.config.yaml` (still `warn` — CI-only block)
3. Pre-commit blocks on S4/S5 FAIL when local `enforcement_mode: block` is set

**Acceptance:**

- [ ] Main branch protected; red CI blocks merge (repo setting)
- [x] Documented escape hatch: `UCGS_ENFORCEMENT=warn` on draft PRs only (see `ucgs.yml` comment)
- [x] Legacy grandfather list: `tests/arch_lint_baseline.json`

---

## Stage 4 — Constitutional Gate (Target: 2027)

**Changes:**

1. `verify_constitution.py` becomes merge gate superset:
   - Required topics in `topics.py` match ARCHITECTURE.md table
   - Service factory registers all services referenced in ARCHITECTURE.md flows
   - AppState reducers exist for all UI-facing snapshots
2. Amendment process required for invariant changes (`governance/amendment_template.md`)
3. Phase documents archived; transformation tracks replace phase gates

**Acceptance:**

- [ ] No architecture-sensitive merge without constitution PASS
- [ ] UCGS + constitution combined workflow < 5 min CI

---

## Tooling Matrix

| Tool | Stage 1 | Stage 2 | Stage 3 | Stage 4 |
|------|---------|---------|---------|---------|
| verify_constitution.py | presence | import grep | import grep | full contract |
| ucgs_runner.py | warn | warn + PR artifact | block | block |
| ruff | advisory | CI check | CI required | CI required |
| pytest | manual | CI required | CI required | CI required |
| git hooks | warn | warn | block local | block local |

---

## Risks

| Risk | Mitigation |
|------|------------|
| False positive flood | Tune profile rules; start warn-only per stage |
| Contributor friction | STABILIZATION_LOG + clear remediation messages |
| Legacy violations | Grandfather list in UCGS config; burn down per track |

---

## Rollback per Stage

Each stage is independently reversible by reverting `ucgs.config.yaml`, workflow env, and hook installer — no schema migrations involved.
