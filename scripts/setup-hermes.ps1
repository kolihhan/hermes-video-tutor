[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$RunRoot = Join-Path $RepoRoot '.run'
$HermesCheckout = Join-Path $RunRoot 'hermes-agent'
$HermesVenv = Join-Path $RunRoot 'hermes-venv'
$AppVenv = Join-Path $RunRoot 'app-venv'
$HermesHome = Join-Path $RunRoot 'hermes-home'
$HermesRepo = 'https://github.com/NousResearch/hermes-agent.git'
$HermesRelease = 'v0.20.4'
$HermesCommit = '8911e2e0edf750b104edbdc106d63d6cdac88524'
$ProjectConfig = Join-Path $RepoRoot 'config\hermes-project.yaml' # config/hermes-project.yaml

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    $ResolvedCommand = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $ResolvedCommand) {
        throw "Required command '$Name' was not found on PATH."
    }
}

foreach ($CommandName in @('git', 'uv', 'ffmpeg', 'ollama')) {
    Require-Command $CommandName
}

New-Item -ItemType Directory -Force $RunRoot, $HermesHome | Out-Null

if (-not (Test-Path (Join-Path $HermesCheckout '.git'))) {
    if (Test-Path $HermesCheckout) {
        Remove-Item -Recurse -Force $HermesCheckout
    }
    New-Item -ItemType Directory -Force $HermesCheckout | Out-Null
    & git -C $HermesCheckout init
    if ($LASTEXITCODE -ne 0) { throw 'Failed to initialize the project-local Hermes checkout.' }
    & git -C $HermesCheckout remote add origin $HermesRepo
    if ($LASTEXITCODE -ne 0) { throw 'Failed to configure the Hermes Agent remote.' }
}
else {
    & git -C $HermesCheckout remote set-url origin $HermesRepo
    if ($LASTEXITCODE -ne 0) { throw 'Failed to verify the Hermes Agent remote.' }
}

& git -C $HermesCheckout fetch --depth 1 --filter=blob:none origin $HermesCommit
if ($LASTEXITCODE -ne 0) { throw 'Failed to fetch the pinned Hermes Agent revision.' }
& git -C $HermesCheckout checkout --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Failed to checkout pinned Hermes commit $HermesCommit ($HermesRelease)." }
& git -C $HermesCheckout sparse-checkout set --no-cone '/*' '!/contributors/'
if ($LASTEXITCODE -ne 0) { throw 'Failed to exclude non-runtime contributor metadata from the Windows checkout.' }
& git -C $HermesCheckout sparse-checkout reapply
if ($LASTEXITCODE -ne 0) { throw 'Failed to apply the project-local Hermes sparse checkout.' }
$ResolvedHermesCommit = (& git -C $HermesCheckout rev-parse HEAD).Trim()
if (-not $ResolvedHermesCommit.Equals($HermesCommit, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Hermes revision mismatch: expected $HermesCommit, got $ResolvedHermesCommit."
}
$HermesStatus = (& git -C $HermesCheckout status --porcelain | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $HermesStatus) {
    throw 'Project-local Hermes checkout is not clean after setup.'
}

if (-not (Test-Path (Join-Path $HermesVenv 'Scripts\python.exe'))) {
    & uv venv --python 3.11 $HermesVenv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create the project-local Hermes virtual environment.' }
}
$HermesPython = Join-Path $HermesVenv 'Scripts\python.exe'
& uv pip install --python $HermesPython -e "$HermesCheckout[all]"
if ($LASTEXITCODE -ne 0) { throw 'Failed to install the pinned Hermes checkout.' }

Copy-Item -Force $ProjectConfig (Join-Path $HermesHome 'config.yaml')
$env:HERMES_HOME = $HermesHome

$PreviousProjectEnvironment = $env:UV_PROJECT_ENVIRONMENT
try {
    $env:UV_PROJECT_ENVIRONMENT = $AppVenv
    Push-Location $RepoRoot
    try {
        & uv sync --extra ui --extra dev
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create the project application environment.' }
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:UV_PROJECT_ENVIRONMENT = $PreviousProjectEnvironment
}

$OllamaModels = (& ollama list | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw 'Ollama is installed but its local server could not be queried. Start Ollama and rerun setup.'
}
if ($OllamaModels -notmatch '(?im)^qwen3\.5:4b\s') {
    throw "Required model qwen3.5:4b is not installed. Run: ollama pull qwen3.5:4b"
}

& ollama create qwen3.5-hermes:4b -f (Join-Path $RepoRoot 'Modelfile.hermes')
if ($LASTEXITCODE -ne 0) { throw 'Failed to create qwen3.5-hermes:4b from Modelfile.hermes.' }
$CreatedModels = (& ollama list | Out-String)
if ($LASTEXITCODE -ne 0 -or $CreatedModels -notmatch '(?im)^qwen3\.5-hermes:4b\s') {
    throw 'Created Hermes model qwen3.5-hermes:4b was not found after ollama create.'
}

Write-Host "Hermes Video Tutor setup complete."
Write-Host "Pinned Hermes: $ResolvedHermesCommit ($HermesRelease)"
Write-Host "Project state: $RunRoot"
