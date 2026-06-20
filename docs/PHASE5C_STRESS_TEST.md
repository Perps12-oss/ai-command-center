# Phase 5C — Daily Driver Stress Test Protocol

**Objective:** Answer one question only:

> Can I use this as my primary AI control layer without frustration or avoidance?

Not: architecture quality, completeness, or elegance.  
Only: **natural use under stress.**

---

## Test environment rules

Before starting:

| Rule | Requirement |
|------|-------------|
| Freeze changes | **No** UI mods, features, or refactors unless blocking |
| Logging mindset | Observe behavior — do not improve mid-test |
| Preflight | All automated gates PASS (see below) |
| Record git SHA | Note commit under test in scorecard |

---

## Preflight (automated)

```powershell
$py = "C:\Users\S8633\AppData\Local\Python\bin\python.exe"
& $py scripts/verify_phase5c_preflight.py
```

Runs contracts, phase gates 1–5B, note audit, and `run_daily_driver.py`.  
Manual layers start only after preflight PASS.

---

## Test structure (4 layers)

### Layer 1 — Core loop (command usage)

**Goal:** Validate Alt+Space → command → result.

| # | Action | Command / step |
|---|--------|----------------|
| 1 | Open palette | Alt+Space |
| 2 | Ten varied prompts | e.g. summarize, explain, list, compare |
| 3 | Shell | `> echo phase5c` |
| 4 | Note search | `note: {keyword}` |
| 5 | New note | `new note: Phase 5C probe \| body text` |
| 6 | Clipboard | Copy text → `Summarize this clipboard` |

**Measure**

| Metric | Meaning |
|--------|---------|
| Time to first response | Latency perception |
| Keystrokes per task | Friction cost |
| Hesitation moments | UX confusion (count + note) |
| Retry rate | Command routing failure |

**Red flags:** hesitate before opening; reach for Explorer/mouse; commands feel uncertain.

---

### Layer 2 — Context stress (real-world chaos)

**Goal:** ContextManager under messy input.

| # | Scenario |
|---|----------|
| 1 | Copy random text → ask question |
| 2 | Switch apps → re-open palette |
| 3 | Long session (20+ interactions) |
| 4 | Deliberately omit context (no clipboard, no note) |
| 5 | Conflicting inputs (clipboard vs selected note vs plain chat) |

**Measure**

| Metric | Meaning |
|--------|---------|
| Hallucinated context | Bad assembly |
| Missing key info | Context failure |
| Overload lag | Compression inefficiency |
| Irrelevant outputs | Routing issue |

**Red flags:** system “forgets what you meant”; generic/detached replies; frequent re-explaining.

---

### Layer 3 — UI / glassmorphism usability

**Goal:** Interaction comfort and cognitive load.

**Focus:** Alt+Space speed, overlay clarity, text readability, animation distraction, palette discoverability.

**Measure**

| Metric | Meaning |
|--------|---------|
| Visual fatigue | UI overload |
| Hesitation to open | Poor ergonomics |
| Readability strain | Glass/contrast failure |
| Perceived latency | Animation delay illusion |

**Critical insight:** You are not testing aesthetics. You are testing:

> Does the UI disappear from attention while staying usable?

If the UI is noticeable → it is too heavy.

---

### Layer 4 — Failure modes (most important)

**Goal:** Graceful degradation under breakage.

| # | Break | Expected |
|---|-------|----------|
| 1 | Kill Ollama | Clear `chat.error`, UI responsive |
| 2 | Clear/remove Obsidian path | Note commands fail clearly |
| 3 | Empty clipboard + “Summarize this clipboard” | No silent success |
| 4 | Rapid command spam (5+ in 10s) | No crash, queue sane |
| 5 | Disconnect / reconnect Ollama | Retry succeeds |

**Measure**

| Metric | Meaning |
|--------|---------|
| Graceful degradation | System maturity |
| Crash recovery | Stability |
| Error clarity | Usability under failure |
| Silent failures | Architectural weakness |

---

## Daily driver scorecard (mandatory)

Record with:

```powershell
$py = "C:\Users\S8633\AppData\Local\Python\bin\python.exe"
& $py scripts/phase5c_scorecard.py record
```

Or edit `%APPDATA%\AICommandCenter\phase5c_scorecard.json` from `docs/templates/phase5c_scorecard.json`.

### Scores (1–5 each)

| Category | Field |
|----------|-------|
| Core Loop | `scores.core_loop` |
| Context Handling | `scores.context_handling` |
| UI Experience | `scores.ui_experience` |
| Failure Recovery | `scores.failure_recovery` |
| Overall Trust | `scores.overall_trust` |

### Interpretation

| Score | Meaning |
|-------|---------|
| 5 | Feels like native OS tool |
| 4 | Usable daily with minor friction |
| 3 | Usable but noticeable friction |
| 2 | Annoying; avoids usage |
| 1 | Unusable / breaks flow |

### Gold standard (Phase 5C PASS)

| Criterion | Threshold |
|-----------|-----------|
| Core Loop | ≥ 4 |
| Context Handling | ≥ 4 |
| Failure Recovery | ≥ 4 |
| Natural reuse | `natural_reuse: true` (subjective) |
| Preflight | Automated preflight PASS |

Gate:

```powershell
& $py scripts/verify_phase5c.py
```

---

## Telemetry evidence (5C+)

During the stress test, telemetry records passively (no code changes mid-session).

```powershell
& $py scripts/telemetry_summary.py
```

Example output:

```text
SESSION SUMMARY (20260618T120000Z)

Commands:
- total: 12
- success: 11
- fail: 1
- avg latency: 1842.3 ms

UX:
- palette opens: 8
- cancellations: 2
- hesitation rate: 12.5%

Context:
- over budget: 1
- avg tokens: 934.0

Friction Score:
- LOW
```

Combine subjective scorecard scores with telemetry friction score for sign-off.

---

## Sign-off

After scorecard + gate PASS, update `docs/PHASE_LEDGER.md` § Current with date, scores, and blockers.

Legacy short protocol: [DAILY_DRIVER.md](DAILY_DRIVER.md) (Tests A–C subset of Layer 1 + 4).
