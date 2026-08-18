# ARM64 ISA Evidence — 2026-08-16 (operator desktop)

**Class:** B operator ledger (fields supplied for v1.0 close-out; not a Cloud-executed GUI/PE session)  
**Plan:** [`ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md`](ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md) steps 2–3 evidence + step 4 alignment  
**Wave 5 GUI:** [`GATE5_WINDOWS_ARM64_GUI_VERIFICATION.md`](GATE5_WINDOWS_ARM64_GUI_VERIFICATION.md) (2026-08-17 attestation; same SKU)  
**Close-out package tip:** `26df9cd` (this branch). **Release SHA / tag:** only after merge to `main`.

## Environment

| Field | Value |
|-------|--------|
| Timestamp | 2026-08-16 |
| Host OS | Windows ARM64 |
| Python executable | `C:\Users\S8633\AppData\Local\Python\pythoncore-3.14-64\python.exe` |
| `platform.machine()` | ARM64 |
| Ollama | Native ARM64 PE (`0xAA64`) |
| Phase 0 preflight | PASS |

CI ARM64 gate uses GitHub `windows-11-arm` + Python **3.12** ARM64. Operator desktop is Python **3.14** ARM64. Both must remain native ARM64 processes; they are not the same interpreter.

## Two-tier wheel results (operator 2026-08-16)

**Core (native required)**

| Component | Result |
|-----------|--------|
| Python process | Native ARM64 |
| Ollama `ollama.exe` | Native ARM64 PE `0xAA64` |

**Allowlist (AMD64 PE permitted)**

| Package | Result |
|---------|--------|
| psutil | Emulated AMD64 — allowlisted |
| pyyaml | Emulated AMD64 — allowlisted |
| aiohttp (+ transitives in policy module) | Emulated AMD64 — allowlisted |
| Pillow | Emulated AMD64 — allowlisted |
| pywin32 | Emulated AMD64 — allowlisted |

**No PE / pure Python (operator)**

customtkinter, CTkMessagebox, mistune, pystray, keyboard, watchdog

Policy code: `ai_command_center/platform/arm64_policy.py` (includes aiohttp transitives `yarl`, `multidict`, `frozenlist`, `propcache` so the scanner does not FAIL those `.pyd` files).

## What this does not prove

- PERF Art XV soak / GUI frame budgets (remain **Mitigated**, not Closed).
- GitHub `arm64-gate.yml` success (separate CI; see [`ARM64_NATIVE_GATE_RESULTS.md`](ARM64_NATIVE_GATE_RESULTS.md)).
- x86-64 SKU.
