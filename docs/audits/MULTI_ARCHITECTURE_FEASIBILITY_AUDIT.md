# Windows Multi-Architecture Feasibility Audit

**Date:** 2026-08-18  
**Auditor:** Cursor Cloud agent (read-only investigation)  
**Baseline:** `origin/main` @ `354681b087bb75d1e2cd80ac630d4181c529fe4b` (`docs: Wave 4 Gate 5 verification and Gate 6 close-out`)  
**Authority:** Governance decision gate — evidence first, decision second, ADR third, implementation last  
**Scope:** Native Windows x86-64 as a possible second SKU beside Windows ARM64 for a hypothetical v1.0  
**Out of scope:** Implementation, ADR drafting, CI changes, SKU declaration, Cross-OS (macOS/Linux)

**This report is not an approval to implement.**

---

## Executive conclusion

**Outcome: C — Existing platform contract has unresolved issues. Fix the ARM64 baseline validation before deciding v1.0 vs v1.1 x86-64.**

The current contract is “this process must be ARM64,” not “host ISA must match native binaries.” Wave 5 / Gate 5 ledgers do not record Python PE, `platform.machine()`, or Ollama PE `0xAA64`. The GitHub workflow that would prove a pure ARM64 environment (`arm64-gate.yml`) has **zero runs**. PERF GUI budgets remain operator-owned and **not Closed**. Adding `0x8664` to a whitelist would be the wrong fix even if the baseline were proven.

**Confidence in Outcome C: 85%.**  
**ARM64 baseline confidence: Partially proven** (product identity + operator GUI attestation exist; native-ISA proof for Python / Ollama / inference PE is not in the verification ledgers).

---

## 1. ARM64 baseline reality

**Rating: Partially proven**

### 1.1 Validation framework (what exists vs what ran)

`scripts/preflight_arm64.py` is a **Phase 0 CLI**, not imported by `main.py`. It hard-fails (`return 1`) when any of these fail: Python ≥3.11, `platform.machine() == "ARM64"`, `baseline.json` present, Ollama HTTP `/api/tags`, `validate_ollama_arm64_native()`, critical Phase 0 imports (`psutil`, `pyyaml`). Optional deps and wheel-audit `WARN` rows do not fail the process unless severity is `FAIL` (performance-critical + emulated).

| Check | Mechanism | Phase | Blocks `main.py`? |
|-------|-----------|-------|-------------------|
| Interpreter ISA | `is_arm64()` → `platform.machine().upper() == "ARM64"` | **Runtime** (`main.py` L20–22) and Phase 0 | **Yes** — stderr + exit 1 |
| Python PE of `sys.executable` | `get_pe_machine_type` in live test only | Test (`tests/test_arm64_binaries.py` L110–114) | No |
| Ollama PE `0xAA64` | `validate_ollama_arm64_native()` | Phase 0 only | **No** if operator skips preflight |
| Env PE scan | `scripts/check_arm64_binaries.py` | CI dispatch / pre-commit | Not at GUI startup |
| Wheel class | `wheel_audit.audit_all_deps()` | Phase 0 only | Prints; `FAIL` only for inference-critical emulated wheels |

`is_arm64()` does **not** inspect the Python PE. It only compares `platform.machine()` to the string `"ARM64"`. That is enough to reject x64-emulated Python on Windows ARM64 (emulated x64 Python reports `AMD64`), and enough to reject native Windows x86-64. It is **not** a PE proof, and it does not treat Linux `AARCH64` / `X86_64` as Windows SKUs.

Callers of `preflight_arm64.py`: documentation and operator setup (`README.md`, `compatibility_matrix.md`). No production import. `benchmark_startup.py` L23–25 also hard-requires `is_arm64()` before writing `baseline.json`.

### 1.2 Wave 5 / Gate 5 — what architecture was actually recorded?

`docs/audits/WAVE_5_FULL_SYSTEM_VERIFICATION.md`:

- Linux Class A: keyword pytest, arch_lint, constitution, UCGS, `create_application()` — **Linux x86_64 Cloud**, not Windows ARM64 Python.
- Windows ARM64 GUI: Class B operator attestation via `GATE5_WINDOWS_ARM64_GUI_VERIFICATION.md` (2026-08-17). **No screenshots. No `sys.executable`. No `platform.machine()`. No Ollama PE.** Cloud host cannot launch `main.py` because `is_arm64()` is false.

