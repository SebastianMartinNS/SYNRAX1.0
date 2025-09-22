param(
    [ValidateSet('start','stop','status','health')]
    [string]$Action = 'start',
    [string]$BindHost = '127.0.0.1',
    [int]$BindPort = 8000,
    [string]$LogLevel = 'info'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ProjectRoot  # scripts/ -> project root
Set-Location $Root

function Get-PythonPath {
    $venvPy = Join-Path $Root 'venv\Scripts\python.exe'
    if (Test-Path $venvPy) { return $venvPy }
    return 'python'
}

function Start-Server {
    $py = Get-PythonPath
    $cmd = "$py -m uvicorn web_new:app --host ${BindHost} --port ${BindPort} --log-level ${LogLevel}"
    $job = Start-Job -ScriptBlock { param($wdir,$cmdline) Set-Location $wdir; Invoke-Expression $cmdline } -ArgumentList $Root,$cmd
    $env:APP_JOBID = $job.Id
    Write-Host "Server avviato come job: $($job.Id)"
    Start-Sleep -Seconds 6
    try {
    $health = Invoke-WebRequest -UseBasicParsing -Uri ("http://${BindHost}:${BindPort}/health") -TimeoutSec 5
        Write-Host "Health: $($health.Content)"
    } catch {
        Write-Warning "Health check fallito: $($_.Exception.Message)"
    }
}

function Stop-Server {
    if ($env:APP_JOBID) {
        try {
            Stop-Job -Id $env:APP_JOBID -ErrorAction SilentlyContinue
            Receive-Job -Id $env:APP_JOBID -Keep | Out-Null
            Remove-Job -Id $env:APP_JOBID -Force -ErrorAction SilentlyContinue
            Write-Host "Server job fermato: $($env:APP_JOBID)"
            Remove-Item Env:APP_JOBID -ErrorAction SilentlyContinue
        } catch {
            Write-Warning "Impossibile fermare il job: $($_.Exception.Message)"
        }
    } else {
        Write-Host 'Nessun job registrato in $env:APP_JOBID.'
    }
    # Kill any process listening on the configured port as a fallback
    try {
        $line = netstat -ano | Select-String -Pattern ":${BindPort}\s+LISTENING" | Select-Object -First 1
        if ($line) {
            $pid = ($line.ToString().Trim() -split '\s+')[-1]
            if ($pid -match '^[0-9]+$') {
                Write-Warning "Terminazione forzata del processo PID=$pid sulla porta ${BindPort}"
                Stop-Process -Id [int]$pid -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Warning "Cleanup porta ${BindPort} fallito: $($_.Exception.Message)"
    }
}

function Status-Server {
    if ($env:APP_JOBID) {
        try {
            $job = Get-Job -Id $env:APP_JOBID -ErrorAction Stop
            Write-Host "Job: $($job.Id) Stato: $($job.State)"
        } catch {
            Write-Warning "Job non trovato o già terminato."
        }
    } else {
        Write-Host 'Nessun job registrato.'
    }
    # Porta in ascolto?
    $listening = netstat -ano | Select-String -Pattern ":${BindPort}\s+LISTENING" | Select-Object -First 1
    if ($listening) { Write-Host "Porta ${BindPort}: LISTENING" } else { Write-Host "Porta ${BindPort}: non in ascolto" }
}

function Health-Server {
    try {
    $resp = Invoke-WebRequest -UseBasicParsing -Uri ("http://${BindHost}:${BindPort}/health") -TimeoutSec 5
        Write-Host $resp.Content
    } catch {
        Write-Warning "Health check fallito: $($_.Exception.Message)"
    }
}

switch ($Action) {
    'start'  { Start-Server }
    'stop'   { Stop-Server }
    'status' { Status-Server }
    'health' { Health-Server }
    default  { Start-Server }
}
