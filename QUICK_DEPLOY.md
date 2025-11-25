# Quick Deployment Commands
# Copy and paste these commands one by one into your SSH session

# 1. SSH into your server
ssh root@185.241.7.158

# 2. Update system and install Git
apt-get update -y && apt-get install -y git curl

# 3. Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl start docker
systemctl enable docker

# 4. Verify installations
docker --version
docker compose version
git --version

# 5. Clone the repository
cd /opt
git clone https://github.com/Codin-Technologies/tire-data-pipelines.git
cd tire-data-pipelines

# 6. Start all services
docker compose up --build -d

# 7. Wait for services to start (60 seconds)
sleep 60

# 8. Submit Flink jobs
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/aggregator.py
sleep 10
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/alert_processor.py

# 9. Verify deployment
docker ps
docker exec flink-jobmanager ./bin/flink list

# 10. Check logs if needed
# docker compose logs -f

echo "Deployment complete!"
echo "Access Grafana at: http://185.241.7.158:3000 (admin/admin123)"
echo "Access Flink Dashboard at: http://185.241.7.158:8082"
