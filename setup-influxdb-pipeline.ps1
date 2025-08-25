# Complete InfluxDB Pipeline Setup Script

Write-Host "🚀 Setting up complete InfluxDB pipeline for Citi Bike data..." -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
} catch {
    Write-Host "❌ Docker is not running or not installed. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check if data-infra-network exists
$networkExists = docker network ls --format "{{.Name}}" | Where-Object { $_ -eq "data-infra-network" }

if (-not $networkExists) {
    Write-Host "🔗 Creating data-infra-network..." -ForegroundColor Yellow
    docker network create data-infra-network
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create network. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Step 1: Deploy InfluxDB in the centralized Docker directory
Write-Host ""
Write-Host "📊 Step 1: Deploying InfluxDB..." -ForegroundColor Cyan
$dockerDir = "..\Data-Infrastrucuture\Docker"

if (Test-Path $dockerDir) {
    $currentDir = Get-Location
    Set-Location $dockerDir
    
    Write-Host "Starting InfluxDB from centralized Docker directory..." -ForegroundColor Yellow
    docker-compose -f influxdb-docker.yaml up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ InfluxDB deployed successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to deploy InfluxDB. Check logs." -ForegroundColor Red
        Set-Location $currentDir
        exit 1
    }
    
    Set-Location $currentDir
} else {
    Write-Host "❌ Cannot find Docker directory at $dockerDir" -ForegroundColor Red
    exit 1
}

# Wait for InfluxDB to be ready
Write-Host ""
Write-Host "⏳ Waiting for InfluxDB to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check InfluxDB health
$influxHealthy = $false
$attempts = 0
$maxAttempts = 6

while (-not $influxHealthy -and $attempts -lt $maxAttempts) {
    $attempts++
    Write-Host "Checking InfluxDB health (attempt $attempts/$maxAttempts)..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8086/health" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            $influxHealthy = $true
            Write-Host "✅ InfluxDB is healthy!" -ForegroundColor Green
        }
    } catch {
        Write-Host "InfluxDB not ready yet, waiting 10 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
}

if (-not $influxHealthy) {
    Write-Host "❌ InfluxDB failed to become healthy. Check logs:" -ForegroundColor Red
    docker logs influxdb
    exit 1
}

# Step 2: Check if Kafka and producer are running
Write-Host ""
Write-Host "🔍 Step 2: Checking Kafka and producer status..." -ForegroundColor Cyan

$kafkaRunning = docker ps --format "{{.Names}}" | Where-Object { $_ -eq "kafka" }
$producerRunning = docker ps --format "{{.Names}}" | Where-Object { $_ -eq "citi-bike-producer" }

if (-not $kafkaRunning) {
    Write-Host "⚠️ Kafka is not running. Please start Kafka first." -ForegroundColor Yellow
    Write-Host "Expected command: docker-compose -f ..\Data-Infrastrucuture\Docker\kafka-docker.yaml up -d" -ForegroundColor White
}

if (-not $producerRunning) {
    Write-Host "⚠️ Citi Bike producer is not running. Please start the producer first." -ForegroundColor Yellow
    Write-Host "Expected command: docker-compose up -d" -ForegroundColor White
}

if (-not $kafkaRunning -or -not $producerRunning) {
    $continue = Read-Host "Do you want to continue with just InfluxDB consumer setup? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host "Please start Kafka and producer first, then run this script again." -ForegroundColor Yellow
        exit 1
    }
}

# Step 3: Deploy the InfluxDB consumer
Write-Host ""
Write-Host "📥 Step 3: Deploying InfluxDB consumer..." -ForegroundColor Cyan

docker-compose -f docker-compose.consumer-only.yml up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ InfluxDB consumer deployed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to deploy consumer. Check logs." -ForegroundColor Red
    docker-compose -f docker-compose.consumer-only.yml logs
    exit 1
}

# Display status and access information
Write-Host ""
Write-Host "🎉 InfluxDB Pipeline Setup Complete!" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host ""
Write-Host "📊 Access Information:" -ForegroundColor Cyan
Write-Host "  - InfluxDB UI: http://localhost:8086" -ForegroundColor White
Write-Host "    Username: admin" -ForegroundColor White
Write-Host "    Password: influxdb_admin_2025" -ForegroundColor White
Write-Host "    Organization: data-infra-org" -ForegroundColor White
Write-Host "    Token: data-infra-super-secret-auth-token-2025" -ForegroundColor White

Write-Host ""
Write-Host "📈 Monitoring Commands:" -ForegroundColor Cyan
Write-Host "  - InfluxDB logs: docker logs -f influxdb" -ForegroundColor White
Write-Host "  - Consumer logs: docker logs -f citi-bike-influxdb-consumer" -ForegroundColor White
Write-Host "  - All services: docker ps" -ForegroundColor White

Write-Host ""
Write-Host "🔍 Data Verification:" -ForegroundColor Cyan
Write-Host "  1. Go to http://localhost:8086" -ForegroundColor White
Write-Host "  2. Login with the credentials above" -ForegroundColor White
Write-Host "  3. Navigate to Data Explorer" -ForegroundColor White
Write-Host "  4. Select bucket 'citi-bike-data'" -ForegroundColor White
Write-Host "  5. Look for measurement 'station_status'" -ForegroundColor White

Write-Host ""
Write-Host "🛑 To stop everything:" -ForegroundColor Yellow
Write-Host "  - Consumer: docker-compose -f docker-compose.consumer-only.yml down" -ForegroundColor White
Write-Host "  - InfluxDB: docker-compose -f ..\Data-Infrastrucuture\Docker\influxdb-docker.yaml down" -ForegroundColor White

Write-Host ""
Write-Host "✅ Setup completed! Data should start flowing into InfluxDB." -ForegroundColor Green
