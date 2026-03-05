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
    Compose 'down' | Out-Null
    if ($build) { Compose 'up -d --build' } else { Compose 'up -d --build' }
} else {
    Write-Host "Ensuring any existing services are stopped (compose down)"
    Compose 'down' | Out-Null
    if ($build) { Write-Host "Building containers before start..."; Compose 'build' }
    Write-Host "Starting services with compose up -d"
    Compose 'up -d' | Out-Null
}

if ($log) {
    Write-Host "Writing service logs to start.log"
    "--- compose logs (snapshot) ---" | Out-File -FilePath start.log -Encoding utf8 -Append
    docker compose logs --no-color --timestamps | Out-File -FilePath start.log -Encoding utf8 -Append
}

if ($frontend) {
    Write-Host "Starting frontend container"
    Compose 'up -d frontend' | Out-Null
    if ($log) {
        Write-Host "Appending frontend logs to start.log"
        docker compose logs --no-color frontend | Out-File -FilePath start.log -Encoding utf8 -Append
    }
}

Write-Host "start.ps1 completed. Use 'docker ps' to inspect running containers."
