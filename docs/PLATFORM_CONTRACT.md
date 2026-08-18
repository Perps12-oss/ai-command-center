# Platform contract — Windows ARM64 two-tier

**Status:** Binding for the Windows ARM64 desktop SKU  
**Code SoT:** `ai_command_center/platform/arm64_policy.py`  
**Evidence:** [`audits/ARM64_ISA_EVIDENCE_2026-08-16.md`](audits/ARM64_ISA_EVIDENCE_2026-08-16.md)

## Invariant

On the supported product host:

| Layer | Required |
|-------|----------|
| Host OS | Windows ARM64 |
| ACC process | Native ARM64 Python (`platform.machine()==ARM64` and `python.exe` PE `0xAA64`) |
| Ollama | PE `0xAA64` (HTTP is not a substitute) |
| Inference-critical wheels | Native ARM64 if installed |
| Utility wheels on the allowlist | AMD64 PE permitted |
| Any other PE | FAIL |

Host ISA must match the **process**. Whitelisting both `0xAA64` and `0x8664` globally is **forbidden** (that would allow emulated Ollama on ARM64).

## Core (native ARM64 only)

- Python interpreter used to launch `main.py`
- `ollama.exe`
- `PERFORMANCE_CRITICAL_PACKAGES` in `arm64_policy.py` (whisper/TTS/screenpipe if installed)

## Allowlist (emulation permitted)

`ALLOWLIST_EMULATION` in `arm64_policy.py`: aiohttp (+ yarl, multidict, frozenlist, propcache), watchdog, pywin32, psutil, pyyaml, Pillow.

New dependencies default to **FAIL** if they ship AMD64 PE. Do not add to the allowlist without an ISA evidence row (PE + why + runtime impact).

## Enforcement

| Tool | Role |
|------|------|
| `main.py` `is_arm64()` | Runtime process gate |
| `validate_ollama_arm64_native()` | Phase 0 Ollama PE |
| `scripts/check_arm64_binaries.py` | Env PE scan, two-tier (skips CPython/pip toolchain noise; still FAILs `python.exe` / site-packages) |
| `wheel_audit.py` | Phase 0 package rows |
| `.github/workflows/arm64-gate.yml` | CI on `windows-11-arm` |
