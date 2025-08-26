import os
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from influxdb_client import InfluxDBClient
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# InfluxDB Configuration
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "data-infra-super-secret-auth-token-2025")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "data-infra-org")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "citi-bike-data")

# Detection Configuration
DETECTION_INTERVAL = int(os.environ.get("DETECTION_INTERVAL", "60"))  # seconds
LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", "15"))  # how far back to look for trends

@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    station_id: str
    anomaly_type: str
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    timestamp: datetime
    current_value: Any
    expected_range: Optional[str] = None
    action_required: Optional[str] = None

class CitiBikeAnomalyDetector:
    """
    Real-time anomaly detector for Citi Bike stations using InfluxDB.
    Runs detection every minute and identifies operational issues.
    """
    
    def __init__(self):
        self.setup_influxdb_client()
        self.anomalies_buffer = []
        
    def setup_influxdb_client(self):
        """Initialize InfluxDB client"""
        logger.info(f"Connecting to InfluxDB: {INFLUXDB_URL}")
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.query_api = self.influx_client.query_api()
        logger.info("✅ InfluxDB client initialized successfully")
    
    def run_detection_cycle(self):
        """Run one complete anomaly detection cycle"""
        logger.info("🔍 Starting anomaly detection cycle...")
        
        try:
            # Get current station states
            current_states = self.get_current_station_states()
            logger.info(f"Retrieved data for {len(current_states)} stations")
            
            # Run different anomaly detection methods
            anomalies = []
            anomalies.extend(self.detect_capacity_issues(current_states))
            anomalies.extend(self.detect_station_health_issues(current_states))
            anomalies.extend(self.detect_rapid_state_changes(current_states))
            
            # Process and output anomalies
            if anomalies:
                self.handle_anomalies(anomalies)
            else:
                logger.info("✅ No anomalies detected")
                
        except Exception as e:
            logger.error(f"❌ Error in detection cycle: {e}")
    
    def get_current_station_states(self) -> List[Dict]:
        """Get the most recent state for all stations"""
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "station_status")
          |> group(columns: ["station_id"])
          |> last()
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        result = self.query_api.query(query)
        stations = []
        
        for table in result:
            for record in table.records:
                station_data = {
                    'station_id': record.values.get('station_id'),
                    'timestamp': record.get_time(),
                    'num_bikes_available': record.values.get('num_bikes_available', 0),
                    'num_docks_available': record.values.get('num_docks_available', 0),
                    'num_bikes_disabled': record.values.get('num_bikes_disabled', 0),
                    'num_docks_disabled': record.values.get('num_docks_disabled', 0),
                    'is_renting': record.values.get('is_renting') == 'True',
                    'is_returning': record.values.get('is_returning') == 'True',
                    'is_installed': record.values.get('is_installed') == 'True',
                    'last_reported': record.values.get('last_reported', 0)
                }
                stations.append(station_data)
        
        return stations
    
    def detect_capacity_issues(self, stations: List[Dict]) -> List[Anomaly]:
        """Detect stations that are empty, full, or approaching capacity limits"""
        anomalies = []
        
        for station in stations:
            station_id = station['station_id']
            bikes_available = station['num_bikes_available']
            docks_available = station['num_docks_available']
            
            # Calculate total capacity
            total_capacity = bikes_available + docks_available + \
                           station['num_bikes_disabled'] + station['num_docks_disabled']
            
            if total_capacity == 0:
                continue  # Skip invalid data
            
            # Critical: Station completely empty
            if bikes_available == 0 and station['is_renting']:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="STATION_EMPTY",
                    severity="CRITICAL",
                    message=f"Station {station_id} is completely empty (0 bikes available)",
                    timestamp=station['timestamp'],
                    current_value=bikes_available,
                    action_required="URGENT: Dispatch bikes for rebalancing"
                ))
            
            # Critical: Station completely full
            elif docks_available == 0 and station['is_returning']:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="STATION_FULL",
                    severity="CRITICAL",
                    message=f"Station {station_id} is completely full (0 docks available)",
                    timestamp=station['timestamp'],
                    current_value=docks_available,
                    action_required="URGENT: Remove bikes to free up docks"
                ))
            
            # Warning: Station nearly empty (< 20% bikes)
            elif bikes_available / total_capacity < 0.2 and station['is_renting']:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="STATION_LOW",
                    severity="WARNING",
                    message=f"Station {station_id} is running low ({bikes_available}/{total_capacity} bikes)",
                    timestamp=station['timestamp'],
                    current_value=bikes_available,
                    expected_range="20-80% of capacity",
                    action_required="Plan bike rebalancing"
                ))
            
            # Warning: Station nearly full (< 20% docks)
            elif docks_available / total_capacity < 0.2 and station['is_returning']:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="STATION_HIGH",
                    severity="WARNING",
                    message=f"Station {station_id} is nearly full ({docks_available}/{total_capacity} docks available)",
                    timestamp=station['timestamp'],
                    current_value=docks_available,
                    expected_range="20-80% of capacity",
                    action_required="Plan bike removal"
                ))
        
        return anomalies
    
    def detect_station_health_issues(self, stations: List[Dict]) -> List[Anomaly]:
        """Detect stations with operational/health issues"""
        anomalies = []
        current_time = datetime.utcnow()
        
        for station in stations:
            station_id = station['station_id']
            
            # Critical: Station not accepting rentals
            if not station['is_renting'] and station['is_installed']:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="STATION_NOT_RENTING",
                    severity="CRITICAL",
                    message=f"Station {station_id} is not accepting bike rentals",
                    timestamp=station['timestamp'],
                    current_value=False,
                    action_required="Check station status and repair if needed"
                ))
            
            # Critical: Station not accepting returns
            if not station['is_returning'] and station['is_installed']:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="STATION_NOT_RETURNING",
                    severity="CRITICAL",
                    message=f"Station {station_id} is not accepting bike returns",
                    timestamp=station['timestamp'],
                    current_value=False,
                    action_required="Check station status and repair if needed"
                ))
            
            # Critical: Station not installed
            if not station['is_installed']:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="STATION_OFFLINE",
                    severity="CRITICAL",
                    message=f"Station {station_id} is marked as not installed/offline",
                    timestamp=station['timestamp'],
                    current_value=False,
                    action_required="Check station installation and connectivity"
                ))
            
            # Warning: High number of disabled bikes
            total_bikes = station['num_bikes_available'] + station['num_bikes_disabled']
            if total_bikes > 0 and station['num_bikes_disabled'] / total_bikes > 0.3:
                anomalies.append(Anomaly(
                    station_id=station_id,
                    anomaly_type="HIGH_DISABLED_BIKES",
                    severity="WARNING",
                    message=f"Station {station_id} has high number of disabled bikes ({station['num_bikes_disabled']}/{total_bikes})",
                    timestamp=station['timestamp'],
                    current_value=station['num_bikes_disabled'],
                    expected_range="< 30% of total bikes",
                    action_required="Schedule bike maintenance"
                ))
            
            # Warning: Stale data (no updates in last 10 minutes)
            if station['last_reported'] > 0:
                last_report_time = datetime.fromtimestamp(station['last_reported'])
                time_diff = (current_time - last_report_time).total_seconds()
                if time_diff > 600:  # 10 minutes
                    anomalies.append(Anomaly(
                        station_id=station_id,
                        anomaly_type="STALE_DATA",
                        severity="WARNING",
                        message=f"Station {station_id} has not reported data for {int(time_diff/60)} minutes",
                        timestamp=station['timestamp'],
                        current_value=f"{int(time_diff/60)} minutes ago",
                        action_required="Check station communication"
                    ))
        
        return anomalies
    
    def detect_rapid_state_changes(self, stations: List[Dict]) -> List[Anomaly]:
        """Detect stations with unusually rapid changes in bike/dock availability"""
        # This will be implemented in the next step with trend analysis
        anomalies = []
        
        # TODO: Implement rapid change detection by comparing with historical data
        # For now, return empty list - we'll add this in step 3
        
        return anomalies
    
    def handle_anomalies(self, anomalies: List[Anomaly]):
        """Process and output detected anomalies"""
        # Sort by severity
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        anomalies.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        logger.info(f"🚨 Detected {len(anomalies)} anomalies:")
        
        for anomaly in anomalies:
            severity_emoji = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}
            emoji = severity_emoji.get(anomaly.severity, "⚪")
            
            logger.info(f"{emoji} [{anomaly.severity}] {anomaly.message}")
            if anomaly.action_required:
                logger.info(f"   Action: {anomaly.action_required}")
        
        # Store anomalies for further processing (dashboard, alerts, etc.)
        self.store_anomalies(anomalies)
    
    def store_anomalies(self, anomalies: List[Anomaly]):
        """Store anomalies for later analysis and alerting"""
        # For now, just log to console. Later we can add:
        # - Database storage
        # - Alert system integration  
        # - Dashboard updates
        # - Email/SMS notifications
        
        anomaly_data = []
        for anomaly in anomalies:
            anomaly_data.append({
                'timestamp': anomaly.timestamp.isoformat(),
                'station_id': anomaly.station_id,
                'type': anomaly.anomaly_type,
                'severity': anomaly.severity,
                'message': anomaly.message,
                'current_value': anomaly.current_value,
                'action_required': anomaly.action_required
            })
        
        # Save to file for now (can be replaced with proper alerting system)
        with open('anomalies.json', 'a') as f:
            for anomaly in anomaly_data:
                f.write(json.dumps(anomaly) + '\n')
    
    def run(self):
        """Main detection loop"""
        logger.info("🚀 Starting Citi Bike Anomaly Detector...")
        logger.info(f"   Detection Interval: {DETECTION_INTERVAL} seconds")
        logger.info(f"   InfluxDB Bucket: {INFLUXDB_BUCKET}")
        
        try:
            while True:
                start_time = time.time()
                
                # Run detection cycle
                self.run_detection_cycle()
                
                # Calculate sleep time to maintain consistent interval
                execution_time = time.time() - start_time
                sleep_time = max(0, DETECTION_INTERVAL - execution_time)
                
                logger.info(f"Detection cycle completed in {execution_time:.2f}s, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"❌ Fatal error in anomaly detector: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up resources...")
        if hasattr(self, 'influx_client'):
            self.influx_client.close()
            logger.info("InfluxDB client closed")
        logger.info("✅ Cleanup completed")

if __name__ == "__main__":
    detector = CitiBikeAnomalyDetector()
    detector.run()
