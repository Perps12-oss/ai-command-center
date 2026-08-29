# ARM64 ISA evidence session (operator protocol)

**Plan:** [`ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md`](ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md) sequence steps 2–3.  
**Script:** `scripts/capture_arm64_isa_evidence.py`  
**Allowlist:** §4.1 — **pending until evidenced**. Do not treat `compatibility_matrix.md` WARN as Allow.

## Who

The **Windows ARM64** desktop that runs product `main.py` (canonical tree). Linux Cloud / x64 CI **cannot** close this session.

## Command

Use the **same interpreter** as `main.py`:

```powershell
cd <canonical-repo>
git rev-parse HEAD
python scripts\capture_arm64_isa_evidence.py --out %APPDATA%\AICommandCenter\isa_evidence.json
python scripts\preflight_arm64.py
```

The capture script also records a preflight subprocess result when `--skip-preflight` is not passed.

Attach `isa_evidence.json` (and preflight stdout if captured separately) to the audit ledger. Do not edit JSON to grant `"policy": "allow"`.

## Required fields (script emits these)

Host env (`PROCESSOR_ARCHITECTURE`, `PROCESSOR_ARCHITEW6432`), `platform.machine()`, `sys.executable`, Python PE, Ollama locate + PE + HTTP, scanner report, wheel-audit rows, git SHA, timestamp, allowlist candidate rows with `policy: pending`.

## After capture

Fill empty `why_emulation_exists` and `runtime_impact` in a ledger addendum **from facts in the JSON** (PE/tags). If a package is already native ARM64 PE, it is **not** an exception. If AMD64 and impact/reason cannot be established, **Deny**.

Then stop. Sequence step 4 (tool reconcile) is a **separate** authorized change.
