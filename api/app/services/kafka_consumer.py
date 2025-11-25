import os, json
from kafka import KafkaConsumer
from ..database import SessionLocal
from ..models import TireData
from datetime import datetime

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "tire_data"

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda m: json.loads(m.decode("utf-8"))
)

def consume():
    db = SessionLocal()
    for message in consumer:
        data = message.value
        tire = TireData(
            tire_id=data["tire_id"],
            pressure=data["pressure"],
            temperature=data["temperature"],
            timestamp=datetime.fromtimestamp(float(data["timestamp"]))
        )
        db.add(tire)
        db.commit()
        print("Saved:", data)

if __name__ == "__main__":
    consume()
