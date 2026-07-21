[CmdletBinding()]
param(
    [int]$RestartDelaySeconds = 10
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$workerPath = Join-Path $root "apps\worker"
$pythonPath = Join-Path $workerPath ".venv\Scripts\python.exe"
$workerEnv = Join-Path $workerPath ".env"
$logDirectory = Join-Path $env:LOCALAPPDATA "PdfAiAgent\logs"
$launcherLog = Join-Path $logDirectory "launcher.log"
$workerLog = Join-Path $logDirectory "worker.log"
$workerOutputLog = Join-Path $logDirectory "worker-output.log"

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

function Write-LauncherLog {
    param([Parameter(Mandatory)][string]$Message)

    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
    Add-Content -LiteralPath $launcherLog -Value "$timestamp $Message"
}

function Test-Ollama {
    try {
        $response = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
        return $response
    } catch {
        return $null
    }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No se encontro el Python del worker en: $pythonPath"
}

if (-not (Test-Path -LiteralPath $workerEnv)) {
    throw "No se encontro el archivo de configuracion del worker en: $workerEnv"
}

$existingWorker = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "-m\s+worker\.main" } |
    Select-Object -First 1

if ($existingWorker) {
    Write-LauncherLog "Worker already active with PID $($existingWorker.ProcessId). Launcher exits."
    exit 0
}

$ollama = Test-Ollama
if (-not $ollama) {
    $ollamaCommand = Get-Command "ollama.exe" -ErrorAction SilentlyContinue
    if (-not $ollamaCommand) {
        throw "No se encontro ollama.exe en PATH."
    }

    Write-LauncherLog "Ollama is not active. Starting ollama serve."
    Start-Process -FilePath $ollamaCommand.Source -ArgumentList "serve" -WindowStyle Hidden | Out-Null

    foreach ($attempt in 1..30) {
        Start-Sleep -Seconds 1
        $ollama = Test-Ollama
        if ($ollama) {
            break
        }
    }
}

if (-not $ollama) {
    throw "Ollama no respondio despues de 30 segundos."
}

$modelNames = @($ollama.models | ForEach-Object { $_.name })
foreach ($requiredModel in @("qwen3:8b", "qwen3-vl:4b", "nomic-embed-text:latest")) {
    if ($requiredModel -notin $modelNames) {
        throw "Falta el modelo requerido '$requiredModel'."
    }
}

Write-LauncherLog "Unattended worker supervisor started."
Set-Location -LiteralPath $workerPath

while ($true) {
    try {
        Write-LauncherLog "Starting worker process."

        # Windows PowerShell 5.1 converts text written to native stderr into
        # ErrorRecord objects. Python warnings and normal logging therefore
        # terminated the previous launcher because ErrorActionPreference is Stop.
        # Starting an independent process keeps stderr as plain log output.
        $workerProcess = Start-Process `
            -FilePath $pythonPath `
            -ArgumentList @("-m", "worker.main") `
            -WorkingDirectory $workerPath `
            -RedirectStandardError $workerLog `
            -RedirectStandardOutput $workerOutputLog `
            -WindowStyle Hidden `
            -PassThru

        Write-LauncherLog "Worker process started with PID $($workerProcess.Id)."
        $workerProcess.WaitForExit()
        $exitCode = $workerProcess.ExitCode
        Write-LauncherLog "Worker stopped with exit code $exitCode. Restarting in $RestartDelaySeconds seconds."
    } catch {
        Write-LauncherLog "Worker launcher error: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $RestartDelaySeconds
}
