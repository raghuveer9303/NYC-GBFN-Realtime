#!/bin/bash
# Citi Bike Anomaly Detection API Startup Script

echo "🚀 Starting Citi Bike Anomaly Detection API..."

# Check if required environment variables are set
if [ -z "$INFLUXDB_URL" ]; then
    echo "⚠️  INFLUXDB_URL not set, using default: http://brahma:8086"
    export INFLUXDB_URL="http://brahma:8086"
fi

if [ -z "$INFLUXDB_TOKEN" ]; then
    echo "⚠️  INFLUXDB_TOKEN not set, using default"
    export INFLUXDB_TOKEN="data-infra-super-secret-auth-token-2025"
fi

if [ -z "$INFLUXDB_ORG" ]; then
    echo "⚠️  INFLUXDB_ORG not set, using default: data-infra-org"
    export INFLUXDB_ORG="data-infra-org"
fi

if [ -z "$INFLUXDB_BUCKET" ]; then
    echo "⚠️  INFLUXDB_BUCKET not set, using default: citi-bike-data"
    export INFLUXDB_BUCKET="citi-bike-data"
fi

echo "🔧 Configuration:"
echo "   InfluxDB URL: $INFLUXDB_URL"
echo "   InfluxDB Org: $INFLUXDB_ORG"
echo "   InfluxDB Bucket: $INFLUXDB_BUCKET"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.influxdb.txt

# Start the API server
echo "🌐 Starting FastAPI server on http://0.0.0.0:8000"
uvicorn anomaly_api:app --host 0.0.0.0 --port 8000 --reload
