# ARM64 Compatibility Matrix

Tracked during Phase 0 preflight. Policy: **performance-critical inference** packages must be native ARM64; utility packages may run emulated with a WARN.

Last verified: run `python scripts/preflight_arm64.py` to refresh.

## Legend

| Column | Meaning |
|--------|---------|
| ARM64 Native | `win_arm64` wheel or pure Python |
| Emulated | `win_amd64` binary on ARM64 Windows |
| Unknown | Not installed or arch undetected |

## Python runtime

| Component | ARM64 Native | Emulated | Unknown | Notes |
|-----------|:------------:|:--------:|:-------:|-------|
| Python 3.14 (recommended) | ✓ | | | `C:\Users\S8633\AppData\Local\Python\bin\python.exe` |
| Python on PATH (`python`) | | ✓ | | Often x64-emulated; **do not use** |

## Inference / AI (hard fail if emulated)

| Package | ARM64 Native | Emulated | Unknown | Notes |
|---------|:------------:|:--------:|:-------:|-------|
| Ollama (`ollama.exe`) | ✓ | | | PE `0xAA64` required; HTTP alone insufficient |
| faster-whisper | | | ? | Phase 6 — not installed |
| whisper | | | ? | Phase 6 — not installed |
| XTTS / TTS | | | ? | Phase 6 — not installed |
| Screenpipe | | | ? | Future plugin — not installed |

## Application stack (`requirements.txt`)

| Package | ARM64 Native | Emulated | Unknown | Gate |
|---------|:------------:|:--------:|:-------:|------|
| psutil | ✓ | | | Critical Phase 0 |
| pyyaml | ✓ | | | Critical Phase 0 |
| customtkinter | ✓ | | | Optional — WARN if missing |
| CTkMessagebox | ✓ | | | Optional — pure Python |
| Pillow | ✓ | | | Optional |
| mistune | ✓ | | | Optional — pure Python |
| keyboard | ✓ | | | Optional — pure Python |
| pystray | ✓ | | | Optional — pure Python |
| aiohttp | | ✓ | | Optional — emulated `.pyd`; acceptable |
| yarl | | ✓ | | Transitive — emulated |
| multidict | | ✓ | | Transitive — emulated |
| frozenlist | | ✓ | | Transitive — emulated |
| propcache | | ✓ | | Transitive — emulated |
| watchdog | | ✓ | | Optional — emulated; acceptable |
| pywin32 | | ✓ | | Optional — emulated; acceptable |

## Policy summary

```text
Inference-critical (Ollama, Whisper, XTTS, Screenpipe) → FAIL if not ARM64 native
Utility / I/O (aiohttp, watchdog, pywin32, pyyaml)     → WARN if emulated, do not block Phase 0
```

## Baseline log

Phase 0 requires `baseline.json` at:

```text
%APPDATA%\AICommandCenter\baseline.json
```

Generate with:

```powershell
C:\Users\S8633\AppData\Local\Python\bin\python.exe scripts\benchmark_startup.py
```

## Maintenance

- Single source of truth for versions: `requirements.txt`
- Validation tiers live in `ai_command_center/platform/wheel_audit.py`:
  - `CRITICAL_PHASE0_DEPS`
  - `OPTIONAL_DEPS`
  - `PERFORMANCE_CRITICAL_PACKAGES`
- Update this matrix when adding packages or changing phases.
