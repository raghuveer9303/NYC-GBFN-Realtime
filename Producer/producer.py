import os
import requests
import time
import json
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# --- Configuration ---
# Get Kafka broker address from environment variable, with a default for local testing
KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

# Citi Bike API URLs
STATION_STATUS_URL = "https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_status.json"
STATION_INFO_URL = "https://gbfs.lyft.com/gbfs/2.3/bkn/en/station_information.json"

# Kafka topics
KAFKA_TOPIC = "citi_bike_stations"
STATION_INFO_TOPIC = "citi_bike_station_info"

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


def fetch_station_status(producer):
    """
    Fetches station status data from the Citi Bike API and sends each
    station's data as a separate message to the Kafka topic.
    """
    try:
        print(f"Fetching station status from {STATION_STATUS_URL}...")
        # Make the HTTP GET request to the API
        response = requests.get(STATION_STATUS_URL, timeout=15)
        # Raise an exception for bad status codes (e.g., 404, 500)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        stations = data.get('data', {}).get('stations', [])

        if not stations:
            print("⚠️ No station status data found in the API response.")
            return

        print(f"✅ Successfully fetched {len(stations)} station status updates.")

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
        print(f"📤 Published all station status updates to the '{KAFKA_TOPIC}' topic.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching station status from API: {e}")
    except json.JSONDecodeError:
        print("❌ Error decoding JSON from station status API response.")
    except Exception as e:
        print(f"❌ An unexpected error occurred during station status fetch: {e}")

def fetch_station_information(producer):
    """
    Fetches station information (coordinates, names, capacity) from the Citi Bike API
    and sends each station's information as a separate message to the Kafka topic.
    """
    try:
        print(f"Fetching station information from {STATION_INFO_URL}...")
        # Make the HTTP GET request to the API
        response = requests.get(STATION_INFO_URL, timeout=15)
        # Raise an exception for bad status codes (e.g., 404, 500)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        stations = data.get('data', {}).get('stations', [])

        if not stations:
            print("⚠️ No station information found in the API response.")
            return

        print(f"✅ Successfully fetched {len(stations)} station information records.")

        # Iterate over each station in the response
        for station in stations:
            station_id = station.get('station_id')
            if station_id:
                # Send the station information to the Kafka topic.
                producer.send(
                    STATION_INFO_TOPIC,
                    value=station,
                    key=str(station_id).encode('utf-8')
                )

        # Ensure all buffered messages are sent to the broker
        producer.flush()
        print(f"📤 Published all station information to the '{STATION_INFO_TOPIC}' topic.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching station information from API: {e}")
    except json.JSONDecodeError:
        print("❌ Error decoding JSON from station information API response.")
    except Exception as e:
        print(f"❌ An unexpected error occurred during station information fetch: {e}")


if __name__ == "__main__":
    print("🚀 Starting Citi Bike Kafka Producer...")
    
    # Create the producer instance, retrying until successful
    kafka_producer = create_kafka_producer()

    # Station information fetch interval (less frequent since it rarely changes)
    station_info_interval = 300  # 5 minutes
    last_info_fetch = 0

    # Main loop to continuously fetch and produce data
    if kafka_producer:
        # Fetch station information immediately on startup
        fetch_station_information(kafka_producer)
        last_info_fetch = time.time()
        
        while True:
            # Always fetch station status (real-time data)
            fetch_station_status(kafka_producer)
            
            # Fetch station information periodically (static data)
            current_time = time.time()
            if current_time - last_info_fetch >= station_info_interval:
                print("--- Refreshing station information ---")
                fetch_station_information(kafka_producer)
                last_info_fetch = current_time
            
            print(f"--- Waiting for {FETCH_INTERVAL} seconds before next fetch ---")
            time.sleep(FETCH_INTERVAL)
