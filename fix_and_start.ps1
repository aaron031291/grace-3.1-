# Grace Fix & Start Script for Windows
# Run this in PowerShell to fix all issues and start Grace

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Grace - Fix & Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill ALL old processes
Write-Host "[1/6] Killing old processes..." -ForegroundColor Yellow
Get-Process -Name node, python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "  Done" -ForegroundColor Green

# Step 2: Pull latest code
Write-Host "[2/6] Pulling latest code..." -ForegroundColor Yellow
git pull origin Aaron-new
git checkout origin/Aaron-new -- frontend/src/components/
git checkout origin/Aaron-new -- frontend/vite.config.js
git checkout origin/Aaron-new -- backend/settings.py
git checkout origin/Aaron-new -- backend/genesis/genesis_key_service.py
Write-Host "  Done" -ForegroundColor Green

# Step 3: Fix .env
Write-Host "[3/6] Fixing .env..." -ForegroundColor Yellow
$envFile = "backend\.env"
if (Test-Path $envFile) {
    $content = Get-Content $envFile -Raw
    $content = $content -replace "EMBEDDING_DEFAULT=qwen_4b", "EMBEDDING_DEFAULT=all-MiniLM-L6-v2"
    if ($content -notmatch "SKIP_EMBEDDING_LOAD") {
        $content += "`nSKIP_EMBEDDING_LOAD=true"
    }
    if ($content -notmatch "SKIP_QDRANT_CHECK") {
        $content += "`nSKIP_QDRANT_CHECK=true"
    }
    Set-Content $envFile $content
    Write-Host "  .env fixed" -ForegroundColor Green
} else {
    Write-Host "  No .env found - using defaults" -ForegroundColor Yellow
}

# Step 4: Install dependencies
Write-Host "[4/6] Installing dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm install 2>$null
Set-Location ..
Write-Host "  Done" -ForegroundColor Green

# Step 5: Start backend
Write-Host "[5/6] Starting backend..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "python" -ArgumentList "-m uvicorn app:app --host 0.0.0.0 --port 8000" -WorkingDirectory "backend" -PassThru -NoNewWindow
Write-Host "  Backend starting on http://localhost:8000" -ForegroundColor Green
Start-Sleep -Seconds 5

# Step 6: Start frontend
Write-Host "[6/6] Starting frontend..." -ForegroundColor Yellow
Set-Location frontend
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Grace is starting!" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Health:   http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
npm run dev
