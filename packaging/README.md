# Packaging (Track 6)

Platform build stubs for Windows P0. Full design: [docs/architecture/PACKAGING_MSI_DESIGN.md](../docs/architecture/PACKAGING_MSI_DESIGN.md).

## Prerequisites

- Windows 10/11
- Python 3.11+ with project dev dependencies
- `pip install pyinstaller` (not yet in pyproject optional deps — add in P0 build PR)

## P0 — PyInstaller one-folder

```powershell
pip install -r requirements.txt -r requirements-test.txt pyinstaller
python scripts/build_windows.py
# Output: dist/AICommandCenter/AICommandCenter.exe
```

CI: `.github/workflows/package-windows-smoke.yml` (unsigned artifact upload).

## P0 — MSI via WiX (not implemented)

1. Build PyInstaller output (above)
2. Harvest `dist/AICommandCenter` with WiX `heat.exe` or manual `File` entries
3. `candle` + `light` → `AICommandCenter.msi`
4. Optional: `signtool sign` with Authenticode cert from secret store

See commented template in `packaging/windows/ai_command_center.spec`.

## macOS / Linux

Deferred — see PACKAGING_MSI_DESIGN.md § macOS / Linux deferral.
