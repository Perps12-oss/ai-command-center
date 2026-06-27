# Release Notes — vX.Y.Z

## Summary

Brief one-paragraph summary of the release, including the primary user-facing goal and any architectural milestones.

## New Features

- Feature or capability added in this release.
- Link to the phase or task document that introduced it.

## Improvements

- Performance, reliability, or UX improvement.
- Architectural hardening that is visible to operators or maintainers.

## Bug Fixes

- Issue fixed and the behavior before/after the fix.
- Reference to the regression test or gate that now passes.

## Upgrade Instructions

1. Pull the release tag:
   ```powershell
   git fetch origin
   git checkout vX.Y.Z
   ```
2. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. Upgrade dependencies:
   ```powershell
   python -m pip install -U pip
   pip install -r requirements.txt
   ```
4. Run the ARM64 preflight on the target device:
   ```powershell
   python scripts/preflight_arm64.py
   ```
5. Run the daily driver smoke test:
   ```powershell
   python scripts/run_daily_driver.py
   ```
6. Start the application normally:
   ```powershell
   python main.py
   ```

## Rollback Instructions

1. Stop the application.
2. Revert to the previous production tag:
   ```powershell
   git checkout vPREVIOUS.TAG
   ```
3. Re-install dependencies and re-run the preflight:
   ```powershell
   pip install -r requirements.txt
   python scripts/preflight_arm64.py
   ```
4. Restart the application.
5. If the rollback is due to a constitutional or contract violation, open an architectural exception record (AER) before re-releasing.

## Known Issues

- Known issue or limitation, with a workaround if available.
- Link to the deferred work item or issue tracker entry.

## Dependencies

- Dependency updates or compatibility notes.
- ARM64 vs. emulated wheel policy notes (see `compatibility_matrix.md`).

## Governance

- Constitutional review: [link to review document]
- Phase ledger: [link to `docs/PHASE_LEDGER.md`]
- Release checklist: [link to `docs/RELEASE_CHECKLIST.md`]
- CI artifacts: [link to GitHub Actions artifacts or release attachments]
