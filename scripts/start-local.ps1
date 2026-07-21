[CmdletBinding()]
param(
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$apiPath = Join-Path $root "apps\backend-api"
$frontendPath = Join-Path $root "apps\frontend-angular"
$workerPath = Join-Path $root "apps\worker"

function Assert-Path {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Description)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "No se encontro $Description en: $Path"
    }
}

function Assert-Command {
    param([Parameter(Mandatory)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$Name' en PATH. Instalalo antes de iniciar el proyecto."
    }
}

function Test-ListeningPort {
    param([Parameter(Mandatory)][int]$Port)

    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Start-ServiceTerminal {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][string]$Command
    )

    $safeTitle = $Title.Replace("'", "''")
    $safeDirectory = $WorkingDirectory.Replace("'", "''")
    $terminalScript = @"
`$Host.UI.RawUI.WindowTitle = '$safeTitle'
Set-Location -LiteralPath '$safeDirectory'
$Command
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($terminalScript))
    Start-Process powershell.exe -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-EncodedCommand",
        $encoded
    ) | Out-Null
}

Write-Host "Validando PDF AI Agent..." -ForegroundColor Cyan

Assert-Command "node"
Assert-Command "npm"
Assert-Command "ollama"
Assert-Path (Join-Path $apiPath ".env") "el .env de la API"
Assert-Path (Join-Path $workerPath ".env") "el .env del worker"
Assert-Path (Join-Path $frontendPath "src\assets\config.json") "config.json del frontend"
Assert-Path (Join-Path $apiPath ".venv\Scripts\python.exe") "el entorno virtual de la API"
Assert-Path (Join-Path $workerPath ".venv\Scripts\python.exe") "el entorno virtual del worker"
Assert-Path (Join-Path $frontendPath "node_modules") "node_modules del frontend"

try {
    $ollamaTags = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
} catch {
    throw "Ollama no responde en http://127.0.0.1:11434. Inicia Ollama y vuelve a ejecutar el script."
}

$availableModels = @($ollamaTags.models | ForEach-Object { $_.name })
foreach ($model in @("qwen3:8b", "qwen3-vl:4b", "nomic-embed-text:latest")) {
    if ($model -notin $availableModels) {
        Write-Warning "El modelo '$model' no aparece en Ollama. Modelos detectados: $($availableModels -join ', ')"
    }
}

if (Test-ListeningPort 8000) {
    Write-Host "API ya esta activa en el puerto 8000." -ForegroundColor Yellow
} else {
    Start-ServiceTerminal -Title "PDF AI Agent - API" -WorkingDirectory $apiPath -Command @'
$env:PYTHONPATH = (Get-Location).Path
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
'@
    Write-Host "API iniciada en una terminal nueva." -ForegroundColor Green
}

if (Test-ListeningPort 4200) {
    Write-Host "Angular ya esta activo en el puerto 4200." -ForegroundColor Yellow
} else {
    Start-ServiceTerminal -Title "PDF AI Agent - Angular" -WorkingDirectory $frontendPath -Command "npm start"
    Write-Host "Angular iniciado en una terminal nueva." -ForegroundColor Green
}

$workerRunning = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "-m\s+worker\.main" } |
    Select-Object -First 1

if ($workerRunning) {
    Write-Host "El worker ya esta activo (PID $($workerRunning.ProcessId))." -ForegroundColor Yellow
} else {
    Start-ServiceTerminal -Title "PDF AI Agent - Worker" -WorkingDirectory $workerPath -Command @'
$env:PYTHONPATH = (Get-Location).Path
& .\.venv\Scripts\python.exe -m worker.main
'@
    Write-Host "Worker iniciado en una terminal nueva." -ForegroundColor Green
}

Start-Sleep -Seconds 3

if (-not $SkipBrowser) {
    Start-Process "http://localhost:4200"
    Start-Process "http://127.0.0.1:8000/docs"
}

Write-Host "Inicio solicitado. Revisa las terminales nuevas para confirmar que cada servicio quede activo." -ForegroundColor Cyan
