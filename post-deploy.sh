#!/bin/bash
# Post-Deployment Configuration Script

echo "=== Post-Deployment Configuration ==="

# 1. Check running containers
echo "Step 1: Checking running containers..."
docker ps --format "table {{.Names}}\t{{.Status}}"

# 2. Configure firewall (UFW)
echo ""
echo "Step 2: Configuring firewall..."
ufw allow 3000/tcp   # Grafana
ufw allow 8082/tcp   # Flink Dashboard
ufw allow 9004/tcp   # Kafdrop
ufw allow 8000/tcp   # FastAPI
ufw allow 22/tcp     # SSH (ensure we don't lock ourselves out)
ufw --force enable
echo "✓ Firewall configured"

# 3. Start data generator
echo ""
echo "Step 3: Starting data generator..."
cd /opt/tire-data-pipelines
docker exec tire-data-pipelines-fastapi-1 python -c "
import sys
sys.path.append('/app')
from data_generator import generate_tire_data
import time

print('Starting data generator...')
while True:
    try:
        generate_tire_data()
        time.sleep(5)  # Generate data every 5 seconds
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f'Error: {e}')
        time.sleep(5)
" &

GENERATOR_PID=$!
echo "✓ Data generator started (PID: $GENERATOR_PID)"

# 4. Check Flink jobs
echo ""
echo "Step 4: Checking Flink jobs..."
docker exec flink-jobmanager ./bin/flink list

echo ""
echo "=== Configuration Complete! ==="
echo ""
echo "Services are accessible at:"
echo "  - Grafana: http://185.241.7.158:3000"
echo "  - Flink: http://185.241.7.158:8082"
echo "  - Kafdrop: http://185.241.7.158:9004"
echo "  - FastAPI: http://185.241.7.158:8000/docs"
echo ""
echo "Data generator is running in the background."
echo "To stop it: kill $GENERATOR_PID"
