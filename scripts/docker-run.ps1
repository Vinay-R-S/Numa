param(
    [switch]$NoNgrok,
    [switch]$Down,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ComposeFile = Join-Path $RepoRoot "docker-compose.yml"
$ServerEnv = Join-Path $RepoRoot "server\.env"
$ClientEnv = Join-Path $RepoRoot "client\.env.local"

function Assert-FileExists {
    param(
        [string]$Path,
        [string]$Message
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

function Test-EnvKey {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    $pattern = "^\s*$([regex]::Escape($Key))\s*=\s*.+"
    return [bool](Select-String -LiteralPath $Path -Pattern $pattern -Quiet)
}

function Get-NgrokPublicUrl {
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 2
            $httpsTunnel = $response.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
            if ($httpsTunnel.public_url) {
                return [string]$httpsTunnel.public_url
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
        Start-Sleep -Milliseconds 500
    }

    return ""
}

Push-Location $RepoRoot
try {
    if ($Down) {
        docker compose -f $ComposeFile down
        exit $LASTEXITCODE
    }

    Assert-FileExists $ServerEnv "Missing server\.env. Create it before running Docker."
    Assert-FileExists $ClientEnv "Missing client\.env.local. Create it before running Docker."

    $services = @("server", "client")
    if (-not $NoNgrok) {
        $services += "ngrok"
        if (-not (Test-EnvKey $ServerEnv "NGROK_AUTHTOKEN")) {
            Write-Warning "NGROK_AUTHTOKEN is not set in server\.env. The ngrok container may stop if your ngrok account requires authentication."
        }
    }

    docker compose -f $ComposeFile up -d --build @services
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "Containers started:"
    Write-Host "  Client:  http://localhost:3000"
    Write-Host "  Server:  http://localhost:8000"
    if (-not $NoNgrok) {
        Write-Host "  Ngrok UI: http://localhost:4040"
        $ngrokPublicUrl = Get-NgrokPublicUrl
        if ($ngrokPublicUrl) {
            Write-Host "  Ngrok public URL: $ngrokPublicUrl"
            Write-Host "  Slack Request URL: $ngrokPublicUrl/slack/events"
            Write-Host "  Slack Redirect URL: $ngrokPublicUrl/slack/callback"
        }
        else {
            Write-Host "  Public URL is visible in the ngrok container logs or at http://localhost:4040"
        }
    }
    Write-Host ""
    Write-Host "Stop containers with:"
    Write-Host "  .\scripts\docker-run.ps1 -Down"

    if ($Logs) {
        docker compose -f $ComposeFile logs -f @services
    }
}
finally {
    Pop-Location
}
