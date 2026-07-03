# Packaging (Track 6)

Platform build stubs for Windows P0. Full design: [docs/architecture/PACKAGING_MSI_DESIGN.md](../docs/architecture/PACKAGING_MSI_DESIGN.md).

## Prerequisites

- Windows 10/11
- Python 3.11+ with project dev dependencies
- `pip install pyinstaller` (not yet in pyproject optional deps — add in P0 build PR)
- **MSI only:** [WiX Toolset v3.11+](https://wixtoolset.org/) (`heat.exe`, `candle.exe`, `light.exe` on PATH)

## P0 — PyInstaller one-folder

```powershell
pip install -r requirements.txt -r requirements-test.txt pyinstaller
python scripts/build_windows.py
# Output: dist/AICommandCenter/AICommandCenter.exe
```

CI: `.github/workflows/package-windows-smoke.yml` (unsigned artifact upload).

## P0 — MSI via WiX (unsigned local / CI smoke)

1. Build PyInstaller output (above)
2. Run the MSI script (harvests `dist/AICommandCenter`, compiles `packaging/windows/Product.wxs`):

```powershell
.\scripts\build_msi.ps1
# Output: dist/AICommandCenter.msi (unsigned)
```

Generated at build time (do not commit): `packaging/windows/AppHarvest.wxs`, `build/wix/*.wixobj`.

### Authenticode signing (release only — not in repo)

Signing keys live in CI secret store / HSM. P0 CI produces **unsigned** artifacts.

```powershell
# Sign the main executable (optional pre-MSI)
signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com `
  dist\AICommandCenter\AICommandCenter.exe

# Sign the MSI outer cabinet
signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com `
  dist\AICommandCenter.msi
```

Replace `/a` with `/f cert.pfx /p password` when using a PFX from your secret store.

## macOS / Linux

Deferred — see PACKAGING_MSI_DESIGN.md § macOS / Linux deferral.
