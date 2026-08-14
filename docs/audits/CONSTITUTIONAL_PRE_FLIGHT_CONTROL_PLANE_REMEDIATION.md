# Constitutional Pre-Flight — Control-Plane Remediation

**Date:** 2026-08-12  
**Branch:** `cursor/control-plane-security-remediation-4b28`  
**Authority:** `PROJECT_CONSTITUTION_V4.md`; ADR-004, ADR-009, ADR-018; Inv 12 (non-circumvention)

## Scope

Remediate live control-plane defects identified in `CONTROL_PLANE_SECURITY_AUDIT.md`:

1. Remove EA unconditional `auto_approve`
2. Orchestrator approval gate ignores `auto_approve` bypass; high-risk UI shell requires HITL
3. Non-spoofable actor identity via `core/control_plane.py`
4. `interactive_user` stamp required for trusted `user` shell privilege
5. Sandbox blocks `python -c` / `--command`

## Verification

- `tests/test_control_plane_security_acceptance.py` — 19 passed (xfail removed)
- Full `pytest -m "not slow"` — green
- UCGS / constitution / arch_lint — green
