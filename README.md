# NYC Citi Bike Real-time Data Producer

This project contains a Kafka producer that fetches real-time Citi Bike station status data and publishes it to a Kafka topic.

## Overview

The producer:
- Fetches real-time station status data from the Citi Bike API every 30 seconds
- Publishes each station's data as a separate message to the `citi_bike_stations` Kafka topic
- Uses the station ID as the message key to ensure messages for the same station go to the same partition
- Includes robust error handling and automatic retry logic

## Prerequisites

- Docker and Docker Compose installed
- Your Kafka cluster running (from the `kafka-docker.yaml` file)
- The `data-infra-network` Docker network created

## Setup and Running

### 1. Ensure Kafka is Running

First, make sure your Kafka cluster is running. From the `Data-Infrastructure/Docker` directory:

```powershell
docker-compose -f kafka-docker.yaml up -d
```

### 2. Verify Network Exists

Ensure the `data-infra-network` exists:

```powershell
docker network ls | findstr data-infra-network
```

If it doesn't exist, create it:

```powershell
docker network create data-infra-network
```

### 3. Build and Run the Producer

From this directory (`NYC-GBFN-Realtime`):

```powershell
# Build and start the producer
docker-compose up --build -d

# View logs
docker-compose logs -f citi-bike-producer

# Stop the producer
docker-compose down
```

## Configuration

You can customize the producer behavior using environment variables in the `docker-compose.yml` file:

- `KAFKA_BROKER`: Kafka broker address (default: `kafka:29092` for internal Docker network)
- `FETCH_INTERVAL`: Time between API calls in seconds (default: `30`)

## Monitoring

### View Producer Logs
```powershell
docker logs -f citi-bike-producer
```

### Check Producer Health
```powershell
docker-compose ps
```

### Access Kafka UI
Once your Kafka cluster is running, you can monitor the topics and messages at:
- Kafka UI: http://localhost:9522

### Verify Messages in Kafka

You can use the Kafka UI or connect to the Kafka container to verify messages are being produced:

```powershell
# Connect to Kafka container
docker exec -it kafka bash

# List topics
kafka-topics --bootstrap-server localhost:9092 --list

# Consume messages from the topic (to verify data is flowing)
kafka-console-consumer --bootstrap-server localhost:9092 --topic citi_bike_stations --from-beginning
```

## Troubleshooting

### Producer Cannot Connect to Kafka
- Ensure Kafka is running: `docker ps | findstr kafka`
- Check if the containers are on the same network: `docker network inspect data-infra-network`
- Verify Kafka health: `docker logs kafka`

### API Connection Issues
- Check internet connectivity from the container
- Verify the API URL is accessible: https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_status.json

### No Data in Kafka Topic
- Check producer logs for errors: `docker logs citi-bike-producer`
- Verify the topic exists in Kafka UI
- Ensure the producer has successfully connected to Kafka

## Data Format

Each message contains station data in JSON format with fields like:
- `station_id`: Unique identifier for the station
- `num_bikes_available`: Number of bikes currently available
- `num_docks_available`: Number of empty docks available
- `last_reported`: Timestamp of last update
- And other station status information

## Development

To run the producer locally for development:

```powershell
# Install dependencies
pip install -r requirements.txt

# Set environment variable for local Kafka
$env:KAFKA_BROKER = "localhost:9520"

# Run the producer
python producer.py
```

Note: When running locally, use port `9520` which is mapped to Kafka's internal port `9092` in your kafka-docker.yaml configuration.
