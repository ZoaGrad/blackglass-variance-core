# BLACKGLASS SWARM AUTO-RECOVERY WRAPPER (Windows)
# =================================================
# Equivalent to systemd service on Linux.
# Ensures the swarm auto-restarts on crash and survives reboots.
#
# DEPLOYMENT:
# 1. Create scheduled task: Task Scheduler -> Create Basic Task
# 2. Trigger: "When the computer starts"
# 3. Action: "Start a program" -> powershell.exe -ExecutionPolicy Bypass -File "C:\path\to\start_swarm.ps1"

$ErrorActionPreference = "Continue"
$WorkDir = "C:\Users\colem\Code\blackglass-variance-core"
$LogFile = "$WorkDir\swarm.log"

Write-Host "[SWARM] :: Initializing Blackglass Oculus V2..." -ForegroundColor Cyan

# Ensure .env is loaded (for PRIVATE_KEY, RPC_URL)
if (-Not (Test-Path "$WorkDir\.env")) {
    Write-Host "[SWARM] :: FATAL :: .env file not found!" -ForegroundColor Red
    exit 1
}

# Infinite restart loop (systemd equivalent: Restart=always)
while ($true) {
    try {
        Write-Host "[SWARM] :: ACTIVATING :: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Green
        
        # Launch the swarm (blocks until crash or manual termination)
        Set-Location $WorkDir
        python run_species.py 2>&1 | Tee-Object -FilePath $LogFile -Append
        
        $exitCode = $LASTEXITCODE
        Write-Host "[SWARM] :: TERMINATED :: Exit Code $exitCode" -ForegroundColor Yellow
        
        # If intentional shutdown (Ctrl+C = exit code 0), break loop
        if ($exitCode -eq 0) {
            Write-Host "[SWARM] :: Clean shutdown detected. Exiting auto-restart." -ForegroundColor Cyan
            break
        }
        
    }
    catch {
        Write-Host "[SWARM] :: CRASH DETECTED :: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Restart delay (systemd equivalent: RestartSec=5s)
    Write-Host "[SWARM] :: Auto-restart in 5 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

Write-Host "[SWARM] :: Service stopped." -ForegroundColor Gray