`docs/audits/WAVE_4_GATE_5_VERIFICATION.md`: same split — Linux machine PASS; Windows “runtime enforcement” is operator-attested F1–F4 behavior, not PE architecture.

**Ollama PE `0xAA64` is not traced in Wave 5.** `validate_ollama_arm64_native()` is only called from `scripts/preflight_arm64.py` L156. Wave 5 does not claim that script was run, and does not quote a PE machine type.

### 1.3 Performance / GUI budgets

`docs/audits/PERF_BASELINE_REPORT_2026-07-26.md`: environment **Linux x86_64**. UI thread / view-switch / inspector refresh **N/A**.

`docs/audits/TOM_AUDIT_PERF_001_002_FREEZE_CLOSEOUT_2026-08-04.md`: **no Win ARM64 GUI soak**, no before/after Tk timings.

`PERFORMANCE_CONSTITUTION.md` Article XV: PERF-001–004 **Mitigated** headless; Win ARM64 soak **not Closed**. PERF-005 still Open.

GUI thread budgets are **architecture-sensitive in the sense that they have never been closed on the declared SKU**, not that the constants are ARM64-ISA-specific.

### 1.4 Captured baseline.json fields

`write_baseline_log()` in `detector.py` L159–176 would record `python.executable`, `python.machine`, RAM, import ms — **if** `benchmark_startup.py` ran on native ARM64. No `baseline.json` is in the repository (it lives under `%APPDATA%\AICommandCenter`). Wave 5 does not quote those fields.

`compatibility_matrix.md` **claims** native ARM64 Python 3.14 at `C:\Users\S8633\AppData\Local\Python\bin\python.exe` and Ollama PE `0xAA64`, with “Last verified: run preflight.” That is an operator checklist, not a Wave 5 evidence attachment. CI Python matrix is **3.11/3.12**, not 3.14.

### 1.5 Dependencies vs native ARM64

`requirements.txt` has **no** environment markers for `win_arm64` / `win_amd64`. No `setup.py` / `pyproject.toml` in repo. Architecture is not constrained at install time.

| Package | In `requirements.txt`? | Native x86-64 generally? | ARM64 notes in-repo |
|---------|------------------------|--------------------------|---------------------|
| customtkinter | Yes | Yes (Tk wrapper) | Matrix: native / optional |
| Pillow | Yes | Yes | Matrix: native |
| psutil, pyyaml | Yes | Yes | Phase 0 critical |
| keyboard, pystray | Yes | Yes (mostly pure) | Hotkey/tray |
| aiohttp (+ yarl, multidict, …) | Yes | Yes | Matrix: **emulated AMD64 WARN** on ARM64 host |
| pywin32 | **Test extra only** (`requirements-test.txt`; `sys_platform == win32`) | Yes | Matrix: emulated WARN |
| Ollama | External binary | Yes (official amd64 + arm64) | Phase 0 PE hard-fail if not ARM64 |
| faster-whisper / whisper / TTS / screenpipe | Not installed | N/A | `PERFORMANCE_CRITICAL_PACKAGES` in `wheel_audit.py`; matrix Unknown |

**Inference-critical native ARM64 is claimed for Ollama in the matrix, not proven in Wave 5.** Utility wheels are **explicitly allowed emulated** in the matrix while `check_arm64_binaries.py` **fails any non-`0xAA64` PE** in site-packages. Those two policies cannot both be the production contract.

### 1.6 Baseline confidence summary

| Claim | Evidence class | Verdict |
|-------|----------------|---------|
| GUI launches on operator Windows ARM64 box | Class B attestation, no artifacts | Partially proven |
| Python is native ARM64 PE, not x64-emulated | Gate exists (`is_arm64` + live test skip); Wave 5 does not record PE/`machine` | Unproven in ledgers |
| Ollama PE = `0xAA64` | Validator exists; not invoked by Wave 5 | Unproven in ledgers |
| All inference-critical deps native ARM64 | Only Ollama is in the live inference path; not PE-logged | Unproven in ledgers |
| Pure ARM64 site-packages (no AMD64 `.pyd`) | Hard scanner exists; GH `ARM64 Native Gate` **0 runs**; matrix admits emulated aiohttp | Contradicted / unproven |
| GUI PERF budgets on ARM64 | Tom + Art XV: not Closed | Unproven |

