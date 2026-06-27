# Release Checklist

## Versioning and Tagging Policy

- Release versions follow `v<MAJOR>.<MINOR>.<PATCH>` (SemVer).
- Release candidates are tagged `vX.Y.Z-rcN` (e.g., `v1.0.0-rc1`).
- Production drops are tagged `vX.Y.Z` (e.g., `v1.0.0`).
- Phase completion tags follow `phase-N-complete-YYYYMMDD`.
- The latest phase completion tag is recorded in `docs/PHASE_LEDGER.md`.

## Pre-release Checklist

1. **Update the phase ledger** — record the current phase as complete and tag the snapshot.
2. **Run all governance gates**:
   - `python scripts/verify_constitution.py`
   - `python scripts/verify_contracts.py`
3. **Run all phase gates**:
   - `python scripts/verify_phase1.py`
   - `python scripts/verify_phase2.py`
   - `python scripts/verify_phase3a.py`
   - `python scripts/verify_phase3b.py`
   - `python scripts/verify_phase3c.py`
   - `python scripts/verify_phase3d.py`
   - `python scripts/verify_phase4a.py`
   - `python scripts/verify_phase4b.py`
   - `python scripts/verify_phase4c.py`
   - `python scripts/verify_phase4d.py`
   - `python scripts/verify_phase4e.py`
   - `python scripts/verify_phase4f.py`
   - `python scripts/verify_phase5a.py`
   - `python scripts/verify_phase5b.py`
   - `python scripts/verify_phase5c.py`
   - `python scripts/verify_phase5c_telemetry.py`
   - `python scripts/verify_capability_completion.py`
4. **Run the full unit test suite**:
   - `python -m unittest discover -s tests -v`
5. **Run the architecture enforcement kit**:
   - `python tools/ucgs_runner.py > ucgs_report.yaml`
   - `python tools/ucgs_ci_gate.py ucgs_report.yaml`
6. **Prepare release notes** from `docs/RELEASE_NOTES_TEMPLATE.md`.
7. **Ensure no uncommitted source changes** except release metadata and documentation.
8. **Run the ARM64 preflight on target hardware**:
   - `python scripts/preflight_arm64.py`
9. **Run the daily driver smoke test**:
   - `python scripts/run_daily_driver.py`
10. **Capture evidence** — scorecard, preflight output, and UC GS report.

## Build and Tag

1. Commit the release metadata and release notes.
2. Create an annotated tag:
   - `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
3. Push the tag and commit:
   - `git push origin main --tags`
4. Create a GitHub release from the tag.
5. Attach CI artifacts (UC GS report, scorecard, preflight evidence).

## Rollback Policy

1. If the release candidate fails smoke testing, immediately revert to the previous production tag.
2. Preserve contract-compatible event payloads during rollback.
3. Re-run `verify_constitution.py`, `verify_contracts.py`, and `preflight_arm64.py` before promoting any replacement candidate.
4. Update `docs/PHASE_LEDGER.md` with the rollback decision and new tag.

## Operator Notes

- The canonical repository is `c:\Users\S8633\Documents\GITHUB\ai-command-center`.
- Runtime data lives in `%APPDATA%\AICommandCenter` and is not version-controlled.
- Do not release from the OneDrive backup copy.
