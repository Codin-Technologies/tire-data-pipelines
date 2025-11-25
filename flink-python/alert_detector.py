from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer, FlinkKafkaProducer, JdbcSink, JdbcConnectionOptions, JdbcExecutionOptions
from pyflink.common import SimpleStringSchema, WatermarkStrategy, Time
from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import ProcessFunction, RuntimeContext
from pyflink.common import Row
import json
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TireDataDeserializer(SimpleStringSchema):
    def deserialize(self, message: str) -> str:
        try:
            # Basic JSON validation
            data = json.loads(message)
            required_fields = ['sensor_id', 'vehicle_id', 'timestamp', 'pressure_kpa', 'temperature_c']
            if all(field in data for field in required_fields):
                return message
            else:
                logger.warning(f"Missing required fields in message: {message}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {message}, error: {e}")
            return None

class AlertDetectionProcessFunction(ProcessFunction):
    def __init__(self):
        self.pressure_threshold_low = 180.0  # kPa
        self.pressure_threshold_high = 300.0  # kPa
        self.temperature_threshold = 80.0  # Celsius
    
    def open(self, runtime_context: RuntimeContext):
        logger.info("Alert detection process function initialized")
    
    def process_element(self, value, ctx: 'ProcessFunction.Context'):
        try:
            data = json.loads(value)
            
            sensor_id = data['sensor_id']
            vehicle_id = data['vehicle_id']
            pressure = data['pressure_kpa']
            temperature = data['temperature_c']
            timestamp = data['timestamp']
            
            alerts = []
            
            # Check for low pressure
            if pressure < self.pressure_threshold_low:
                alerts.append({
                    'alert_type': 'LOW_PRESSURE',
                    'severity': 'HIGH',
                    'description': f'Pressure {pressure:.1f} kPa is below threshold {self.pressure_threshold_low} kPa',
                    'triggering_value': pressure
                })
            
            # Check for high pressure
            if pressure > self.pressure_threshold_high:
                alerts.append({
                    'alert_type': 'HIGH_PRESSURE', 
                    'severity': 'HIGH',
                    'description': f'Pressure {pressure:.1f} kPa is above threshold {self.pressure_threshold_high} kPa',
                    'triggering_value': pressure
                })
            
            # Check for high temperature
            if temperature > self.temperature_threshold:
                alerts.append({
                    'alert_type': 'HIGH_TEMPERATURE',
                    'severity': 'MEDIUM',
                    'description': f'Temperature {temperature:.1f}°C is above threshold {self.temperature_threshold}°C',
                    'triggering_value': temperature
                })
            
            # Emit alerts
            for alert in alerts:
                alert_id = f"{sensor_id}_{int(time.time() * 1000)}"
                alert_data = {
                    'alert_id': alert_id,
                    'sensor_id': sensor_id,
                    'vehicle_id': vehicle_id,
                    'timestamp': timestamp,
                    **alert,
                    'processed_at': datetime.now().isoformat()
                }
                logger.info(f"Generated alert: {alert_data}")
                yield json.dumps(alert_data)
                
        except Exception as e:
            logger.error(f"Error processing message: {value}, error: {e}")

def create_kafka_consumer(bootstrap_servers: str, topic: str, group_id: str):
    """Create Kafka consumer for tire data"""
    return FlinkKafkaConsumer(
        topics=topic,
        deserialization_schema=TireDataDeserializer(),
        properties={
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        }
    )

def create_kafka_producer(bootstrap_servers: str, topic: str):
    """Create Kafka producer for alerts"""
    return FlinkKafkaProducer(
        topic=topic,
        serialization_schema=SimpleStringSchema(),
        producer_config={
            'bootstrap.servers': bootstrap_servers,
            'batch.size': '16384',
            'linger.ms': '5'
        }
    )

def create_jdbc_sink():
    """Create JDBC sink for PostgreSQL"""
    return JdbcSink.sink(
        sql="""INSERT INTO tire_alerts 
               (alert_id, sensor_id, vehicle_id, timestamp, alert_type, severity, description, triggering_value) 
               VALUES (?, ?, to_timestamp(?::bigint/1000), ?, ?, ?, ?, ?)""",
        type_info=Types.ROW([  # FIXED: ROW instead of ROW_
            Types.STRING(),  # alert_id
            Types.STRING(),  # sensor_id
            Types.STRING(),  # vehicle_id
            Types.STRING(),  # timestamp
            Types.STRING(),  # alert_type
            Types.STRING(),  # severity
            Types.STRING(),  # description
            Types.FLOAT()    # triggering_value
        ]),
        jdbc_connection_options=JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
            .with_url('jdbc:postgresql://postgres:5432/tire_db')
            .with_driver_name('org.postgresql.Driver')
            .with_user_name('admin')
            .with_password('admin123')
            .build(),
        jdbc_execution_options=JdbcExecutionOptions.builder()
            .with_batch_interval_ms(1000)
            .with_batch_size(100)
            .with_max_retries(3)
            .build()
    )
def main():
    # Set up the execution environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    # Add Kafka connector dependency
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-3.0.2-1.18.jar")
    env.add_jars("file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar")
    env.add_jars("file:///opt/flink/lib/postgresql-42.6.0.jar")
    
    # Kafka configuration
    bootstrap_servers = "kafka:9092"
    input_topic = "tire.raw"
    output_topic = "tire.alerts"
    
    logger.info(f"Setting up Kafka consumer for topic: {input_topic}")
    
    # Create Kafka consumer
    kafka_consumer = create_kafka_consumer(bootstrap_servers, input_topic, "flink-alert-group")
    
    # Create data stream from Kafka
    data_stream = env.add_source(kafka_consumer)
    
    # Process data and detect alerts
    alerts_stream = data_stream \
        .process(AlertDetectionProcessFunction()) \
        .name("alert_detection")
    
    # Write alerts to Kafka
    kafka_producer = create_kafka_producer(bootstrap_servers, output_topic)
    alerts_stream.add_sink(kafka_producer).name("kafka_alerts_sink")
    
    # Write alerts to PostgreSQL
    jdbc_sink = create_jdbc_sink()
    
    # Convert alert stream to JDBC format
    def map_to_jdbc_alert(alert_json):
        try:
            alert = json.loads(alert_json)
            return Row(
                alert['alert_id'],
                alert['sensor_id'],
                alert['vehicle_id'],
                str(alert['timestamp']),
                alert['alert_type'],
                alert['severity'],
                alert['description'],
                float(alert['triggering_value'])
            )
        except Exception as e:
            logger.error(f"Error mapping alert to JDBC format: {e}")
            return None
    
    alerts_stream \
        .map(map_to_jdbc_alert) \
        .filter(lambda x: x is not None) \
        .name("map_to_jdbc_format") \
        .add_sink(jdbc_sink) \
        .name("postgres_alerts_sink")
    
    logger.info("Starting Flink Alert Detection Job...")
    env.execute("Tire Monitoring Alert Detection")

if __name__ == "__main__":
    main()