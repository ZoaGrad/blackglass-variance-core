param(
  [string]$TaskName = "BlackglassWatchtower",
  [string]$RepoRoot = (Get-Location).Path,
  [string]$PythonRel = "venv\Scripts\python.exe",
  [string]$AgentRel  = "src\agent.py",
  [int]$IntervalMinutes = 5
)

$python = Join-Path $RepoRoot $PythonRel
$agent  = Join-Path $RepoRoot $AgentRel

if (-not (Test-Path $python)) { throw "Python not found: $python" }
if (-not (Test-Path $agent))  { throw "Agent not found:  $agent" }

# Command: Continuous Mode (Long-Running Agent)
$prompt = 'Enter continuous mode for 999999 cycles. Interval 60s. Use duration 60s per cycle. Interdict if drift_score > 0.15 OR queue_depth > 50.'
$args = "`"$agent`" `"$prompt`""

$action  = New-ScheduledTaskAction -Execute $python -Argument $args -WorkingDirectory $RepoRoot

# Triggers: At Startup AND At Logon
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerLogon.Repetition.Interval = (New-TimeSpan -Minutes $IntervalMinutes)
$triggerLogon.Repetition.Duration = ([TimeSpan]::MaxValue)

$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$triggerStartup.Repetition.Interval = (New-TimeSpan -Minutes $IntervalMinutes)
$triggerStartup.Repetition.Duration = ([TimeSpan]::MaxValue)

# Settings: restart on fail, allow on battery, don't stop if idle
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -RestartCount 99 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
  -MultipleInstances IgnoreNew

# Run as current user (Highest privileges).
# Using S4U allows running whether user is logged on or not (if they have batch job rights), 
# but mostly ensures it runs in a context that can access local files/network.
$principal = New-ScheduledTaskPrincipal -UserId $env:UserName -LogonType S4U -RunLevel Highest

# Register (overwrite if exists)
try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon, $triggerStartup) -Settings $settings -Principal $principal | Out-Null

Write-Host "Installed Scheduled Task: $TaskName"
Write-Host "RepoRoot: $RepoRoot"
Write-Host "Runs: $python $args"
