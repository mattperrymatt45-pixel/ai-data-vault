# start.ps1 - Run this to start the AI Data Vault backend

$backendDir  = Join-Path $PSScriptRoot "backend"
$venvDir     = Join-Path $backendDir ".venv"
$pip         = Join-Path $venvDir "Scripts\pip.exe"
$pythonExe   = Join-Path $venvDir "Scripts\python.exe"

# Python 3.14 installation path (detected on this machine)
$systemPython = "C:\Users\Vivaan\AppData\Local\Programs\Python\Python314\python.exe"

# Fallback: try py launcher or PATH python
if (-not (Test-Path $systemPython)) {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) { $systemPython = $pyCmd.Source }
}
if (-not $systemPython -or -not (Test-Path $systemPython)) {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) { $systemPython = $pyCmd.Source }
}
if (-not $systemPython -or -not (Test-Path $systemPython)) {
    Write-Host "ERROR: Python not found. Please install from https://python.org" -ForegroundColor Red
    pause; exit 1
}

Write-Host "Personal AI Data Vault" -ForegroundColor Magenta
Write-Host "Using Python: $systemPython" -ForegroundColor DarkGray
Write-Host "-------------------------------" -ForegroundColor DarkGray

# Create venv if needed
if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    & $systemPython -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Could not create venv." -ForegroundColor Red
        pause; exit 1
    }
}

# Install deps
Write-Host "Installing dependencies (first run may take a few minutes)..." -ForegroundColor Cyan
& $pip install -r "$backendDir\requirements.txt" -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install failed." -ForegroundColor Red
    pause; exit 1
}

Write-Host ""
Write-Host "Server starting at: http://localhost:8000" -ForegroundColor Green
Write-Host "Open browser at:    http://localhost:8000/app" -ForegroundColor Green
Write-Host ""
Write-Host "Make sure Ollama is running in another terminal:" -ForegroundColor Yellow
Write-Host "  ollama serve" -ForegroundColor DarkYellow
Write-Host "  ollama pull llama3" -ForegroundColor DarkYellow
Write-Host "  ollama pull nomic-embed-text" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host "-------------------------------" -ForegroundColor DarkGray

Set-Location $backendDir
& $pythonExe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
