#!/usr/bin/env python3
"""
Simple test script to verify Kafka connectivity and topic creation.
Run this before starting the main producer to ensure everything is working.
"""

import os
import json
import time
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin.config_resource import ConfigResource, ConfigResourceType
from kafka.admin.new_topic import NewTopic
from kafka.errors import TopicAlreadyExistsError

# Configuration
KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9520")
TOPIC_NAME = "citi_bike_stations"

def test_kafka_connection():
    """Test basic Kafka connectivity"""
    print(f"🔍 Testing connection to Kafka broker: {KAFKA_BROKER}")
    
    try:
        # Test with a simple producer
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version_auto_timeout_ms=10000
        )
        
        # Send a test message
        test_message = {"test": "connectivity", "timestamp": time.time()}
        future = producer.send("test-topic", value=test_message)
        result = future.get(timeout=10)
        
        print("✅ Successfully connected to Kafka!")
        print(f"   Topic: {result.topic}")
        print(f"   Partition: {result.partition}")
        print(f"   Offset: {result.offset}")
        
        producer.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return False

def create_topic():
    """Create the citi_bike_stations topic if it doesn't exist"""
    print(f"🏗️ Creating topic: {TOPIC_NAME}")
    
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=[KAFKA_BROKER],
            api_version_auto_timeout_ms=10000
        )
        
        topic = NewTopic(
            name=TOPIC_NAME,
            num_partitions=3,  # Good for distributing station data
            replication_factor=1  # Single broker setup
        )
        
        admin_client.create_topics([topic], validate_only=False)
        print(f"✅ Topic '{TOPIC_NAME}' created successfully!")
        
    except TopicAlreadyExistsError:
        print(f"ℹ️ Topic '{TOPIC_NAME}' already exists.")
    except Exception as e:
        print(f"❌ Failed to create topic: {e}")

def list_topics():
    """List all available topics"""
    print("📋 Listing all topics:")
    
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=[KAFKA_BROKER],
            api_version_auto_timeout_ms=10000
        )
        
        metadata = admin_client.describe_topics()
        topics = list(metadata.keys())
        
        for topic in sorted(topics):
            partitions = len(metadata[topic].partitions)
            print(f"   - {topic} ({partitions} partitions)")
            
    except Exception as e:
        print(f"❌ Failed to list topics: {e}")

def test_consumer():
    """Test consuming messages from the topic"""
    print(f"👂 Testing consumer for topic: {TOPIC_NAME}")
    
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=[KAFKA_BROKER],
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=5000  # 5 second timeout
        )
        
        print("✅ Consumer created successfully!")
        print("   Listening for messages (5 second timeout)...")
        
        message_count = 0
        for message in consumer:
            print(f"   📨 Received message from partition {message.partition}, offset {message.offset}")
            print(f"       Station ID: {message.value.get('station_id', 'N/A')}")
            message_count += 1
            if message_count >= 3:  # Show first 3 messages
                break
                
        if message_count == 0:
            print("   ℹ️ No messages received (topic may be empty)")
            
        consumer.close()
        
    except Exception as e:
        print(f"❌ Failed to test consumer: {e}")

if __name__ == "__main__":
    print("🚀 Kafka Infrastructure Test")
    print("=" * 50)
    
    # Test connectivity
    if not test_kafka_connection():
        print("\n❌ Cannot proceed - Kafka connection failed!")
        exit(1)
    
    print("\n" + "=" * 50)
    
    # Create topic
    create_topic()
    
    print("\n" + "=" * 50)
    
    # List topics
    list_topics()
    
    print("\n" + "=" * 50)
    
    # Test consumer
    test_consumer()
    
    print("\n✅ Kafka infrastructure test completed!")
    print("\n🚀 You can now run the producer with:")
    print("   docker-compose up --build -d")
