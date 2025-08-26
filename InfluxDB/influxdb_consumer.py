import os
import json
import time
from datetime import datetime
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Kafka Configuration
KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9520")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "citi_bike_stations")
CONSUMER_GROUP = os.environ.get("CONSUMER_GROUP", "influxdb_consumer_group")

# InfluxDB Configuration - Updated for centralized deployment
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "data-infra-super-secret-auth-token-2025")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "data-infra-org")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "citi-bike-data")

# Batch configuration for performance
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))
BATCH_TIMEOUT = int(os.environ.get("BATCH_TIMEOUT", "10"))  # seconds

class CitiBikeInfluxDBConsumer:
    def __init__(self):
        self.setup_kafka_consumer()
        self.setup_influxdb_client()
        self.batch_buffer = []
        self.last_write_time = time.time()
        
    def setup_kafka_consumer(self):
        """Initialize Kafka consumer"""
        logger.info(f"Connecting to Kafka broker: {KAFKA_BROKER}")
        self.consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset='latest',  # Start from latest messages
            enable_auto_commit=True,
            group_id=CONSUMER_GROUP,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=1000  # 1 second timeout for batching
        )
        logger.info("✅ Kafka consumer initialized successfully")
        
    def setup_influxdb_client(self):
        """Initialize InfluxDB client"""
        logger.info(f"Connecting to InfluxDB: {INFLUXDB_URL}")
        logger.info(f"Organization: {INFLUXDB_ORG}")
        logger.info(f"Bucket: {INFLUXDB_BUCKET}")
        
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        logger.info("✅ InfluxDB client initialized successfully")
        
        # Create bucket if it doesn't exist
        self.ensure_bucket_exists()
        
    def ensure_bucket_exists(self):
        """Create the bucket if it doesn't exist"""
        try:
            buckets_api = self.influx_client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(INFLUXDB_BUCKET)
            
            if bucket is None:
                logger.info(f"Creating bucket: {INFLUXDB_BUCKET}")
                org_api = self.influx_client.organizations_api()
                org = org_api.find_organization(INFLUXDB_ORG)
                
                buckets_api.create_bucket(bucket_name=INFLUXDB_BUCKET, org=org)
                logger.info(f"✅ Bucket '{INFLUXDB_BUCKET}' created successfully")
            else:
                logger.info(f"✅ Bucket '{INFLUXDB_BUCKET}' already exists")
                
        except Exception as e:
            logger.error(f"❌ Error ensuring bucket exists: {e}")
        
    def create_point_from_station_data(self, station_data, timestamp=None):
        """Convert station data to InfluxDB Point"""
        if timestamp is None:
            timestamp = datetime.utcnow()
            
        # Extract station information
        station_id = station_data.get('station_id')
        if not station_id:
            return None
            
        # Create the point
        point = (
            Point("station_status")
            .tag("station_id", station_id)
            .tag("is_installed", str(station_data.get('is_installed', False)))
            .tag("is_renting", str(station_data.get('is_renting', False)))
            .tag("is_returning", str(station_data.get('is_returning', False)))
            .field("num_bikes_available", station_data.get('num_bikes_available', 0))
            .field("num_docks_available", station_data.get('num_docks_available', 0))
            .field("num_bikes_disabled", station_data.get('num_bikes_disabled', 0))
            .field("num_docks_disabled", station_data.get('num_docks_disabled', 0))
            .field("last_reported", station_data.get('last_reported', 0))
            .time(timestamp, WritePrecision.S)
        )
        
        # Add vehicle type information if available
        vehicle_types = station_data.get('vehicle_types_available', [])
        if vehicle_types:
            for vehicle_type in vehicle_types:
                vehicle_type_id = vehicle_type.get('vehicle_type_id', 'unknown')
                count = vehicle_type.get('count', 0)
                point = point.field(f"vehicles_{vehicle_type_id}", count)
                
        return point
        
    def write_batch_to_influxdb(self):
        """Write accumulated batch to InfluxDB"""
        if not self.batch_buffer:
            return
            
        try:
            logger.info(f"Writing batch of {len(self.batch_buffer)} points to InfluxDB")
            self.write_api.write(bucket=INFLUXDB_BUCKET, record=self.batch_buffer)
            logger.info(f"✅ Successfully wrote {len(self.batch_buffer)} points to InfluxDB")
            self.batch_buffer.clear()
            self.last_write_time = time.time()
            
        except Exception as e:
            logger.error(f"❌ Failed to write batch to InfluxDB: {e}")
            # Clear buffer to prevent memory buildup on persistent errors
            self.batch_buffer.clear()
            
    def should_flush_batch(self):
        """Determine if batch should be flushed"""
        return (
            len(self.batch_buffer) >= BATCH_SIZE or
            (time.time() - self.last_write_time) >= BATCH_TIMEOUT
        )
        
    def process_message(self, message):
        """Process a single Kafka message"""
        try:
            station_data = message.value
            station_id = station_data.get('station_id')
            
            if not station_id:
                logger.warning("Received message without station_id, skipping")
                return
                
            # Create InfluxDB point
            point = self.create_point_from_station_data(station_data)
            if point:
                self.batch_buffer.append(point)
                logger.debug(f"Added station {station_id} to batch (batch size: {len(self.batch_buffer)})")
                
                # Check if we should flush the batch
                if self.should_flush_batch():
                    self.write_batch_to_influxdb()
                    
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            logger.error(f"Message content: {message.value}")
            
    def run(self):
        """Main consumer loop"""
        logger.info("🚀 Starting Citi Bike InfluxDB Consumer...")
        logger.info(f"   Kafka Topic: {KAFKA_TOPIC}")
        logger.info(f"   Consumer Group: {CONSUMER_GROUP}")
        logger.info(f"   InfluxDB Bucket: {INFLUXDB_BUCKET}")
        logger.info(f"   Batch Size: {BATCH_SIZE}")
        logger.info(f"   Batch Timeout: {BATCH_TIMEOUT}s")
        
        try:
            while True:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if message_batch:
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            self.process_message(message)
                
                # Check for timeout-based batch flush
                if self.should_flush_batch():
                    self.write_batch_to_influxdb()
                    
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"❌ Fatal error in consumer: {e}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up resources...")
        
        # Flush any remaining data
        if self.batch_buffer:
            logger.info("Flushing remaining batch data...")
            self.write_batch_to_influxdb()
            
        # Close connections
        if hasattr(self, 'consumer'):
            self.consumer.close()
            logger.info("Kafka consumer closed")
            
        if hasattr(self, 'influx_client'):
            self.influx_client.close()
            logger.info("InfluxDB client closed")
            
        logger.info("✅ Cleanup completed")

if __name__ == "__main__":
    consumer = CitiBikeInfluxDBConsumer()
    consumer.run()
