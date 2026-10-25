# ARM64 Compatibility Matrix

**Policy SoT:** [`docs/PLATFORM_CONTRACT.md`](docs/PLATFORM_CONTRACT.md) and `ai_command_center/platform/arm64_policy.py`  
**Evidence:** [`docs/audits/ARM64_ISA_EVIDENCE_2026-08-16.md`](docs/audits/ARM64_ISA_EVIDENCE_2026-08-16.md)

Two-tier: **core native ARM64**; **allowlisted utilities may be AMD64 PE**. Non-allowlisted AMD64 **FAIL** (scanner and wheel_audit).

Last verified (operator desktop): 2026-08-16. Refresh locally with `python scripts/preflight_arm64.py`.

## Legend

| Column | Meaning |
|--------|---------|
| ARM64 Native | `win_arm64` wheel, native PE `0xAA64`, or pure Python |
| Emulated | `win_amd64` PE on ARM64 Windows (allowlist only) |
| Unknown | Not installed or arch undetected |

## Python runtime

| Component | ARM64 Native | Emulated | Notes |
|-----------|:------------:|:--------:|-------|
| Python 3.14 (`pythoncore-3.14-64`) | ✓ | | Operator 2026-08-16 |
| Python on PATH (`python`) | | ✓ | Often x64-emulated; **do not use** |

## Core / inference (FAIL if emulated)

| Package | ARM64 Native | Emulated | Notes |
|---------|:------------:|:--------:|-------|
| Ollama (`ollama.exe`) | ✓ | | PE `0xAA64` required; HTTP alone insufficient |
| faster-whisper / whisper / TTS / screenpipe | | | Not installed; FAIL if emulated when added |

## Application stack

| Package | ARM64 Native | Emulated | Gate |
|---------|:------------:|:--------:|------|
| psutil | | ✓ | Allowlist PASS |
| pyyaml | | ✓ | Allowlist PASS |
| Pillow | | ✓ | Allowlist PASS |
| aiohttp + yarl/multidict/frozenlist/propcache | | ✓ | Allowlist PASS |
| pywin32 | | ✓ | Allowlist PASS |
| watchdog | ✓ / n/a | | Operator: pure Python; AMD64 PE still allowlisted if present |
| customtkinter, CTkMessagebox, mistune, keyboard, pystray | ✓ | | Pure Python |

## Policy summary

```text
Process + Ollama + inference-critical → FAIL if not ARM64 native
ALLOWLIST_EMULATION in arm64_policy.py → PASS if AMD64 PE
Any other AMD64 PE                     → FAIL
```