---

## 2. Host ↔ binary architecture contract

**Intended invariant (this audit):** `host ISA == process/native binary ISA` (ARM64↔ARM64 PASS, x86-64↔x86-64 PASS, cross-ISA FAIL, x86-32 FAIL).

**Implemented invariant:** `platform.machine() == "ARM64"` for the GUI process, and (Phase 0 only) Ollama PE == ARM64. AMD64 binaries are treated as **emulation on ARM**, never as **native on AMD64**.

### 2.1 Callers

**`validate_ollama_arm64_native()`**

- `scripts/preflight_arm64.py` L156 only (plus re-export in `platform/__init__.py`).
- Phase 0. Result `False` → preflight `critical_fail` → process exit 1.
- **Not** called at `main.py` startup, chat, or Ollama HTTP client paths.

**`get_pe_machine_type()`**

- `detector.py` `validate_ollama_arm64_native`
- `wheel_audit.py` L53 (`_classify_extension`)
- `tests/test_arm64_binaries.py` L110 (skip if Python PE ≠ ARM64)

Can return `AMD64` (`0x8664`). That result is used to **fail** Ollama (must be ARM64) and to label wheels `emulated_amd64`. It is **not** used as “native on an AMD64 host.”

**`is_arm64()`**

- `main.py` L20 — **runtime hard gate**
- `scripts/preflight_arm64.py` L49
- `scripts/benchmark_startup.py` L23
- `tests/test_arm64_binaries.py` L108

Uses `platform.machine()` only (`detector.py` L23–31). No PE of `python.exe`.

**Additional ISA surface (not in detector.py):** `scripts/check_arm64_binaries.py` — any PE ≠ `IMAGE_FILE_MACHINE_ARM64` (`0xAA64`) is an offender. Host ISA is ignored. Non-Windows hosts skip.

### 2.2 Whitelist fallacy

Adding `0x8664` next to `0xAA64` as “allowed” would:

- PASS ARM64 host + AMD64 Ollama / wheels (the case the product currently forbids as emulation).
- PASS x86-64 host + ARM64 binary (should FAIL).
- Leave `is_arm64()` still blocking native Windows x86-64 GUI.

Host architecture is **not** stored as a settings/SKU constant. It is read dynamically via `platform.machine()` (and, in tests, Python PE). There is no host↔binary matcher.

**Required contract change (not implemented):** classify host ISA (prefer PE of `sys.executable` + `platform.machine()`), classify each binary’s PE, PASS iff equal, FAIL iff mismatch, keep explicit policy if any emulation is ever allowed (today: utilities WARN in matrix, FAIL in scanner — unresolved).

**Confidence that code implements host-match: High that it does not.** It implements ARM64-only.

---

## 3. Wheel audit (`wheel_audit.py`)

`audit_wheel_arch()` returns `native_arm64` | `emulated_amd64` | `pure_python` | `not_installed`. AMD64 is **always** “emulated on ARM” (`wheel_audit.py` L50–57, L87–88). An AMD64 wheel on an AMD64 host would be classified **emulated** and optionally `WARN`/`FAIL`.

`audit_all_deps()` is called from `scripts/preflight_arm64.py` L175 only. **Not** at GUI runtime. `FAIL` (perf-critical + emulated) fails Phase 0. `WARN` (optional + emulated) does not. Current `PERFORMANCE_CRITICAL_PACKAGES` are not in `requirements.txt`, so a typical Phase 0 wheel FAIL from whisper/TTS is unlikely; Ollama is a separate PE check.

**Runtime impact of wheel audit: none** unless the operator runs preflight.

**Host-aware change** is more than 3–5 lines if the public labels (`native_arm64`, `emulated_amd64`) and tests that craft ARM64 PE files stay consistent. There is **no** dedicated `test_wheel_audit.py`. `platform.machine()` on Windows is `ARM64` / `AMD64` in this codebase’s own comments and README; PE of `sys.executable` is the stronger fallback already used in `test_live_environment_is_pure_arm64`.

