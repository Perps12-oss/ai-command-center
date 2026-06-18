# AI Command Center

Phase 0 preflight scaffold for a local AI command surface on **Windows ARM64**.

## Project home

`c:\Users\S8633\OneDrive\Desktop\ai-command-center`

## Target hardware

- Lenovo 83N3, Snapdragon X, 16 GB RAM
- **Native ARM64 Python required** — the default `python` on PATH may be x64-emulated (`platform.machine()` reports `AMD64`).

Recommended interpreter:

```powershell
C:\Users\S8633\AppData\Local\Python\bin\python.exe
```

Runtime application data (not in repo): `%APPDATA%\AICommandCenter`

## Setup

```powershell
cd c:\Users\S8633\OneDrive\Desktop\ai-command-center
C:\Users\S8633\AppData\Local\Python\bin\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
python scripts\preflight_arm64.py
```

## Phase 0 layout

- `scripts/preflight_arm64.py` — environment checks
- `scripts/benchmark_startup.py` — cold-start stub
- `ai_command_center/platform/detector.py` — platform probes
- `main.py` — entry stub (Phase 1+)

## GitHub

Authenticated `gh` users can publish with:

```powershell
gh repo create ai-command-center --private --source=. --remote=origin --push
```
