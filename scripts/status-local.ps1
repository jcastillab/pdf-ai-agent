[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Test-HttpEndpoint {
    param(
        [Parameter(Mandatory)][string]$Url,
        [int]$TimeoutSeconds = 4
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds
        return [pscustomobject]@{
            Active = $response.StatusCode -ge 200 -and $response.StatusCode -lt 400
            Detail = "HTTP $($response.StatusCode)"
        }
    } catch {
        return [pscustomobject]@{
            Active = $false
            Detail = $_.Exception.Message
        }
    }
}

$results = [System.Collections.Generic.List[object]]::new()

$api = Test-HttpEndpoint "http://127.0.0.1:8000/api/v1/health"
$results.Add([pscustomobject]@{
    Service = "FastAPI"
    State = if ($api.Active) { "ACTIVE" } else { "STOPPED" }
    Address = "http://127.0.0.1:8000"
    Detail = $api.Detail
})

$frontend = Test-HttpEndpoint "http://localhost:4200"
$results.Add([pscustomobject]@{
    Service = "Angular"
    State = if ($frontend.Active) { "ACTIVE" } else { "STOPPED" }
    Address = "http://localhost:4200"
    Detail = $frontend.Detail
})

try {
    $ollama = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 4
    $modelNames = @($ollama.models | ForEach-Object { $_.name })
    $ollamaActive = $true
    $ollamaDetail = "$($modelNames.Count) models: $($modelNames -join ', ')"
} catch {
    $ollamaActive = $false
    $ollamaDetail = $_.Exception.Message
}

$results.Add([pscustomobject]@{
    Service = "Ollama"
    State = if ($ollamaActive) { "ACTIVE" } else { "STOPPED" }
    Address = "http://127.0.0.1:11434"
    Detail = $ollamaDetail
})

$worker = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "-m\s+worker\.main" } |
    Select-Object -First 1

$results.Add([pscustomobject]@{
    Service = "Worker"
    State = if ($worker) { "ACTIVE" } else { "STOPPED" }
    Address = "local process"
    Detail = if ($worker) { "PID $($worker.ProcessId)" } else { "worker.main was not found" }
})

$results | Format-Table -AutoSize -Wrap

$stopped = @($results | Where-Object { $_.State -ne "ACTIVE" })
if ($stopped.Count -gt 0) {
    Write-Warning "$($stopped.Count) service(s) are not active."
    exit 1
}

Write-Host "All local services are active." -ForegroundColor Green