**Scanner vs audit contradiction is a baseline defect:** `compatibility_matrix.md` L47–50 allows emulated aiohttp/watchdog/pywin32; `check_arm64_binaries.py` L137–178 fails the env if those `.pyd` files are AMD64. Enabling the unused `arm64-gate.yml` against a matrix-compliant install would likely **FAIL**.

---

## 4. Repository-wide ARM64 assumptions

**detector.py + wheel_audit.py are not the only ISA-sensitive files.**

### 4.1 `ai_command_center` Python

| File | Role |
|------|------|
| `platform/detector.py` | ARM64 string gate; PE probe; Ollama ARM64-only |
| `platform/wheel_audit.py` | AMD64 = emulated |
| `platform/__init__.py` | Re-exports |
| `ui/ui_queue.py` L1 | Comment “ARM64-tuned”; constants are 16 ms / 50–200 ms Tk drain — **not ISA opcodes** |
| `platform/hotkey_provider.py` | `sys.platform` (OS), not ISA |
| `platform/runtime_paths.py` | `%APPDATA%` on any Windows ISA |
| `platform/platform_service.py` | OS ABC; Windows methods `NotImplementedError` (tray/hotkey live in `ui/tray.py` + `utils/hotkey.py`) |
| `services/qwenpaw_sidecar_service.py` L222 | `CREATE_NO_WINDOW` on `win32` — OS, not ISA |

False positive: `platform/macos/hotkey_provider.py` keycode `0x64` is F8, not PE `0x8664`.

### 4.2 Scripts / entry / CI / tests (must change for a second SKU)

- `main.py` L20–22 — GUI hard ARM64
- `scripts/preflight_arm64.py`, `scripts/benchmark_startup.py`, `scripts/check_arm64_binaries.py`
- `tests/test_arm64_binaries.py`, `tests/test_arm64_emulation_smoke.py`, `tests/conftest.py` markers
- `.github/workflows/arm64-gate.yml`, `tests.yml` informational scan, `azure-pipelines-tests.yml` ARM64 pool
- `packaging/windows/ai_command_center.spec` `target_arch=None` (host arch of the **CI** runner)
- Docs/identity: `README.md`, `AGENTS.md`, `ARCHITECTURE_DIAGRAM.md`, `compatibility_matrix.md`

### 4.3 Paths / registry

`runtime_paths.py` uses `%APPDATA%\AICommandCenter` for all Windows. No ISA-specific data dir. WiX uses `ProgramFiles6432Folder` (`packaging/windows/Product.wxs` L39) — install root follows 64-bit Program Files on both ARM64 and AMD64 Windows. Registry `HKCU\Software\AICommandCenter` is not WOW64-split in the wxs. **No ARM64-only path contract.**

### 4.4 UI / EventBus

CustomTkinter, EventBus, and hotkeys are **OS-Windows** concerns. Hotkey uses the `keyboard` package (`utils/hotkey.py`) on `win32` regardless of ISA. No ARM64-specific window manager. `PlatformService` Windows tray is **unimplemented** (live tray is `TrayController`).

---

## 5. CI feasibility

### 5.1 What actually runs

| Workflow | Runner | Arch | Trigger | ISA role |
|----------|--------|------|---------|----------|
| `tests.yml` Risk-Area Tests | `windows-latest`, `ubuntu-latest` | **x86-64** (GitHub-hosted default) | push/PR | Headless pytest **already on Windows x86-64** |
| `tests.yml` ARM64 binary scan | same | x64 env | `continue-on-error: true` | Informational; cannot hard-gate |
| `arm64-gate.yml` | `windows-11-arm` | ARM64 (intended) | **`workflow_dispatch` only** | Hard PE + full pytest |
| `package-windows-smoke.yml` | `windows-latest` | **x86-64** | packaging path PR | Builds unsigned exe; **does not launch** `main.py` |
| `ucgs.yml`, tom-audit, etc. | Ubuntu | x86-64 | PR | Governance, not GUI |

**GitHub Actions:** `windows-latest` = x86-64. ARM64 Windows is `windows-11-arm` (already named in-repo) or self-hosted. Azure stage uses pool name `ARM64-Windows` (existence not verified here).

