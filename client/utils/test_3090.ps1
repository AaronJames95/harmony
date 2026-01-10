# Harmony AI - Client-Side Connectivity Validator
# Replace this with your workstation's Tailscale IP
$WORKSTATION_IP = "100.94.65.56" 
$MODEL_NAME = "harmony-coder"

Write-Host "--- Harmony AI Pre-Flight Check ---" -ForegroundColor Cyan

# 1. Check if Tailscale is running locally
Write-Host "[1/4] Checking Local Tailscale..." -NoNewline
$tsStatus = tailscale status --json | ConvertFrom-Json
if ($tsStatus.BackendState -eq "Running") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host " -> Action: Start the Tailscale app on this laptop."
    exit
}

# 2. Ping the Workstation over Tailscale
Write-Host "[2/4] Pinging Workstation ($WORKSTATION_IP)..." -NoNewline
if (Test-Connection -ComputerName $WORKSTATION_IP -Count 1 -Quiet) {
    Write-Host " REACHABLE" -ForegroundColor Green
} else {
    Write-Host " UNREACHABLE" -ForegroundColor Red
    Write-Host " -> Action: Ensure the 3090 Workstation is powered on and connected to Tailscale."
    exit
}

# 3. Check if Ollama API is responding
Write-Host "[3/4] Testing Ollama API (Port 11434)..." -NoNewline
try {
    $version = Invoke-RestMethod -Uri "http://$($WORKSTATION_IP):11434/api/version" -TimeoutSec 5
    Write-Host " RESPONDING (v$($version.version))" -ForegroundColor Green
} catch {
    Write-Host " NO RESPONSE" -ForegroundColor Red
    Write-Host " -> Action: Run './launch_ai.sh' on the workstation and check the firewall (UFW)."
    exit
}

# 4. Check if the specific model is loaded
Write-Host "[4/4] Checking Model ($MODEL_NAME)..." -NoNewline
$models = Invoke-RestMethod -Uri "http://$($WORKSTATION_IP):11434/api/tags"
if ($models.models.name -contains "$MODEL_NAME:latest" -or $models.models.name -contains $MODEL_NAME) {
    Write-Host " READY" -ForegroundColor Green
} else {
    Write-Host " NOT FOUND" -ForegroundColor Yellow
    Write-Host " -> Action: Run './setup_ai.sh' on the workstation to register the model."
    exit
}

Write-Host "`nSUCCESS: Your 3090 is ready for Cline." -ForegroundColor Green -BackgroundColor DarkGreen