import json
import time
import random
import logging
from kafka import KafkaProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def produce_test_data():
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',  # Use container name
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    vehicles = ['V001', 'V002', 'V003']
    positions = ['FL', 'FR', 'RL', 'RR']
    
    logger.info("Starting Kafka producer inside Docker container...")
    logger.info("Producing test data to tire.raw topic")
    
    try:
        message_count = 0
        while True:
            vehicle = random.choice(vehicles)
            position = random.choice(positions)
            
            # 30% chance of problematic data to trigger alerts
            if random.random() < 0.3:
                pressure = random.uniform(150, 350)
                temperature = random.uniform(75, 95)
            else:
                pressure = random.uniform(200, 280)
                temperature = random.uniform(65, 78)
            
            data = {
                'sensor_id': f"{vehicle}-{position}",
                'vehicle_id': vehicle,
                'timestamp': int(time.time() * 1000),
                'pressure_kpa': round(pressure, 2),
                'temperature_c': round(temperature, 2),
                'battery_voltage': round(random.uniform(2.8, 3.4), 2)
            }
            
            producer.send('tire.raw', value=data)
            message_count += 1
            logger.info(f"Message {message_count}: Produced to tire.raw - Pressure: {data['pressure_kpa']} kPa, Temp: {data['temperature_c']}°C")
            
            time.sleep(3)  # Send every 3 seconds
    
    except KeyboardInterrupt:
        logger.info("Stopping producer...")
    except Exception as e:
        logger.error(f"Producer error: {e}")
    finally:
        producer.flush()
        producer.close()
        logger.info("Producer stopped.")

if __name__ == "__main__":
    produce_test_data()