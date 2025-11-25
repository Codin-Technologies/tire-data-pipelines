import json
import time
import random
from kafka import KafkaProducer

def produce_initial_data():
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    vehicles = ['V001', 'V002', 'V003']
    positions = ['FL', 'FR', 'RL', 'RR']
    
    print("Producing initial test data...")
    
    # Produce 10 initial messages
    for i in range(10):
        vehicle = random.choice(vehicles)
        position = random.choice(positions)
        
        # Mix of normal and alert-triggering data
        if i % 3 == 0:  # Every 3rd message has issues
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
        print(f"Produced: {data}")
        time.sleep(1)
    
    producer.flush()
    producer.close()
    print("Initial test data production completed!")

if __name__ == "__main__":
    produce_initial_data()