from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors import FlinkKafkaConsumer, JdbcSink, JdbcConnectionOptions, JdbcExecutionOptions
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.datastream.functions import ProcessWindowFunction
from pyflink.common import SimpleStringSchema, WatermarkStrategy, Time, Row
from pyflink.common.typeinfo import Types
import json
import logging
from datetime import datetime
from typing import Iterable

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TireDataDeserializer(SimpleStringSchema):
    def deserialize(self, message: str) -> str:
        try:
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

class TireAggregationWindowFunction(ProcessWindowFunction):
    def process(self, key, context: ProcessWindowFunction.Context, elements: Iterable) -> Iterable:
        try:
            sensor_id, vehicle_id = key
            window_start = context.window().start
            window_end = context.window().end
            
            pressures = []
            temperatures = []
            
            for element in elements:
                data = json.loads(element)
                pressures.append(data['pressure_kpa'])
                temperatures.append(data['temperature_c'])
            
            if pressures and temperatures:
                aggregation = {
                    'sensor_id': sensor_id,
                    'vehicle_id': vehicle_id,
                    'window_start': window_start,
                    'window_end': window_end,
                    'window_size': '1m',
                    'avg_pressure': sum(pressures) / len(pressures),
                    'avg_temperature': sum(temperatures) / len(temperatures),
                    'min_pressure': min(pressures),
                    'max_pressure': max(pressures),
                    'min_temperature': min(temperatures),
                    'max_temperature': max(temperatures),
                    'record_count': len(pressures)
                }
                logger.info(f"Generated aggregation: {aggregation}")
                yield aggregation
                
        except Exception as e:
            logger.error(f"Error in aggregation: {e}")

def create_aggregation_jdbc_sink():
    """Create JDBC sink for aggregations"""
    return JdbcSink.sink(
        sql="""INSERT INTO tire_aggregations 
               (sensor_id, vehicle_id, window_start, window_end, window_size, 
                avg_pressure, avg_temperature, min_pressure, max_pressure, 
                min_temperature, max_temperature, record_count) 
               VALUES (?, ?, to_timestamp(?::bigint/1000), to_timestamp(?::bigint/1000), ?, ?, ?, ?, ?, ?, ?, ?)""",
        type_info=Types.ROW([
            Types.STRING(),  # sensor_id
            Types.STRING(),  # vehicle_id
            Types.STRING(),  # window_start
            Types.STRING(),  # window_end
            Types.STRING(),  # window_size
            Types.FLOAT(),   # avg_pressure
            Types.FLOAT(),   # avg_temperature
            Types.FLOAT(),   # min_pressure
            Types.FLOAT(),   # max_pressure
            Types.FLOAT(),   # min_temperature
            Types.FLOAT(),   # max_temperature
            Types.INT()      # record_count
        ]),
        jdbc_connection_options=JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
            .with_url('jdbc:postgresql://postgres:5432/tire_db')
            .with_driver_name('org.postgresql.Driver')
            .with_user_name('admin')
            .with_password('admin123')
            .build(),
        jdbc_execution_options=JdbcExecutionOptions.builder()
            .with_batch_interval_ms(5000)
            .with_batch_size(1000)
            .with_max_retries(3)
            .build()
    )

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    # Add dependencies
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-3.0.2-1.18.jar")
    env.add_jars("file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar")
    env.add_jars("file:///opt/flink/lib/postgresql-42.6.0.jar")
    
    # Kafka configuration
    bootstrap_servers = "kafka:9092"
    input_topic = "tire.raw"
    
    # Create Kafka consumer
    kafka_consumer = FlinkKafkaConsumer(
        topics=input_topic,
        deserialization_schema=TireDataDeserializer(),
        properties={
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'flink-aggregation-group',
            'auto.offset.reset': 'earliest'
        }
    )
    
    # Create data stream
    data_stream = env.add_source(kafka_consumer)
    
    # Key by sensor and vehicle for aggregation
    keyed_stream = data_stream \
        .key_by(lambda x: (json.loads(x)['sensor_id'], json.loads(x)['vehicle_id']))
    
    # 1-minute aggregations
    one_min_aggregations = keyed_stream \
        .window(TumblingProcessingTimeWindows.of(Time.minutes(1))) \
        .process(TireAggregationWindowFunction()) \
        .name("1min_aggregations")
    
    # Convert to JDBC format and write to PostgreSQL
    def map_to_jdbc_aggregation(agg):
        try:
            return Row(
                agg['sensor_id'],
                agg['vehicle_id'],
                str(agg['window_start']),
                str(agg['window_end']),
                agg['window_size'],
                float(agg['avg_pressure']),
                float(agg['avg_temperature']),
                float(agg['min_pressure']),
                float(agg['max_pressure']),
                float(agg['min_temperature']),
                float(agg['max_temperature']),
                int(agg['record_count'])
            )
        except Exception as e:
            logger.error(f"Error mapping aggregation to JDBC format: {e}")
            return None
    
    jdbc_sink = create_aggregation_jdbc_sink()
    
    # Define the output type for the map operation
    row_type_info = Types.ROW([
        Types.STRING(),  # sensor_id
        Types.STRING(),  # vehicle_id
        Types.STRING(),  # window_start
        Types.STRING(),  # window_end
        Types.STRING(),  # window_size
        Types.FLOAT(),   # avg_pressure
        Types.FLOAT(),   # avg_temperature
        Types.FLOAT(),   # min_pressure
        Types.FLOAT(),   # max_pressure
        Types.FLOAT(),   # min_temperature
        Types.FLOAT(),   # max_temperature
        Types.INT()      # record_count
    ])
    
    one_min_aggregations \
        .map(map_to_jdbc_aggregation, output_type=row_type_info) \
        .filter(lambda x: x is not None) \
        .name("map_aggregations_to_jdbc") \
        .add_sink(jdbc_sink) \
        .name("postgres_aggregations_sink")
    
    logger.info("Starting Flink Aggregation Job...")
    env.execute("Tire Monitoring Aggregations")

if __name__ == "__main__":
    main()