**`gh workflow view` / API: ARM64 Native Gate total runs = 0.** The hard native-ARM64 CI contract has never produced a GitHub Actions artifact.

**Headless pytest on Windows x86-64: already green** on recent `tests.yml` (e.g. run `32082935170` on `main`, success). That does **not** prove GUI, Ollama PE match, or packaging launch.

Linux pytest is **not** a proxy for Windows GUI ISA. It is a proxy for headless core only (already used).

### 5.2 x86-64 CI needs (if SKU approved later)

- Keep `windows-latest` pytest (exists).
- Add a **launch smoke** that `is_arm64` currently makes impossible: run `main.py` / frozen exe long enough to prove the gate is host-native, or a headless flag — **product change**, not 1–2 YAML lines.
- Dual PyInstaller artifacts if MSI ships both ISAs (`target_arch`, two artifact names). Current smoke **already produces an AMD64 exe** that the ARM64 `main.py` gate would reject if launched on x64 with current `main.py` — wait: on x64, `is_arm64()` is false, so **the packaged exe from `windows-latest` cannot start**. Packaging CI does not detect that.
- ARM64 gate must actually run if ARM64 remains a SKU; today it does not.
- Ollama in CI: tests mock HTTP; they do not install Ollama. GUI ISA proof still needs a native desktop (operator or `windows-11-arm` with GUI).

**Wheels:** CustomTkinter, Pillow, psutil, keyboard, pywin32, aiohttp all have win_amd64 wheels. Not a blocker.

**Ollama x86-64:** publicly available; not proven in this repo’s CI.

---

## 6. Runtime / GUI architecture sensitivity

| Area | ARM64-specific? | Finding |
|------|-----------------|--------|
| PERF Art. V UI thread | Budgets are absolute ms, not ISA | **Unclosed on ARM64 GUI**; x86-64 would need its own soak, not a copy-paste of Linux headless |
| Wave 5 GUI latency | Not measured | Operator “GUI working”; no p99 |
| UIQueue | Comment ARM64-tuned; 16 ms drain | Same Tk model on both Windows ISAs; still needs native GUI proof |
| EventBus p99 | Headless Linux baseline | Not ARM64-ISA-tuned in code; profiles will differ by CPU; not a code fork |
| aiohttp | May be emulated on ARM64 per matrix | Native on x86-64; different perf, same API |
| Ollama at inference | HTTP to localhost | **No PE re-check** at chat start; mismatch only caught if Phase 0 ran |
| `baseline.json` thresholds | None for ISA | Logging only |
| Memory budgets | Soak tests RSS caps | Not ISA-coded |

**Emulated testing is not sufficient for GUI PERF closeout** (already stated for ARM64). Native x86-64 GUI validation is required if that SKU is claimed. Headless x86-64 is already done.

**Blocker vs improvement:** unclosed ARM64 PERF soak is a **baseline** issue for claiming ARM64 v1.0 completeness; it is not by itself a reason x86-64 code cannot compile. Combined with missing PE evidence and a never-run ARM64 CI job, it is a **C** condition.

---

## 7. Effort (do not treat line count as risk)

The 1–2 week “mechanical” estimate is **not supported** as a v1.0 add-on **until Outcome C is cleared**. After a host-match contract exists and ARM64 evidence is real, remaining SKU work is still larger than 25–40 lines.

### 7.1 Code (if later authorized) — larger than detector+wheel_audit

| File | Why |
|------|-----|
| `main.py` | Replace ARM64-only process gate with host-native gate |
| `detector.py` | Host↔PE match for Ollama; stop AMD64-always-fail; PE of Python |
| `wheel_audit.py` | Host-aware native vs emulated labels |
| `scripts/check_arm64_binaries.py` | Must become host-ISA scanner or it will fail every x86-64 CI job that is not skipped |
| `scripts/preflight_arm64.py` / `benchmark_startup.py` | Rename/generalize; stop requiring ARM64 string |
| `tests/test_arm64_binaries.py` | Live gate today **requires ARM64 PE**; x86-64 needs a native-match twin |
| Packaging spec + smoke | Dual artifacts; **launch** check |
| Docs/identity | README, AGENTS, matrix — **not** this audit’s job |

