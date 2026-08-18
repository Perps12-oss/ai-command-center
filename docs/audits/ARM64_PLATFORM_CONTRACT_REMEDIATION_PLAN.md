# ARM64 Platform Contract Remediation Plan

**Date:** 2026-08-18  
**Authority:** Owner-accepted Outcome C from [`MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md`](MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md)  
**Baseline:** `origin/main` @ `354681b087bb75d1e2cd80ac630d4181c529fe4b`  
**Status:** PLAN LOCKED for ARM64 remediation sequence — not an ADR, not a SKU decision, **not** x86-64 work  
**Owner decision (2026-08-18):** Accept §4 two-tier policy **provisionally**, **subject to evidence validation of the allowlist**. Matrix WARN is **not** a granted exception.  
**Constraint:** No x86-64 implementation in steps 2–7. Do not draft ADR-026. Do not change v1.0/v1.1 scope. PERF Art XV is **not** in the architecture gate unless a demonstrated ISA dependency appears.

This document is the ARM64 remediation plan. It is **not** an x86-64 plan.

**Execution status (2026-08-18):** Sequence **step 1 done**. Steps **2–3 tooling** added: `scripts/capture_arm64_isa_evidence.py` + [`ARM64_ISA_EVIDENCE_SESSION.md`](ARM64_ISA_EVIDENCE_SESSION.md). **Operator Windows ARM64 session still required.** Step 4+ not started. Allowlist still `pending`.

---

## 1. Executive summary

ACC’s declared v1.0 desktop SKU is **native Windows ARM64**. That claim is only **partially proven**: the GUI was operator-attested, while Python PE, Ollama PE `0xAA64`, and a coherent PE policy were **not** recorded in Wave 5 / Gate 5, and the GitHub **ARM64 Native Gate** has **zero runs**.

Two written policies currently coexist:

