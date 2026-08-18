# Constitutional Pre-Flight — ARM64 gate CPython toolchain scan scope

**Date:** 2026-08-18  
**Authority:** Article X; `docs/PLATFORM_CONTRACT.md`; existing two-tier close-out pre-flight.  
**Trigger:** PR #198 `arm64-gate` on `windows-11-arm` failed the PE scan (exit 1) after the runner **did** provision.

## What this change is

Narrow `scripts/check_arm64_binaries.py` so the env scan does not FAIL on CPython/pip **distribution** PE that ACC never loads (installer SFX, pip distlib cross-arch helpers, tcl nmake helper, prefix `vcruntime140_1.dll`). Keep FAIL for `python.exe` / `python*.dll` and for non-allowlisted AMD64 PE under site-packages.

## What this change is not

- Not switching `arm64-gate.yml` to `windows-latest`.
- Not implementing an x86-64 SKU.
- Not expanding `ALLOWLIST_EMULATION`.
- Not tagging v1.0 or merging PR #198.

## Evidence (CI)

Job `Native ARM64 verification` run `32196710055` on `windows-11-arm`, Python `3.12.10` arm64 toolcache. Interpreter check passed (`platform.machine()==ARM64`). Scan offenders were all under `C:\hostedtoolcache\windows\Python\3.12.10\arm64\` (installer exe, `vcruntime140_1.dll`, pip distlib `t32/t64/w32/w64.exe`, tcl nmake helper).

## Invariants

No EventBus/UI/storage changes. Two-tier allowlist unchanged. Core process PE must still be `0xAA64`.
