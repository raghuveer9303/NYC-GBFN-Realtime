# NYC Citi Bike Producer Start Script

Write-Host "🚀 Starting NYC Citi Bike Kafka Producer..." -ForegroundColor Green

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

# Check if Kafka is running
$kafkaRunning = docker ps --format "{{.Names}}" | Where-Object { $_ -eq "kafka" }

if (-not $kafkaRunning) {
    Write-Host "⚠️ Kafka container is not running." -ForegroundColor Yellow
    Write-Host "Starting Kafka cluster first..." -ForegroundColor Yellow
    
    $kafkaDockerPath = "..\Data-Infrastrucuture\Docker\kafka-docker.yaml"
    if (Test-Path $kafkaDockerPath) {
        Set-Location "..\Data-Infrastrucuture\Docker"
        docker-compose -f kafka-docker.yaml up -d
        Set-Location "..\..\NYC-GBFN-Realtime"
        
        # Wait for Kafka to be ready
        Write-Host "⏳ Waiting for Kafka to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 30
    } else {
        Write-Host "❌ Kafka docker-compose file not found at $kafkaDockerPath" -ForegroundColor Red
        Write-Host "Please start Kafka manually before running the producer." -ForegroundColor Red
        exit 1
    }
}

# Build and start the producer
Write-Host "🏗️ Building and starting the Citi Bike producer..." -ForegroundColor Green
docker-compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Producer started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Monitor the producer:" -ForegroundColor Cyan
    Write-Host "  - Logs: docker-compose logs -f citi-bike-producer" -ForegroundColor White
    Write-Host "  - Status: docker-compose ps" -ForegroundColor White
    Write-Host "  - Kafka UI: http://localhost:9522" -ForegroundColor White
    Write-Host ""
    Write-Host "🛑 To stop the producer: docker-compose down" -ForegroundColor Yellow
} else {
    Write-Host "❌ Failed to start the producer. Check the logs for details." -ForegroundColor Red
    docker-compose logs citi-bike-producer
}
