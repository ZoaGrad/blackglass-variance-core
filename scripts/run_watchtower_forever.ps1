# Startup Folder Fallback Script
# Usage: Create a shortcut to this script in your Shell:Startup folder.
# Target: powershell.exe -ExecutionPolicy Bypass -File "C:\path\to\this\script.ps1"

# 1. Navigate to Repo Root (assuming script is in /scripts)
Set-Location -Path $PSScriptRoot
Set-Location ..
$RepoRoot = Get-Location

$PythonPath = Join-Path $RepoRoot "venv\Scripts\python.exe"
$AgentPath  = Join-Path $RepoRoot "src\agent.py"

if (-not (Test-Path $PythonPath)) { 
    Write-Host "Error: Python not found at $PythonPath" -ForegroundColor Red
    Start-Sleep -Seconds 10
    exit 1
}

# 2. Define the Long-Running Command
$Prompt = 'Enter continuous mode for 999999 cycles. Interval 60s. Use duration 60s per cycle. Interdict if drift_score > 0.15 OR queue_depth > 50.'

Write-Host "Starting Blackglass Watchtower Loop..."
Write-Host "Repo: $RepoRoot"

# 3. Infinite Loop (Service Wrapper)
while ($true) {
    Write-Host "Launching Agent..." -ForegroundColor Cyan
    
    # Run the agent. It will block here for ~2 years (999999 cycles * 60s).
    # If it crashes or exits (e.g. lock file collision), we catch it.
    try {
        & $PythonPath $AgentPath $Prompt
    } catch {
        Write-Host "Agent crashed: $_" -ForegroundColor Red
    }

    Write-Host "Agent exited. Restarting in 10 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}
