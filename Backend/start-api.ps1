# Citi Bike Anomaly Detection API Startup Script for Windows

Write-Host "🚀 Starting Citi Bike Anomaly Detection API..." -ForegroundColor Green

# Check if required environment variables are set
if (-not $env:INFLUXDB_URL) {
    Write-Host "⚠️  INFLUXDB_URL not set, using default: http://brahma:8086" -ForegroundColor Yellow
    $env:INFLUXDB_URL = "http://brahma:8086"
}

if (-not $env:INFLUXDB_TOKEN) {
    Write-Host "⚠️  INFLUXDB_TOKEN not set, using default" -ForegroundColor Yellow
    $env:INFLUXDB_TOKEN = "data-infra-super-secret-auth-token-2025"
}

if (-not $env:INFLUXDB_ORG) {
    Write-Host "⚠️  INFLUXDB_ORG not set, using default: data-infra-org" -ForegroundColor Yellow
    $env:INFLUXDB_ORG = "data-infra-org"
}

if (-not $env:INFLUXDB_BUCKET) {
    Write-Host "⚠️  INFLUXDB_BUCKET not set, using default: citi-bike-data" -ForegroundColor Yellow
    $env:INFLUXDB_BUCKET = "citi-bike-data"
}

Write-Host "🔧 Configuration:" -ForegroundColor Cyan
Write-Host "   InfluxDB URL: $env:INFLUXDB_URL" -ForegroundColor White
Write-Host "   InfluxDB Org: $env:INFLUXDB_ORG" -ForegroundColor White
Write-Host "   InfluxDB Bucket: $env:INFLUXDB_BUCKET" -ForegroundColor White

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Blue
pip install -r requirements.txt

# Start the API server
Write-Host "🌐 Starting FastAPI server on http://0.0.0.0:8000" -ForegroundColor Green
uvicorn anomaly_api:app --host 0.0.0.0 --port 8000 --reload
