from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.common.serialization import SimpleStringSchema
import json

env = StreamExecutionEnvironment.get_execution_environment()

# Kafka Consumer
kafka_consumer = FlinkKafkaConsumer(
    topics='tire.raw',
    deserialization_schema=SimpleStringSchema(),
    properties={'bootstrap.servers': 'localhost:9092', 'group.id': 'flink-tire'}
)
stream = env.add_source(kafka_consumer)

# Simple alert: pressure < 90 or temperature > 80
def parse_alert(record):
    data = json.loads(record)
    if data['pressure_psi'] < 90 or data['temperature_c'] > 80:
        return json.dumps({'vehicle_id': data['vehicle_id'],
                           'tire_position': data['tire_position'],
                           'pressure_psi': data['pressure_psi'],
                           'temperature_c': data['temperature_c'],
                           'alert': True,
                           'timestamp': data['timestamp']})
    return None

alerts_stream = stream.map(parse_alert).filter(lambda x: x is not None)

# Kafka Producer for alerts
kafka_producer = FlinkKafkaProducer(
    topic='tire.alerts',
    serialization_schema=SimpleStringSchema(),
    producer_config={'bootstrap.servers': 'localhost:9092'}
)
alerts_stream.add_sink(kafka_producer)

env.execute("TPMS Alert Detector")
