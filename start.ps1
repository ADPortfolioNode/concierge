<#
.SYNOPSIS
  PowerShell wrapper to start the development compose environment on Windows.

Usage: .\start.ps1 [--prune] [--yes] [--build] [--diag] [--log] [--frontend|--no-frontend] [--clear]
#>

Param(
    [switch]$prune,
    [switch]$yes,
    [switch]$build,
    [switch]$diag,
    [switch]$log,
    [switch]$frontend = $true,
    [switch]$noFrontend,
    [switch]$clear
)

function Die($msg){ Write-Error $msg; exit 1 }

function Clear-KnownPorts {
    $ports = 8000,8001,5173,6333
    foreach ($p in $ports) {
        Write-Host "Checking port $p"
        try {
            $matches = & netstat -ano | Select-String ":$p" | ForEach-Object {
                $_.ToString().Trim() -split '\s+' | Select-Object -Last 1
            }
            foreach ($pid in $matches | Where-Object { $_ -match '^[0-9]+$' }) {
                try {
                    Write-Host "Stopping process $pid listening on port ${p}"
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                } catch {
                    Write-Warning "Could not stop process $pid for port ${p}: $($_)"
                }
            }
        } catch {
            Write-Warning "Failed to inspect port ${p}: $($_)"
        }
    }
}

function Show-PortStatus {
    $ports = 8000,8001,5173,6333
    Write-Host "Inspecting port usage for known service ports..."
    foreach ($p in $ports) {
        Write-Host "--- port $p ---"
        try {
            & netstat -ano | Select-String ":$p" | ForEach-Object {
                $_.ToString().Trim()
            }
        } catch {
            Write-Warning "Cannot inspect port $p: $($_)"
        }
    }
}

# support --no-frontend
if ($noFrontend) { $frontend = $false }

Write-Host "Running start.ps1 with options:`n  prune=$prune build=$build diag=$diag log=$log frontend=$frontend clear=$clear"

# check docker
try { docker version | Out-Null } catch { Die "docker CLI not found; please install Docker and ensure the daemon is running." }

function Compose($argString){
    # invoke `docker compose` by calling `docker` with the 'compose' subcommand
    $parts = @('compose') + ($argString -split ' ')
    try { & docker @parts } catch { Die "Failed to run: docker $argString" }
}

if ($prune) {
    if ($yes -or (Read-Host "Prune docker system (containers/images/networks/volumes)? [y/N]" ) -match '^[Yy]'){
        Write-Host "Pruning docker system..."
        try { docker system prune -af } catch { Write-Warning "prune failed, continuing" }
    } else { Write-Host "Skipping prune." }
}

if ($build) { Write-Host "Building containers..."; Compose 'build' }

if ($diag) {
    Write-Host "Writing diagnostics to start.log"
    docker version > start.log 2>&1
    docker-compose version >> start.log 2>&1
    docker ps -a >> start.log 2>&1
}

if ($clear) {
    Write-Host "Clearing environment: compose down; up -d --build"
    Write-Host "Freeing known ports before tear down/start"
    Clear-KnownPorts
    Compose 'down' | Out-Null
    if ($build) { Compose 'up -d --build' } else { Compose 'up -d --build' }
} else {
    Write-Host "Freeing known ports before tear down/start"
    Clear-KnownPorts
    Write-Host "Ensuring any existing services are stopped (compose down)"
    Compose 'down' | Out-Null
    if ($build) { Write-Host "Building containers before start..."; Compose 'build' }
    Write-Host "Starting services with compose up -d"
    Compose 'up -d' | Out-Null
}

if ($log) {
    Write-Host "Writing service logs to start.log"
    "--- compose logs (snapshot) ---" | Out-File -FilePath start.log -Encoding utf8 -Append
    # include both backend and frontend services
    docker compose logs --no-color --timestamps app frontend | Out-File -FilePath start.log -Encoding utf8 -Append
}

if ($frontend) {
    Write-Host "Starting frontend container"
    Compose 'up -d frontend' | Out-Null
    if ($log) {
        Write-Host "Appending backend+frontend logs to start.log"
        docker compose logs --no-color app frontend | Out-File -FilePath start.log -Encoding utf8 -Append
    }
    # check for unexpected exits
    $ps = docker compose ps | Select-String -Pattern 'quesarc_app.*Exited','quesarc_frontend.*Exited'
    if ($ps) {
        Write-Host "One or more containers exited unexpectedly; see logs above" -ForegroundColor Yellow
        Show-PortStatus
    }
}

Write-Host "start.ps1 completed. Use 'docker ps' to inspect running containers."
