# Server Deployment Guide

## Prerequisites
- Server: 185.241.7.158
- OS: Ubuntu/Debian (assumed)
- Root access

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

1. **SSH into your server**:
   ```bash
   ssh root@185.241.7.158
   ```

2. **Download and run the deployment script**:
   ```bash
   # If you've pushed deploy.sh to GitHub
   curl -O https://raw.githubusercontent.com/Codin-Technologies/tire-data-pipelines/main/deploy.sh
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```

### Option 2: Manual Deployment

#### Step 1: SSH into Server
```bash
ssh root@185.241.7.158
```

#### Step 2: Install Git
```bash
apt-get update -y
apt-get install -y git
git --version
```

#### Step 3: Install Docker
```bash
# Install prerequisites
apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Verify installation
docker --version
docker compose version
```

#### Step 4: Clone the Repository
```bash
cd /opt
git clone https://github.com/Codin-Technologies/tire-data-pipelines.git
cd tire-data-pipelines
```

#### Step 5: Start the Services
```bash
# Build and start all services
docker compose up --build -d

# Wait for services to initialize (30-60 seconds)
sleep 30

# Check running containers
docker ps
```

#### Step 6: Submit Flink Jobs
```bash
# Submit Aggregator job
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/aggregator.py

# Wait a few seconds
sleep 10

# Submit Alert Processor job
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/alert_processor.py
```

#### Step 7: Verify Deployment
```bash
# Check Flink jobs
docker exec flink-jobmanager ./bin/flink list

# Check container logs
docker compose logs -f flink-jobmanager
```

## Accessing Services

After deployment, access the services at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://185.241.7.158:3000 | admin / admin123 |
| **Flink Dashboard** | http://185.241.7.158:8082 | N/A |
| **Kafdrop (Kafka UI)** | http://185.241.7.158:9004 | N/A |
| **FastAPI** | http://185.241.7.158:8000/docs | N/A |

## Firewall Configuration

If you have a firewall enabled, open the required ports:

```bash
# UFW (Ubuntu Firewall)
ufw allow 3000/tcp   # Grafana
ufw allow 8082/tcp   # Flink Dashboard
ufw allow 9004/tcp   # Kafdrop
ufw allow 8000/tcp   # FastAPI
ufw reload
```

## Troubleshooting

### Check Service Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs -f flink-jobmanager
docker compose logs -f postgres
docker compose logs -f kafka
```

### Restart Services
```bash
docker compose restart
```

### Stop All Services
```bash
docker compose down
```

### Update Deployment
```bash
cd /opt/tire-data-pipelines
git pull
docker compose down
docker compose up --build -d
# Re-submit Flink jobs (see Step 6)
```

## Post-Deployment Checklist

- [ ] All containers are running (`docker ps`)
- [ ] Flink jobs are running (check http://185.241.7.158:8082)
- [ ] Grafana dashboard is accessible (http://185.241.7.158:3000)
- [ ] Data is flowing to PostgreSQL (check Grafana charts)
- [ ] Alerts are being generated (check `tire_alerts` table)

## Security Recommendations

1. **Change default passwords** in `docker-compose.yml`:
   - Grafana: `GF_SECURITY_ADMIN_PASSWORD`
   - PostgreSQL: `POSTGRES_PASSWORD`

2. **Set up SSL/TLS** for production:
   - Use a reverse proxy (nginx) with Let's Encrypt certificates
   - Configure HTTPS for Grafana and FastAPI

3. **Configure firewall rules** to restrict access to trusted IPs

4. **Set up SSH key authentication** and disable password login

5. **Regular backups** of PostgreSQL data:
   ```bash
   docker exec project-root-postgres-1 pg_dump -U admin tire_db > backup.sql
   ```