**Confidence that “25–40 lines, 2–3 days” is complete: Low (the estimate is incomplete).** Detector+wheel_audit alone is small; scanner + entry + tests + packaging launch + evidence capture is the real surface.

### 7.2 Tests / CI / docs (later)

- Unit tests for host-match (both directions of mismatch).
- Native x86-64 GUI acceptance (hardware). Cloud Linux cannot do it.
- Turn on or replace `arm64-gate.yml` so ARM64 SKU has Class A PE evidence.
- Docs: there is **no** `SUPPORTED_HARDWARE.md` today.

### 7.3 Effort bands (conditional)

| Band | When | Effort | Confidence |
|------|------|--------|------------|
| **Baseline repair only (C)** | Capture PE/`machine` on operator ARM64; reconcile scanner vs matrix; enable or record ARM64 gate | Operator + small CI/docs once authorized | High that this is **prerequisite**, not x86-64 feature work |
| **SKU implementation after C** | Host-match contract + dual packaging + GUI soak x86-64 + ADR | **Likely > 1 week calendar of validation**, even if code edits are days | Medium |
| **Mechanical 1–2 weeks including v1.0 dual SKU** | — | **Not credible** while ARM64 hard gate has 0 CI runs and Wave 5 has no PE log | High |

**Low / Likely / High (for adding x86-64 to v1.0 now): High effort/risk relative to “flip a whitelist,” because v1.0 completeness criteria for ARM64 are themselves incompletely evidenced.**

---

## 8. x86-64 blockers (actual only)

1. **No owner SKU decision / Stream G Gate 1–3.** `STRATEGIC_GAP_MATRIX.md` Stream G missing decision includes **supported SKU set**. `STRATEGIC_RUNTIME_PROGRAM.md` forbids Stream G **code** without Gates 1–3. Windows x86-64 is not macOS/Linux, but it **is** a SKU change. This audit must not declare v1.0 scope.
2. **`main.py` ARM64 hard gate** — process cannot start on native AMD64.
3. **Contract is ARM64-only, not host-match** — a whitelist of `{AA64, 8664}` would authorize emulation on ARM64.
4. **ARM64 production claim lacks Class A ISA evidence** (Wave 5, `arm64-gate` 0 runs, PERF not Closed).
5. **Conflicting PE policies** (matrix WARN vs scanner FAIL) — shipping a second ISA without resolving this leaves both SKUs undefined.
6. **Packaging smoke builds an x64 exe that current `main.py` cannot launch** — dual-SKU packaging is not “already done.”

Non-blockers (do not treat as C): CustomTkinter/Pillow/keyboard win_amd64 availability; `%APPDATA%` path; EventBus source; Ollama existing as an amd64 product.

---

## 9. Conditions before any ADR (including a future multi-arch ADR)

`docs/architecture/adr/README.md` lists **ADR-026 as next free**, informally reserved for Stream D isolation **if** measurement justifies it. A multi-arch ADR must **not** silently consume 026 without re-checking that index.

Prerequisites the owner should require **before** authorizing an ADR for Windows x86-64:

1. **Class A or attached Class B ISA log** from the ARM64 desktop: `platform.machine()`, `get_pe_machine_type(sys.executable)`, `validate_ollama_arm64_native()` detail string showing `ARM64` / `0xAA64`, interpreter path.
2. **Reconcile** `compatibility_matrix.md` vs `check_arm64_binaries.py` (one production PE policy).
3. **Run or replace** `arm64-gate.yml` (or attach equivalent scanner JSON from the device). Zero GitHub runs is not a gate.
4. **Decide emulation policy** (forbidden vs WARN utilities) as part of host-match invariant.
5. **SKU vs Stream G:** owner states whether Windows AMD64 is (a) in-Windows SKU with its own ADR, or (b) parked until Stream G Gate 1. This audit does not choose.
6. **Do not** treat Linux headless or `windows-latest` pytest as GUI ISA proof.
7. PERF Art XV Closed remains operator-owned; dual SKU **multiplies** soak load — do not claim v1.0 dual-ISA GUI quality without a soak plan.

---

## 10. Evidence index

