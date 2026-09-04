[CmdletBinding()]
param(
    [switch]$Cli,
    [string]$Question = 'What color is the highlighted component around 4 seconds?'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunRoot = Join-Path $RepoRoot '.run'
$TempRoot = Join-Path $RunRoot 'tmp'
$HermesHome = Join-Path $RunRoot 'hermes-home'
$HermesScripts = Join-Path $RunRoot 'hermes-venv\Scripts'
$AppPython = Join-Path $RunRoot 'app-venv\Scripts\python.exe'

if (-not (Test-Path $AppPython) -or -not (Test-Path (Join-Path $HermesHome 'config.yaml'))) {
    & (Join-Path $PSScriptRoot 'setup-hermes.ps1')
}

New-Item -ItemType Directory -Force $TempRoot | Out-Null
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:HERMES_HOME = $HermesHome
$env:VIDEO_TUTOR_TOOL_MODE = 'multimodal'
$env:PATH = $HermesScripts + [System.IO.Path]::PathSeparator + $env:PATH

Push-Location $RepoRoot
try {
    if ($Cli) {
        & $AppPython -m video_tutor.cli ask $Question --course (Join-Path $RepoRoot 'demo\course.json')
    }
    else {
        & $AppPython -m streamlit run (Join-Path $RepoRoot 'app.py')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Hermes Video Tutor demo exited with an error.' }
}
finally {
    Pop-Location
}
