# Citi Bike Anomaly Detection API

A FastAPI-based real-time anomaly detection service for Citi Bike station operations. This service monitors bike-sharing stations and identifies operational issues requiring immediate attention.

## Features

- **Real-time Detection**: Analyzes live station data from InfluxDB
- **Multiple Anomaly Types**: Detects capacity issues, station health problems, and communication failures
- **Severity Classification**: Categorizes anomalies as CRITICAL, WARNING, or INFO
- **RESTful API**: Easy integration with dashboards and alerting systems
- **Operational Focus**: Designed for bike-share operators to manage fleet and stations

## Quick Start

### Prerequisites

- Python 3.8+
- InfluxDB with Citi Bike station data
- Required Python packages (see requirements.influxdb.txt)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.influxdb.txt
```

2. Set environment variables (optional):
```bash
export INFLUXDB_URL="http://brahma:8086"
export INFLUXDB_TOKEN="your-token"
export INFLUXDB_ORG="data-infra-org"
export INFLUXDB_BUCKET="citi-bike-data"
```

3. Start the API server:
```bash
# Linux/Mac
./start-api.sh

# Windows
.\start-api.ps1

# Or directly with Python
python anomaly_api.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
- **GET** `/` - Basic health check
- **GET** `/health` - Detailed health check with InfluxDB connectivity

### Anomalies
- **GET** `/anomalies` - Get all current anomalies with summary
- **GET** `/anomalies/critical` - Get only critical anomalies requiring immediate action
- **GET** `/stations/{station_id}/anomalies` - Get anomalies for a specific station

### Station Status
- **GET** `/stations` - Get current status of all stations (limited)

### Query Parameters

#### `/anomalies` endpoint:
- `severity`: Filter by severity (CRITICAL, WARNING, INFO)
- `anomaly_type`: Filter by anomaly type
- `limit`: Maximum number of anomalies to return (default: 100)

#### `/stations` endpoint:
- `limit`: Maximum number of stations to return (default: 50)

## Anomaly Types

### Critical Issues (Immediate Action Required)
- **STATION_EMPTY**: No bikes available for rental
- **STATION_FULL**: No docks available for bike returns
- **STATION_OFFLINE**: Station marked as not installed/offline
- **STATION_NOT_RENTING**: Station not accepting bike rentals
- **STATION_NOT_RETURNING**: Station not accepting bike returns

### Warning Issues (Plan Intervention)
- **STATION_LOW**: Station running low on bikes (< 20% capacity)
- **STATION_HIGH**: Station nearly full (< 20% docks available)
- **HIGH_DISABLED_BIKES**: High number of disabled bikes (> 30%)
- **STALE_DATA**: Station hasn't reported data recently (> 10 minutes)

## API Response Examples

### Get All Anomalies
```bash
curl "http://localhost:8000/anomalies?severity=CRITICAL&limit=10"
```

Response:
```json
{
  "total_stations": 2244,
  "total_anomalies": 1245,
  "critical_count": 234,
  "warning_count": 1011,
  "info_count": 0,
  "detection_timestamp": "2025-08-25T14:20:00.000Z",
  "anomalies": [
    {
      "station_id": "66db2e3a-0aca-11e7-82f6-3863bb44ef7c",
      "anomaly_type": "STATION_EMPTY",
      "severity": "CRITICAL",
      "message": "Station 66db2e3a-0aca-11e7-82f6-3863bb44ef7c is completely empty (0 bikes available)",
      "timestamp": "2025-08-25T14:15:30.000Z",
      "current_value": 0,
      "expected_range": null,
      "action_required": "URGENT: Dispatch bikes for rebalancing"
    }
  ]
}
```

### Get Critical Anomalies Only
```bash
curl "http://localhost:8000/anomalies/critical"
```

### Get Station Status
```bash
curl "http://localhost:8000/stations?limit=5"
```

Response:
```json
[
  {
    "station_id": "66db2e3a-0aca-11e7-82f6-3863bb44ef7c",
    "timestamp": "2025-08-25T14:15:30.000Z",
    "num_bikes_available": 0,
    "num_docks_available": 12,
    "num_bikes_disabled": 2,
    "num_docks_disabled": 0,
    "is_renting": true,
    "is_returning": true,
    "is_installed": true,
    "total_capacity": 14
  }
]
```

## Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Integration Examples

### Dashboard Integration
```javascript
// Fetch critical anomalies for dashboard
fetch('http://localhost:8000/anomalies/critical')
  .then(response => response.json())
  .then(anomalies => {
    // Update dashboard with critical issues
    updateCriticalAlertsPanel(anomalies);
  });
```

### Alerting System
```python
import requests

# Check for critical anomalies
response = requests.get('http://localhost:8000/anomalies/critical')
critical_anomalies = response.json()

for anomaly in critical_anomalies:
    if anomaly['anomaly_type'] in ['STATION_EMPTY', 'STATION_FULL']:
        # Send immediate alert to operations team
        send_urgent_alert(anomaly)
```

### Monitoring Script
```bash
#!/bin/bash
# Check API health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Anomaly Detection API is healthy"
else
    echo "❌ Anomaly Detection API is down"
    # Send alert
fi
```

## Operational Use Cases

### 1. Real-time Operations Dashboard
- Display critical anomalies requiring immediate dispatch
- Show system-wide health metrics
- Monitor station capacity trends

### 2. Fleet Rebalancing
- Identify empty stations needing bike delivery
- Find full stations requiring bike removal
- Optimize rebalancing truck routes

### 3. Maintenance Management
- Track stations with high disabled bike counts
- Monitor communication issues
- Schedule preventive maintenance

### 4. Performance Monitoring
- Track anomaly trends over time
- Measure response time to critical issues
- Generate operational reports

## Configuration

Environment variables:
- `INFLUXDB_URL`: InfluxDB server URL (default: http://brahma:8086)
- `INFLUXDB_TOKEN`: Authentication token
- `INFLUXDB_ORG`: Organization name (default: data-infra-org)
- `INFLUXDB_BUCKET`: Data bucket name (default: citi-bike-data)
- `LOOKBACK_MINUTES`: Historical data window for trends (default: 15)

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.influxdb.txt .
RUN pip install -r requirements.influxdb.txt

COPY anomaly_api.py .

EXPOSE 8000
CMD ["uvicorn", "anomaly_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use a production ASGI server (e.g., Gunicorn + Uvicorn)
- Set up proper logging and monitoring
- Configure environment-specific settings
- Implement rate limiting and authentication if needed
- Set up health checks and auto-scaling

## Troubleshooting

### Common Issues

1. **InfluxDB Connection Failed**
   - Check if InfluxDB is running and accessible
   - Verify connection parameters and credentials
   - Test with: `curl http://brahma:8086/health`

2. **No Data Found**
   - Ensure the producer is running and sending data
   - Check bucket name and measurement name
   - Verify data exists: visit InfluxDB UI

3. **High Memory Usage**
   - Large number of stations can consume memory
   - Implement pagination for large deployments
   - Consider caching strategies

### API Testing
```bash
# Test all endpoints
curl http://localhost:8000/health
curl http://localhost:8000/anomalies
curl http://localhost:8000/anomalies/critical
curl http://localhost:8000/stations
```

## License

This project is part of the Data Infrastructure suite for real-time bike-sharing analytics.
