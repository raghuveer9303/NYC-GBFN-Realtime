import os
import requests
import time
import json
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# --- Configuration ---
# Get Kafka broker address from environment variable, with a default for local testing
KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

# Citi Bike API URL for real-time station status
API_URL = "https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_status.json"

# Kafka topic to which we'll send the data
KAFKA_TOPIC = "citi_bike_stations"

# Time to wait between API calls, in seconds
FETCH_INTERVAL = 30

def create_kafka_producer():
    """
    Creates and returns a Kafka producer.
    Will retry connection if brokers are not available.
    """
    # Loop indefinitely until a connection is made
    while True:
        try:
            # Initialize the Kafka Producer
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                # Serialize messages as JSON and encode to utf-8
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                # Timeout for broker connection attempts (in milliseconds)
                api_version_auto_timeout_ms=10000,
                # Time to wait before retrying a failed connection (in milliseconds)
                reconnect_backoff_ms=5000
            )
            print("✅ Successfully connected to Kafka broker.")
            return producer
        except NoBrokersAvailable:
            print(f"⚠️ Kafka broker at {KAFKA_BROKER} not available. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ An unexpected error occurred while connecting to Kafka: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)


def fetch_and_produce(producer):
    """
    Fetches station status data from the Citi Bike API and sends each
    station's data as a separate message to the Kafka topic.
    """
    try:
        print(f"Fetching data from {API_URL}...")
        # Make the HTTP GET request to the API
        response = requests.get(API_URL, timeout=15)
        # Raise an exception for bad status codes (e.g., 404, 500)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        stations = data.get('data', {}).get('stations', [])

        if not stations:
            print("⚠️ No station data found in the API response.")
            return

        print(f"✅ Successfully fetched {len(stations)} station updates.")

        # Iterate over each station in the response
        for station in stations:
            station_id = station.get('station_id')
            if station_id:
                # Send the station data to the Kafka topic.
                # The station_id is used as the message key to ensure that all data
                # for a specific station is sent to the same partition, preserving order.
                producer.send(
                    KAFKA_TOPIC,
                    value=station,
                    key=str(station_id).encode('utf-8')
                )

        # Ensure all buffered messages are sent to the broker
        producer.flush()
        print(f"📤 Published all station updates to the '{KAFKA_TOPIC}' topic.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data from API: {e}")
    except json.JSONDecodeError:
        print("❌ Error decoding JSON from API response. The data may be malformed.")
    except Exception as e:
        print(f"❌ An unexpected error occurred during fetch/produce cycle: {e}")


if __name__ == "__main__":
    print("🚀 Starting Citi Bike Kafka Producer...")
    
    # Create the producer instance, retrying until successful
    kafka_producer = create_kafka_producer()

    # Main loop to continuously fetch and produce data
    if kafka_producer:
        while True:
            fetch_and_produce(kafka_producer)
            print(f"--- Waiting for {FETCH_INTERVAL} seconds before next fetch ---")
            time.sleep(FETCH_INTERVAL)