- **Two-tier Phase 0** (`compatibility_matrix.md` + `wheel_audit.py`): inference-critical must be native ARM64; some utility wheels may be emulated with WARN.
- **Zero non-ARM64 PE** (`check_arm64_binaries.py` + live `@arm64` test + risk-area #1 copy): any AMD64 `.exe`/`.dll`/`.pyd` in the env fails.

Those cannot both be the production contract. **Reconciling them by copying matrix WARN into the scanner without proof would not close the contradiction** — it would only rename it.

**Locked sequence (owner, 2026-08-18):**

1. Owner accepts two-tier policy **provisionally** (done in this revision’s decision record).  
2. One ARM64 operator evidence session.  
3. Capture host + Python + PE + Ollama + scanner + preflight + Git SHA.  
4. Reconcile scanner / wheel audit / matrix / tests / documentation — **only after allowlist rows are evidenced or denied**.  
5. Run ARM64 native gate.  
6. Attach GUI evidence to the **same** interpreter + commit.  
7. Close ARM64 platform-contract remediation gate.  
8. **Only then** reopen multi-architecture feasibility.  
9. **Only then** decide whether x86-64 belongs in v1.0 or v1.1.

**No x86-64 implementation work in steps 2–7.**

**Prove and unify the ARM64 contract first. Do not evaluate Windows x86-64 until step 8.**

---

## 2. Current contract (what the code actually enforces)

Distinguish layers. The code does **not** implement a single “host ISA == binary ISA” invariant.

| Layer | What “architecture” means | What code checks today | When | If fail |
|-------|---------------------------|------------------------|------|---------|
| **Host OS ISA** | Windows installed as ARM64 vs AMD64 | **Not checked.** No `PROCESSOR_ARCHITEW6432` / native-system probe | — | — |
| **Python / process ISA** | Arch of this interpreter | `is_arm64()` = `platform.machine().upper() == "ARM64"` (`detector.py` L23–31) | **Runtime** `main.py` L20–22; Phase 0 preflight; `benchmark_startup.py` | GUI exit 1; preflight/benchmark fail |
| **Python executable PE** | `IMAGE_FILE_MACHINE_*` of `sys.executable` | `get_pe_machine_type` in **live test skip only** (`test_arm64_binaries.py` L110–114) | Test | Skip, not product fail |
| **Ollama PE** | PE of `ollama.exe` | `validate_ollama_arm64_native()`: PASS only if PE `ARM64` (`0xAA64`); AMD64 always fail (`detector.py` L134–148) | **Phase 0 CLI only** (`preflight_arm64.py` L156) | Preflight exit 1; **GUI still starts** if preflight skipped |
| **Wheel / extension PE** | `.pyd`/DLL of site-packages | `wheel_audit._classify_extension`: ARM64 → `native_arm64`; AMD64 → **`emulated_amd64`** always | Phase 0 print | `FAIL` only if package ∈ `PERFORMANCE_CRITICAL_PACKAGES` **and** emulated; else WARN |
| **Env-wide PE scan** | Every PE under prefix + site-packages | `check_arm64_binaries.py`: offender if machine ≠ `0xAA64` | Dispatch CI, Azure ARM64 job, pre-commit hook (often unwired vs UCGS hook) | Scanner exit 1 |
| **Emulation** | x64 binary on ARM64 Windows (Prism) | Implied by AMD64 PE on assumed ARM64 host; **not** measured via `SetProcessMachineTypeToEmulate` except optional Windows test | — | Product does not detect “host is ARM64 but this file is emulated” separately from “file is AMD64” |

**Intended product identity (docs):** Windows ARM64 desktop; native ARM64 Python required; do not use PATH x64-emulated `python` (`README.md`).

**Intended Phase 0 policy (matrix):** inference-critical native FAIL; utility emulated WARN.

**Intended risk-area #1 (testing guide + scanner docstring):** no non-ARM64 PE in the environment.

`platform.machine()` alone is **not** sufficient evidence: it does not record PE of `python.exe` or Ollama, and Wave 5 never attached it. On Windows ARM64 it is still a **useful process-ISA signal** (x64-emulated Python reports `AMD64`, so `main.py` refuses that process). It is not a host-OS proof and not a dependency proof.

---

## 3. Contract contradictions (three PE policies)

Call the three policies **P-Scan**, **P-Audit**, **P-Matrix**. Preflight **composes** P-Audit + Ollama PE + `platform.machine()`, and does **not** run P-Scan.

| Subject | P-Scan `check_arm64_binaries.py` | P-Audit `wheel_audit.py` + `preflight_arm64.py` | P-Matrix `compatibility_matrix.md` |
|---------|----------------------------------|--------------------------------------------------|-------------------------------------|
| Python process | Indirect (scans `python.exe` as PE; non-ARM64 fails) | `platform.machine()==ARM64` hard fail; **no** Python PE | Claims native 3.14 ARM64 interpreter; PATH python often emulated — do not use |
| Ollama | If `ollama.exe` is under scan roots, AMD64 fails; Ollama may live outside prefix | Separate hard fail unless PE ARM64; HTTP also required (env conflated with service up) | Native PE `0xAA64` required; HTTP alone insufficient |
| aiohttp / yarl / multidict / frozenlist / propcache | **FAIL** if AMD64 `.pyd` present | **WARN** (`OPTIONAL_DEPS`, not in `PERFORMANCE_CRITICAL_PACKAGES`) | **Emulated acceptable** |
| watchdog, pywin32 | **FAIL** if AMD64 | **WARN** | **Emulated acceptable** |
| psutil, pyyaml | FAIL if AMD64 | Import required; emulated still **WARN** (critical only fails if missing) | Listed native; policy text also says pyyaml WARN-if-emulated |
| Whisper / TTS / Screenpipe | FAIL if AMD64 PE present | **FAIL** if installed and emulated | FAIL if not native; **not installed** |
| Unknown AMD64 PE in site-packages | **FAIL** | Not classified unless in audit lists | Unspecified |
| Host AMD64 (x86-64 PC) | Would FAIL entire env (all PE AMD64) | `is_arm64` FAIL | N/A (ARM64 document) |
| `tests.yml` Windows | Scan `continue-on-error` (x64 runner) | Not run | — |
| `arm64-gate.yml` | Hard gate | Not in that workflow (pytest + scanner + interpreter string) | — |
| Live test `test_live_environment_is_pure_arm64` | Aligns with P-Scan (no offenders) | — | Contradicts matrix if aiohttp is AMD64 |

**Where they diverge:** P-Scan and the live ARM64 test are **strict purity**. P-Audit and P-Matrix are **two-tier** and assume the **host is always ARM64** (AMD64 wheel ⇒ “emulated”, never “native on AMD64”). Preflight never calls the scanner, so an operator can “pass Phase 0” with emulated aiohttp and still fail risk-area #1 if the scanner actually ran.

**This plan does not silently pick a winner by changing code.** Section 4 is **provisionally accepted** (two-tier core). Allowlist rows remain **candidates until evidenced** (§4.1). Matrix WARN does not grant an exception.

---

## 4. Authoritative policy (provisional)

### Locked core (not provisional)

**Name:** ARM64 native core; utility emulation **only if evidenced**.

1. **Host:** Supported desktop host is **Windows ARM64** (native OS). Evidence must include a host-ISA signal, not only `platform.machine()` of the process.
2. **Process:** The ACC GUI/process must be **native ARM64 Python**: `platform.machine() == "ARM64"` **and** `python.exe` PE == `0xAA64`. x64-emulated Python on ARM64 Windows remains **forbidden**.
3. **Inference / runtime-critical native binaries:** **No emulation.** Must be PE `0xAA64`:
   - `ollama.exe` (already Phase 0)
   - any installed member of `PERFORMANCE_CRITICAL_PACKAGES` (whisper/TTS/screenpipe — currently not in `requirements.txt`)
   - Tk/Python runtime used to start `main.py` (covered by process PE)
4. **Utility native extensions:** Default **FAIL** (P-Scan). A package may join the allowlist **only after** §4.1 evidence is complete for that row. `compatibility_matrix.md` WARN is a **historical claim**, not a grant.
5. **Everything else with a PE:** **Not evidenced-allowlisted ⇒ FAIL.**
6. **Pure Python** wheels: not PE; no ISA fail.
7. **Ollama HTTP down:** service availability, not ISA proof. Do not treat “Ollama not running” as “not ARM64.”

**Answer to the required question (provisional):**

> **Is emulation permitted?**  
> **Not yet, except as candidates pending §4.1.** Core (host, process, Python PE, Ollama PE, inference-critical if installed) is **never** emulated.  
> **Candidate classes only:** utility/I/O extensions listed below.  
> **Grant rule:** each row must show native vs AMD64 evidence, why emulation exists, inference-critical = No, and runtime impact. If any cell cannot be established, **do not allowlist** — keep scanner FAIL and change the matrix to match, or replace the wheel with native ARM64.

### 4.1 Allowlist evidence bar (must pass before step 4 reconcile)

**Default: deny.** Do not grant an exception because the matrix currently says WARN. The point of this remediation is to **eliminate** the scanner ↔ matrix contradiction, not to encode the matrix into the scanner.

| Package | Native/AMD64 evidence | Why emulation exists | Inference-critical? | Runtime impact | Policy |
|---------|----------------------|----------------------|---------------------|----------------|--------|
| aiohttp transitives (`aiohttp`, `yarl`, `multidict`, `frozenlist`, `propcache`) | **Required** (scanner JSON + wheel tags / PE of `.pyd`) | **Establish** (no `win_arm64` wheel? install chose amd64?) | No | **Establish** (chat HTTP, sidecar — latency, crash, Prism cost) | **Allow only if evidenced**; else **Deny** |
| watchdog | **Required** | **Establish** | No | **Establish** (vault/fs watch path) | **Allow only if evidenced**; else **Deny** |
| pywin32 | **Required** | **Establish** | No | **Establish** (which ACC paths import it; test-only vs runtime) | **Allow only if evidenced**; else **Deny** |

**Minimum proof per row (operator session, same venv as `main.py`):**

- PE machine of each relevant `.pyd`/`.dll` (`ARM64` vs `AMD64`) or pip filename tag (`win_arm64` vs `win_amd64`).
- Whether a native ARM64 wheel exists on PyPI for the installed version (yes/no + source).
- If AMD64: why it was installed (resolver, missing wheel, explicit pin).
- Import graph: production `ai_command_center` vs tests-only (`pywin32` is `requirements-test.txt` today).
- Runtime impact: does GUI/chat/indexing load it on the hot path? Any known freeze/emulation cost? If unknown, **Deny**.

**If Deny:** that package stays under P-Scan FAIL. Step 4 must update matrix/preflight **to FAIL** (or drop/replace the dependency). Do not leave WARN vs FAIL split.

**If native ARM64 PE is already present:** the row is **not an exception** — record as native PASS; no allowlist entry needed.

### Why two-tier core is still the provisional frame

- Core native requirements are unambiguous and already in `main.py` + Ollama PE check.
- Utility exceptions are **optional and evidence-gated**, so the frame does not pre-judge aiohttp.
- Strict empty allowlist remains the outcome if all three rows are **Deny**.

**Owner reject of two-tier core** would mean host/process/Ollama may be emulated — that is **not** this plan.

### What must agree after evidenced allowlist (step 4, authorized later)

Scanner allowlist **equals** evidenced Deny/Allow rows only; `wheel_audit` severity; `compatibility_matrix.md`; live `@arm64` test; preflight; `README_TESTING.md` risk #1. **One policy SoT.** Do not reconcile tools until §4.1 is filled.

---

## 5. Required ISA evidence (native ARM64 release environment)

Capture on the **operator Windows ARM64 desktop** that runs `main.py`, using the **same** `sys.executable` as launch. Prefer attaching command output (JSON/text) to an audit ledger. Do not treat “validator exists” as “this machine passed.”

### Required release evidence (architecture-contract closure)

| Field | How (existing tools; no new product required to *define* this) | Pass criterion |
|-------|----------------------------------------------------------------|----------------|
| Timestamp (UTC) | Clock on the capture | Present |
| Git identity | `git rev-parse HEAD` of the tree launched | Matches claimed `main` (or named commit) |
| Host OS ISA | Windows Settings / `echo %PROCESSOR_ARCHITECTURE%` **and** `%PROCESSOR_ARCHITEW6432%` | Native ARM64 host (e.g. `ARM64` with empty WOW64 overlay, not x64 process on ARM64 OS without documenting it) |
| Process `platform.machine()` | Preflight line or `python -c "import platform; print(platform.machine())"` | `ARM64` |
| Python executable path | `sys.executable` | Canonical tree interpreter (not OneDrive legacy) |
| Python PE | `get_pe_machine_type(sys.executable)` (detector already exists) | `ARM64` (`0xAA64`) |
| Ollama PE | `validate_ollama_arm64_native()` detail | Native ARM64 PE confirmed (not merely HTTP 200) |
| Wheel/audit rows | `preflight_arm64.py` wheel section **or** `audit_all_deps()` | Record every WARN/FAIL; **do not treat WARN as allowlist grant** |
| Scanner result | `python scripts/check_arm64_binaries.py --json` | Attach **raw JSON** (expected FAIL if AMD64 utilities present). Use offender list to fill §4.1 |
| Allowlist dossier | Per-row §4.1 table | Each candidate **Allow** or **Deny** with PE + reason + impact; no empty cells |
| Preflight result | `scripts/preflight_arm64.py` exit code + full stdout | Recorded; HTTP/Ollama-down called out separately from PE |
| GUI identity | Existing runtime identity / `freeze_fix` banner if launching GUI | Same tree as git identity |

`baseline.json` (`benchmark_startup.py` → `write_baseline_log`) already stores `python.executable` and `python.machine` — **required attachment** if the file exists; generate with the same interpreter. It does **not** currently store Python PE or Ollama PE; those must be captured via preflight/detector until a later authorized schema change.

### Useful diagnostic evidence (not required to close the ISA contract)

- Full `check_arm64_binaries.py` offender list (even allowlisted)
- `pip list` / wheel tags (`win_arm64` vs `win_amd64`)
- RAM / import ms from `baseline.json` (startup quality, not ISA)
- Screenshots of GUI (Gate 5 still has none) — product UX, not PE
- PERF Inspector soak traces (Art XV) — **out of this gate** unless a §4.1 runtime-impact finding **demonstrates** an ISA/emulation coupling (record that coupling only; do not open a completion audit)
- `SetProcessMachineTypeToEmulate` smoke (`test_arm64_emulation_smoke.py`) — extra
- GitHub `arm64-gate.yml` green run — **Class A duplicate** of operator PE proof if `windows-11-arm` matches the product venv policy (may differ from operator 3.14 path)

### Class rule

- **Class A:** machine log from CI `windows-11-arm` or attached stdout/JSON from the desktop.  
- **Class B:** operator prose without those fields — **insufficient** for architecture-contract closure (Gate 5 GUI attestation is Class B today).

---

## 6. Validation gaps (classified)

| Gap | Current state | Classification | Notes |
|-----|---------------|----------------|-------|
| `arm64-gate.yml` **0 GitHub runs** | `workflow_dispatch` only; `windows-11-arm` unused | **Required before ARM64 platform-contract closure** *or* substituted by attached operator scanner+preflight JSON | Blocking for “CI proves native ARM64.” Not blocking Stream A–F code already on `main`. |
| Wave 5 / Gate 5 missing PE/ISA fields | GUI Class B; Linux Class A is x86_64 | **Required before ARM64 platform-contract closure** | Does **not** by itself reopen Wave 5 program features; it is an evidence supplement. |
| PERF GUI budgets not Closed | Art XV Mitigated; Tom: no ARM64 soak | **Unrelated to architecture-contract gate** unless a demonstrated ISA/emulation dependency appears | Do **not** pull Art XV into steps 2–7. Separate performance DoD. |
| Package smoke on `windows-latest` builds x64 exe, does not launch | File-exists only | **Unrelated to ARM64 native proof**; **Desirable** hygiene | Prevents mistaking an AMD64 artifact for the ARM64 SKU. Out of scope for ISA ledger. |
| GUI attestation without machine/ISA | 2026-08-17 operator PASS | **Required before ARM64 platform-contract closure** | Re-attest **with** §5 required fields, or attach logs to the existing date’s tree if still valid. |
| Preflight HTTP hard-fail vs ISA | Ollama down ⇒ Phase 0 FAIL | **Desirable** to split env vs service | Do not block ISA capture if PE can still be read from `ollama.exe` on disk. |
| UCGS hook vs `.pre-commit-config.yaml` ARM64 scan | Governance audit: UCGS hook may skip arm64-binary-scan | **Desirable** | Local gap; not Wave 5. |
| `main.py` does not run Ollama PE check | GUI can start without Phase 0 | **Desirable** for runtime enforcement; **not** required if release process **mandates** attached preflight | Smallest contract = process gate + release evidence, not new startup coupling. |
| Python 3.14 operator vs CI 3.11/3.12 | Matrix vs `tests.yml` | **Desirable** | Record which interpreter was proven; do not silently retarget CI in this plan. |
| `PlatformService` Windows `NotImplementedError` | Tray lives in `TrayController` | **Unrelated to architecture support** | Stream G / fossil; OS not ISA. |

**Blocking ARM64 *architecture-contract* closure:** missing ISA record; incomplete §4.1 Allow/Deny rows; tools still contradict after step 4; no native-gate run (step 5); GUI not tied to same interpreter+commit (step 6).

**Not in this gate:** x86-64 SKU, Stream G, PERF Art XV Closed (unless demonstrated ISA dependency), packaging launch smoke, macOS/Linux.

---

## 7. Minimal remediation work (mapped to locked sequence)

**No x86-64 work in B–F (sequence steps 2–7).** PERF soak is not a row here.

| Seq | Item | Current state | Required state | Evidence required | Owner/Agent | Dependency |
|-----|------|---------------|----------------|-------------------|-------------|------------|
| 1 | **A. Provisional policy** | Contradiction open | Two-tier **core** accepted; allowlist **not** granted | This owner decision | Owner | Done |
| 2–3 | **B. Operator evidence session** | No PE ledger | §5 capture on one commit + venv | Run `python scripts/capture_arm64_isa_evidence.py --out …` on ARM64 desktop; attach JSON | Operator | Same interpreter as `main.py` |
| 2–3 | **B1. Allowlist dossier** | Matrix WARN only | Each §4.1 row Allow **or** Deny | PE/tags, why AMD64, import path, runtime impact | Operator + reviewer | B |
| 4 | **C. Reconcile tools** | Scanner FAIL vs matrix WARN | One rule matching **evidenced** Allow/Deny | Diff: scanner, wheel_audit, matrix, tests, README_TESTING | Implementation **after** B1 | A, B1 |
| 5 | **D. ARM64 native gate** | 0 GitHub runs | Successful `arm64-gate.yml` dispatch (post-reconcile) | GH run URL | Operator/CI | C |
| 6 | **E. GUI same identity** | Attestation without ISA | GUI note with same git + `sys.executable` as B | Identity banner / short ledger | Operator | B |
| 7 | **F. Close ISA gate** | Open | §8 checklist complete | Ledger addendum | Docs after D+E | C, D, E |
| 8 | **G. Reopen multi-arch audit** | Premature | Feasibility sequel only after F | New audit, not this plan | Later | F |
| 9 | **H. v1.0 vs v1.1 x86-64** | Not authorized | Owner SKU decision only after G | — | Owner | G |

**Out of this sequence:** dual PyInstaller, ADR-026, Stream G, Art XV soak, packaging launch smoke.

---

## 8. Evidence required for closure (architecture-contract gate)

The **ARM64 platform-contract remediation gate** is satisfied when **all** of the following are true:

1. **Policy:** Two-tier **core** provisionally accepted (recorded).  
2. **Allowlist:** Every §4.1 candidate is **Allow** with full evidence **or** **Deny** with follow-through (matrix/scanner FAIL or native replacement). No WARN-only grants.  
3. **No contradiction:** After step 4, scanner, wheel audit, matrix, tests, and docs **agree**.  
4. **ISA record:** §5 required fields for a named commit, including Python PE `0xAA64` and Ollama PE `0xAA64` (or PE-on-disk if HTTP down).  
5. **Process + host:** `platform.machine() == ARM64` and host OS ARM64 on that executable.  
6. **Native gate:** Step 5 successful `arm64-gate.yml` run (post-reconcile).  
7. **GUI:** Step 6 attestation uses the **same** git SHA + interpreter as the ISA record.

**Not** required for this gate: PERF-001–004 Closed; packaging MSI; x86-64; Stream G. **Do not expand this gate into a broad ACC completion audit.**

---

## 9. Re-entry criteria for x86-64 evaluation

Reopen [`MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md`](MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md) (or a sequel) **only when** all hold:

1. Architecture-contract gate in §8 is **satisfied** (not merely planned).  
2. PE policy is **one** rule; matrix/scanner/preflight/docs **agree**.  
3. Native ARM64 ISA evidence is **attached** (Python PE + Ollama PE + host + git).  
4. ARM64 native gate has a **successful run** **or** a written owner residual that CI ARM64 is not required.  
5. The implemented invariant is understood to be **ARM64-only process + two-tier deps** (or strict purity), **not** host-match `{AA64, 8664}` whitelist.  
6. No open architecture-contract contradiction (unknown AMD64 PE unexplained).  
7. PERF Art XV stays **outside** the ISA gate; a later SKU discussion may note Mitigated vs Closed but must not treat this remediation as having closed GUI budgets.  
8. Sequence **step 8** has happened (feasibility reopened). Step 9 is the v1.0 vs v1.1 decision — **not before**.  
9. Next ADR number is **re-read** from `docs/architecture/adr/README.md` (do not assume ADR-026).

Until step 8: **no** x86-64 implementation, **no** dual-SKU v1.0/v1.1 declaration. Steps 2–7 remain ARM64-only.

---

## 10. Explicit out of scope

This plan does **not**:

- Authorize or specify Windows x86-64, Linux GUI, or macOS work  
- Create or reserve ADR-026  
- Change v1.0/v1.1 product scope  
- Implement scanner/preflight/CI/docs (planning only)  
- Close PERF Art XV or fold Art XV into the ISA gate (unless a demonstrated emulation/ISA dependency is recorded on a §4.1 row)  
- Implement x86-64, dual SKU, or ADR-026 during steps 2–7  
- Fix `PlatformService` stubs, UCGS vs pre-commit drift, or packaging launch  
- Require bundling Ollama or adding whisper/TTS  
- Treat Linux Cloud pytest as ARM64 GUI/ISA evidence  

---

## Final statement

**No x86-64 implementation or v1.0/v1.1 scope decision is authorized until the ARM64 platform-contract remediation gate is satisfied.**

**No x86-64 implementation work is authorized in sequence steps 2–7.**