| ID | File | Observation | Interpretation |
|----|------|-------------|----------------|
| E1 | `main.py` L20–22 | `if not is_arm64(): return 1` | Runtime GUI is ARM64-process-only |
| E2 | `detector.py` L23–31 | `is_arm64` = `platform.machine()=="ARM64"` | Not PE; not host-match |
| E3 | `detector.py` L134–148 | Ollama must be ARM64 PE; AMD64 is always fail | Phase 0 helper; forbids native x86-64 Ollama |
| E4 | `scripts/preflight_arm64.py` L156 | Sole caller of Ollama PE validator | Wave 5 did not execute this path in-ledger |
| E5 | `wheel_audit.py` L46–88 | AMD64 filename/PE → `emulated_amd64` | Host assumed ARM64 |
| E6 | `scripts/check_arm64_binaries.py` L137–178 | Any PE ≠ `0xAA64` fails | x86-64 CI cannot use this as a hard gate; conflicts with matrix WARN |
| E7 | `compatibility_matrix.md` L47–50 | aiohttp etc. emulated acceptable | Conflicts with E6 |
| E8 | `WAVE_5_FULL_SYSTEM_VERIFICATION.md` L59–61 | GUI Class B, no screenshots | No ISA fields |
| E9 | `GATE5_WINDOWS_ARM64_GUI_VERIFICATION.md` L9–11 | Operator statement only | Not PE proof |
| E10 | `PERF_BASELINE_REPORT_2026-07-26.md` L9, L33–35 | Linux x86_64; GUI N/A | PERF not ARM64-proven |
| E11 | `PERFORMANCE_CONSTITUTION.md` Art XV | PERF-001–004 not Closed | Soak gap |
| E12 | `TOM_AUDIT_PERF_001_002_FREEZE_CLOSEOUT_2026-08-04.md` L10 | No Win ARM64 soak | Same |
| E13 | GitHub workflow `305048305` | **Total runs 0** | Hard ARM64 CI never executed |
| E14 | `.github/workflows/tests.yml` L19–20, L56–60 | `windows-latest` + scan `continue-on-error` | Headless x86-64 yes; ARM64 PE no |
| E15 | `.github/workflows/package-windows-smoke.yml` L22, L36–41 | PyInstaller on `windows-latest`; file exists only | Ships/builds x64 binary without start test |
| E16 | `packaging/windows/ai_command_center.spec` L54 | `target_arch=None` | Follows builder ISA |
| E17 | `STRATEGIC_GAP_MATRIX.md` Stream G | SKU set undecided; `is_arm64` GUI | Governance: not an unblocked implementation |
| E18 | `adr/README.md` Next free **ADR-026** | Informally Stream D | Do not assume 026 = multi-arch |
| E19 | `requirements.txt` | No ISA markers | Install does not encode SKU |
| E20 | `ui/ui_queue.py` L1, L21–22 | “ARM64-tuned” comment; 16 ms drain | Documentation of intent, not a second ISA fork |

---

## Outcome mapping (A / B / C)

| Outcome | Conditions from charter | This audit |
|---------|-------------------------|------------|
| **A** Low-risk v1.0 | ARM64 proven; contract correct; &lt;1 week; CI enough; no GUI sensitivity | **Fail** — baseline not proven; contract is ARM64-only; CI ARM64 gate unused; GUI soak open |
| **B** v1.1 | ARM64 **proven**; x86-64 still ≥1 week / new infra | **Fail entry condition** — ARM64 ISA proof is incomplete, so B would paper over C |
| **C** Fix baseline first | Partially proven / Unproven; validation gaps; contract wrong/ambiguous | **Match** |

If the owner later attaches a real ARM64 PE/`machine`/Ollama log and reconciles PE policy, **re-open as a B vs A question**. Until then, ADR-026 for multi-arch (or any implementation) is premature.

---

## Owner decision needed

Choose one:

1. **Accept C** — commission ARM64 ISA evidence + PE policy reconciliation (still no x86-64 SKU).
2. **Override C with explicit residual risk** — only the owner can treat Class B GUI attestation as enough for ARM64 v1.0; this audit does not.
3. **Do not** start ADR or implementation for Windows x86-64 on this report alone.

**Next step:** Owner records whether ARM64 v1.0 requires Class A PE evidence. That decision is upstream of any v1.0 vs v1.1 x86-64 roadmap.
