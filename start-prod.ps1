# NYC CitiBike Real-time Dashboard - Production Startup Script

Write-Host "🚀 Starting NYC CitiBike Real-time Dashboard (Production Mode)" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if docker-compose file exists
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ docker-compose.yml not found in current directory" -ForegroundColor Red
    exit 1
}

Write-Host "🐳 Starting services with Docker Compose..." -ForegroundColor Yellow

try {
    # Pull latest images and build
    docker-compose pull
    docker-compose build
    
    # Start services
    docker-compose up -d
    
    Write-Host "✅ Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Application URLs:" -ForegroundColor Cyan
    Write-Host "  Dashboard: http://localhost:9518" -ForegroundColor White
    Write-Host "  Health Check: http://localhost:9518/health" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 Service Status:" -ForegroundColor Cyan
    docker-compose ps
    
    Write-Host ""
    Write-Host "📝 To view logs:" -ForegroundColor Yellow
    Write-Host "  All services: docker-compose logs -f" -ForegroundColor White
    Write-Host "  Frontend only: docker-compose logs -f frontend" -ForegroundColor White
    Write-Host "  Backend only: docker-compose logs -f backend" -ForegroundColor White
    Write-Host "  Nginx only: docker-compose logs -f nginx" -ForegroundColor White
    
    Write-Host ""
    Write-Host "🛑 To stop services:" -ForegroundColor Yellow
    Write-Host "  docker-compose down" -ForegroundColor White
    
} catch {
    Write-Host "❌ Error starting services: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔍 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check Docker Desktop is running" -ForegroundColor White
    Write-Host "  2. Ensure no other services are using ports 9518" -ForegroundColor White
    Write-Host "  3. Check logs: docker-compose logs" -ForegroundColor White
    exit 1
}
