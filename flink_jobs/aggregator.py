from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer
from pyflink.common.serialization import SimpleStringSchema
import json

env = StreamExecutionEnvironment.get_execution_environment()

kafka_consumer = FlinkKafkaConsumer(
    topics='tire.raw',  # or 'tire.alerts' if alerts
    deserialization_schema=SimpleStringSchema(),
    properties={
        'bootstrap.servers': 'kafka:9092',
        'group.id': 'flink-consumer'
    }
)

data_stream = env.add_source(kafka_consumer)

# Example: parse JSON and map fields
def parse_json(msg):
    return json.loads(msg)

parsed_stream = data_stream.map(parse_json)

# Example: detect alerts
def detect_alert(record):
    if record['pressure_psi'] < 90 or record['temperature_c'] > 80:
        return {'vehicle_id': record['vehicle_id'], 'alert': 'Check tire'}
    return None

alerts_stream = parsed_stream.map(detect_alert).filter(lambda x: x is not None)

# Send alerts back to Kafka
from pyflink.datastream.connectors.kafka import FlinkKafkaProducer
producer = FlinkKafkaProducer(
    topic='tire.alerts',
    serialization_schema=SimpleStringSchema(),
    producer_config={'bootstrap.servers': 'kafka:9092'}
)

alerts_stream.add_sink(producer)

env.execute("Tire Alert Detection")
