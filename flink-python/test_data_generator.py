import json
import time
import random
from kafka import KafkaProducer
import sys

def generate_test_data():
    producer = KafkaProducer(
        bootstrap_servers='kafka:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    vehicles = ['V001', 'V002', 'V003']
    positions = ['FL', 'FR', 'RL', 'RR']
    
    print("Generating test tire data for Airflow pipeline...")
    
    for i in range(10):  # Generate 10 messages
        vehicle = random.choice(vehicles)
        position = random.choice(positions)
        
        # Create a mix of data types
        if i % 4 == 0:
            pressure = random.uniform(150, 179)  # Low pressure
            temperature = random.uniform(70, 78)
        elif i % 4 == 1:
            pressure = random.uniform(301, 350)  # High pressure
            temperature = random.uniform(70, 78)
        elif i % 4 == 2:
            pressure = random.uniform(200, 280)
            temperature = random.uniform(81, 95)  # High temperature
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
        alert_status = "ALERT" if pressure < 180 or pressure > 300 or temperature > 80 else "NORMAL"
        print(f"Message {i+1}: {alert_status} - {data['sensor_id']}")
        time.sleep(1)
    
    producer.flush()
    print("Test data generation completed!")
    return True

if __name__ == "__main__":
    try:
        success = generate_test_data()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error generating test data: {e}")
        sys.exit(1)