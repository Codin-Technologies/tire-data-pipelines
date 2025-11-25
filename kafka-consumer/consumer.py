import json
import logging
from kafka import KafkaConsumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def consume_topic(topic_name):
    consumer = KafkaConsumer(
        topic_name,
        bootstrap_servers='kafka:9092',
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    logger.info(f"Starting Kafka consumer for topic: {topic_name}")
    
    try:
        for message in consumer:
            data = message.value
            logger.info(f"📨 Received from {topic_name}: {data}")
            
    except KeyboardInterrupt:
        logger.info("Stopping consumer...")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        consumer.close()

if __name__ == "__main__":
    # Consume from tire.raw topic
    consume_topic('tire.raw')