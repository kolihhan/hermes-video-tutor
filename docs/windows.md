# Windows

The Windows path is intentionally project-local. Setup writes only under `.run/`; it does not change the machine-wide PowerShell execution policy or the user's global Hermes profile.

## Prerequisites

- Windows 10/11
- `git`
- `uv`
- `ffmpeg`
- Ollama running locally with `qwen3.5:4b`

## Setup

From PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-hermes.ps1
```

The script fetches only the pinned full Hermes Agent revision recorded in
`hermes.lock`, excludes non-runtime contributor metadata that collides on
case-insensitive Windows filesystems, verifies a clean checkout, creates
project-local Hermes/app virtual environments, and copies
`config/hermes-project.yaml` to `.run/hermes-home/config.yaml`. It then verifies
the base `qwen3.5:4b` tag, creates `qwen3.5-hermes:4b` from
`Modelfile.hermes`, and verifies the custom tag.
The custom tag and project-local Hermes profile both declare a 65,536-token
context, the minimum accepted by the pinned Hermes runtime.

## Run

Double-click or run:

```cmd
run-demo.cmd
```

For a CLI question instead of Streamlit:

```cmd
run-demo.cmd -Cli -Question "What are the three stages of the tutor pipeline?"
```

`run-demo.cmd` uses `-ExecutionPolicy Bypass` for that PowerShell process only. It does not call `Set-ExecutionPolicy`.

## Live acceptance

The repository's automated tests validate script contracts and the Python/video-tool layers. The frozen real Windows + Ollama + Hermes evaluation is:

```powershell
.run\app-venv\Scripts\python.exe -m evaluation.run_live_paired --output runs\p3-live-paired-v1\report.json
```

It runs 12 cases in both tool conditions, sequentially, and refuses to
overwrite an existing report. Do not rerun a valid canonical artifact.
