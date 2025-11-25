import json
import uuid
from datetime import datetime
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer
from pyflink.datastream.connectors import JdbcSink, JdbcConnectionOptions, JdbcExecutionOptions
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
from pyflink.common import Row

# ------------------------------------
# Helper logic
# ------------------------------------

def detect_and_format_alert(record):
    """Detect alerts and format for both Kafka and Postgres"""
    try:
        data = json.loads(record)
        
        vehicle_id = data.get("vehicle_id")
        sensor_id = data.get("sensor_id")
        pressure_kpa = float(data.get("pressure_kpa"))
        temperature = float(data.get("temperature_c"))
        timestamp_ms = data.get("timestamp")
        
        # Convert timestamp from ms to datetime
        timestamp_dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
        
        alert = None
        
        # Rule 1: LOW PRESSURE (< 200 kPa)
        if pressure_kpa < 200:
            alert_id = f"{sensor_id}-LP-{timestamp_ms}"
            alert = Row(
                alert_id,
                sensor_id,
                vehicle_id,
                timestamp_dt.isoformat(),
                "LOW_PRESSURE",
                "HIGH" if pressure_kpa < 180 else "MEDIUM",
                f"Pressure {pressure_kpa:.1f} kPa is below threshold 200 kPa",
                pressure_kpa
            )
        
        # Rule 2: HIGH TEMPERATURE (> 90°C)
        elif temperature > 90:
            alert_id = f"{sensor_id}-HT-{timestamp_ms}"
            alert = Row(
                alert_id,
                sensor_id,
                vehicle_id,
                timestamp_dt.isoformat(),
                "HIGH_TEMPERATURE",
                "HIGH" if temperature > 95 else "MEDIUM",
                f"Temperature {temperature:.1f}°C is above threshold 90°C",
                temperature
            )
        
        return alert
        
    except Exception as e:
        return None


def create_alerts_jdbc_sink():
    """Create JDBC sink for tire_alerts table"""
    return JdbcSink.sink(
        sql="""INSERT INTO tire_alerts 
               (alert_id, sensor_id, vehicle_id, timestamp, alert_type, severity, description, triggering_value) 
               VALUES (?, ?, ?, ?::timestamp, ?, ?, ?, ?)
               ON CONFLICT (alert_id) DO NOTHING""",
        type_info=Types.ROW([
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
            .with_batch_interval_ms(5000)
            .with_batch_size(100)
            .with_max_retries(3)
            .build()
    )


# ------------------------------------
# FLINK JOB
# ------------------------------------

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    # Add required JARs
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-3.0.2-1.18.jar")
    env.add_jars("file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar")
    env.add_jars("file:///opt/flink/lib/postgresql-42.6.0.jar")

    # Kafka consumer
    consumer_props = {
        "bootstrap.servers": "kafka:9092",
        "group.id": "flink-alert-processor"
    }

    consumer = FlinkKafkaConsumer(
        topics="tire.raw",
        deserialization_schema=SimpleStringSchema(),
        properties=consumer_props
    )

    # Kafka producer for alerts (JSON strings)
    producer_props = {"bootstrap.servers": "kafka:9092"}
    kafka_producer = FlinkKafkaProducer(
        topic="tire.alerts",
        serialization_schema=SimpleStringSchema(),
        producer_config=producer_props
    )

    # Create JDBC sink
    jdbc_sink = create_alerts_jdbc_sink()
    
    # Define Row type for Postgres sink
    row_type_info = Types.ROW([
        Types.STRING(),  # alert_id
        Types.STRING(),  # sensor_id
        Types.STRING(),  # vehicle_id
        Types.STRING(),  # timestamp
        Types.STRING(),  # alert_type
        Types.STRING(),  # severity
        Types.STRING(),  # description
        Types.FLOAT()    # triggering_value
    ])

    stream = env.add_source(consumer)
    
    # Process alerts into Row objects
    alerts_row = stream.map(detect_and_format_alert, output_type=row_type_info)
    
    # Filter out None rows
    alerts_row = alerts_row.filter(lambda x: x is not None)
    
    # Write to Postgres
    alerts_row.add_sink(jdbc_sink)
    
    # Convert Row to JSON string for Kafka
    alerts_json = alerts_row.map(
        lambda r: json.dumps({
            "alert_id": r[0],
            "sensor_id": r[1],
            "vehicle_id": r[2],
            "timestamp": r[3],
            "alert_type": r[4],
            "severity": r[5],
            "description": r[6],
            "triggering_value": r[7]
        }),
        output_type=Types.STRING()
    )
    
    # Publish to Kafka
    alerts_json.add_sink(kafka_producer)

    # Execute Flink Job
    env.execute("Tire Alert Processor")


if __name__ == "__main__":
    main()
