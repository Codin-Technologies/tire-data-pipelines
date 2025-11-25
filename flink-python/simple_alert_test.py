from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.common import SimpleStringSchema
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    # Add Kafka connector
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-3.0.2-1.18.jar")
    
    # Create Kafka consumer
    kafka_consumer = FlinkKafkaConsumer(
        topics='tire.raw',
        deserialization_schema=SimpleStringSchema(),
        properties={
            'bootstrap.servers': 'kafka:9092',
            'group.id': 'simple-test-group',
            'auto.offset.reset': 'earliest'
        }
    )
    
    # Create data stream
    data_stream = env.add_source(kafka_consumer)
    
    # Simple processing - just parse and log
    def process_message(message):
        try:
            data = json.loads(message)
            logger.info(f"Received: {data}")
            
            # Simple alert detection
            if data.get('pressure_kpa', 0) < 180:
                logger.warning(f"LOW PRESSURE ALERT: {data['sensor_id']} - {data['pressure_kpa']} kPa")
            elif data.get('temperature_c', 0) > 80:
                logger.warning(f"HIGH TEMP ALERT: {data['sensor_id']} - {data['temperature_c']}°C")
                
            return message
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    processed_stream = data_stream.map(process_message)
    
    logger.info("Starting simple alert test job...")
    env.execute("Simple Alert Test")

if __name__ == "__main__":
    main()