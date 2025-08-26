# NYC CitiBike Real-time Dashboard - Development Startup Script

Write-Host "🚀 Starting NYC CitiBike Real-time Dashboard (Development Mode)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Function to check if a port is in use
function Test-Port($port) {
    $result = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    return $result -ne $null
}

# Function to start backend
function Start-Backend {
    Write-Host "📊 Starting Backend API (Port 8000)..." -ForegroundColor Yellow
    
    if (Test-Port 8000) {
        Write-Host "⚠️  Port 8000 is already in use. Backend may already be running." -ForegroundColor Red
        return
    }
    
    $backendPath = Split-Path -Parent $PSScriptRoot
    $backendPath = Join-Path $backendPath "Backend"
    
    if (Test-Path $backendPath) {
        Set-Location $backendPath
        
        # Start backend in a new PowerShell window
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "python anomaly_api.py"
        Write-Host "✅ Backend started in new window" -ForegroundColor Green
    } else {
        Write-Host "❌ Backend directory not found: $backendPath" -ForegroundColor Red
    }
}

# Function to start frontend
function Start-Frontend {
    Write-Host "🎨 Starting Frontend (Port 8080)..." -ForegroundColor Yellow
    
    if (Test-Port 8080) {
        Write-Host "⚠️  Port 8080 is already in use. Frontend may already be running." -ForegroundColor Red
        return
    }
    
    $frontendPath = Join-Path $PSScriptRoot "Frontend"
    
    if (Test-Path $frontendPath) {
        Set-Location $frontendPath
        
        # Install dependencies if node_modules doesn't exist
        if (-not (Test-Path "node_modules")) {
            Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
            npm install
        }
        
        # Start development server
        Write-Host "🔥 Starting Vite development server..." -ForegroundColor Green
        npm run dev
    } else {
        Write-Host "❌ Frontend directory not found: $frontendPath" -ForegroundColor Red
    }
}

# Main execution
try {
    # Start backend first
    Start-Backend
    
    # Wait a moment for backend to start
    Start-Sleep -Seconds 3
    
    # Start frontend
    Start-Frontend
    
} catch {
    Write-Host "❌ Error occurred: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "🌐 Application URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:8080" -ForegroundColor White
Write-Host "  Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
