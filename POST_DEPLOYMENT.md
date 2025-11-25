# Post-Deployment Steps - IMPORTANT!

After deploying to your server, you need to complete these steps to make services accessible and start generating data.

## Step 1: SSH into Your Server
```bash
ssh root@185.241.7.158
# Password: Codinourvps@2025
```

## Step 2: Configure Firewall (Allow Access to Services)

Run these commands to open the required ports:

```bash
# Allow service ports
ufw allow 3000/tcp   # Grafana
ufw allow 8082/tcp   # Flink Dashboard
ufw allow 9004/tcp   # Kafdrop (Kafka UI)
ufw allow 8000/tcp   # FastAPI
ufw allow 22/tcp     # SSH (don't lock yourself out!)

# Enable firewall
ufw --force enable

# Check firewall status
ufw status
```

## Step 3: Check Running Services

```bash
cd /opt/tire-data-pipelines
docker ps
```

All containers should show "Up" status. If any are missing or unhealthy, run:
```bash
docker compose up -d
```

## Step 4: Start the Data Generator

The data generator produces simulated tire sensor data to Kafka. Run this command:

```bash
cd /opt/tire-data-pipelines
docker exec -d tire-data-pipelines-fastapi-1 python -c "
import sys
sys.path.append('/app')
from data_generator import generate_tire_data
import time

print('Data generator started')
while True:
    try:
        generate_tire_data()
        time.sleep(5)
    except Exception as e:
        print(f'Error: {e}')
        time.sleep(5)
"
```

**Alternative**: If the above doesn't work, you can use the FastAPI endpoint:
```bash
# Start generating data via API
curl -X POST http://localhost:8000/generate-data/start
```

## Step 5: Verify Everything is Working

### Check Flink Jobs
```bash
docker exec flink-jobmanager ./bin/flink list
```

You should see 2 running jobs:
- Tire Aggregator
- Tire Alert Processor

### Check Kafka Topics
```bash
docker exec tire-data-pipelines-kafka-1 kafka-topics --list --bootstrap-server localhost:9092
```

You should see:
- `tire.raw`
- `tire.alerts`

### Check Data in PostgreSQL
```bash
docker exec tire-data-pipelines-postgres-1 psql -U admin -d tire_db -c "SELECT count(*) FROM tire_aggregations;"
```

After a few minutes, you should see data accumulating.

## Step 6: Access Your Services

Now you can access the services from your browser:

- **Grafana**: http://185.241.7.158:3000 (admin/admin123)
- **Flink Dashboard**: http://185.241.7.158:8082
- **Kafdrop**: http://185.241.7.158:9004
- **FastAPI Docs**: http://185.241.7.158:8000/docs

## Troubleshooting

### Services still not accessible?
1. Check if UFW is active: `ufw status`
2. Check if ports are listening: `netstat -tulpn | grep -E '3000|8082|9004|8000'`
3. Check cloud provider firewall (if applicable)

### No data in Grafana?
1. Wait 2-3 minutes for data to accumulate
2. Check if data generator is running: `docker logs tire-data-pipelines-fastapi-1`
3. Check Kafka for messages: `docker exec tire-data-pipelines-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic tire.raw --from-beginning --max-messages 5`

### Flink jobs not running?
```bash
# Check Flink logs
docker logs flink-jobmanager
docker logs flink-taskmanager

# Resubmit jobs if needed
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/aggregator.py
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/alert_processor.py
```

## Quick Reference Commands

```bash
# Restart all services
cd /opt/tire-data-pipelines
docker compose restart

# View logs
docker compose logs -f [service-name]

# Stop all services
docker compose down

# Start all services
docker compose up -d
```
