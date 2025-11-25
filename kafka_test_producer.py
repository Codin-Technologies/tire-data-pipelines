import json
import time
import random
from kafka import KafkaProducer

def produce_test_data():
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    vehicles = ['V001', 'V002', 'V003']
    positions = ['FL', 'FR', 'RL', 'RR']  # Front-Left, Front-Right, Rear-Left, Rear-Right
    
    print("Producing test data to Kafka... Press Ctrl+C to stop.")
    
    try:
        while True:
            vehicle = random.choice(vehicles)
            position = random.choice(positions)
            
            # Occasionally generate alert-triggering data
            if random.random() < 0.3:  # 30% chance of problematic data
                pressure = random.uniform(150, 350)  # Sometimes too low/high
                temperature = random.uniform(75, 95)  # Sometimes too high
            else:
                pressure = random.uniform(200, 280)   # Normal range
                temperature = random.uniform(65, 78)  # Normal range
            
            data = {
                'sensor_id': f"{vehicle}-{position}",
                'vehicle_id': vehicle,
                'timestamp': int(time.time() * 1000),
                'pressure_kpa': round(pressure, 2),
                'temperature_c': round(temperature, 2),
                'battery_voltage': round(random.uniform(2.8, 3.4), 2)
            }
            
            producer.send('tire.raw', value=data)
            print(f"Produced: {data}")
            time.sleep(2)  # Send every 2 seconds
    
    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.flush()
        producer.close()
        print("Producer stopped.")

if __name__ == "__main__":
    produce_test_data()