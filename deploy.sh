#!/bin/bash
set -e

echo "=== Tire Management System - Server Deployment Script ==="
echo ""

# Update system packages
echo "Step 1: Updating system packages..."
apt-get update -y

# Install Git
echo "Step 2: Installing Git..."
if ! command -v git &> /dev/null; then
    apt-get install -y git
    echo "Git installed successfully"
else
    echo "Git is already installed"
fi

# Install Docker
echo "Step 3: Installing Docker..."
if ! command -v docker &> /dev/null; then
    apt-get install -y ca-certificates curl gnupg lsb-release
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl start docker
    systemctl enable docker
    echo "Docker installed successfully"
else
    echo "Docker is already installed"
fi

# Verify Docker Compose
echo "Step 4: Verifying Docker Compose..."
docker compose version

# Clone the repository
echo "Step 5: Cloning project from GitHub..."
DEPLOY_DIR="/opt/tire-management-system"
if [ -d "$DEPLOY_DIR" ]; then
    echo "Project directory exists. Pulling latest changes..."
    cd "$DEPLOY_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/Codin-Technologies/tire-data-pipelines.git "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Stop existing containers if any
echo "Step 6: Stopping existing containers (if any)..."
docker compose down || true

# Build and start services
echo "Step 7: Building and starting services..."
docker compose up --build -d

# Wait for services to be ready
echo "Step 8: Waiting for services to start..."
sleep 30

# Submit Flink jobs
echo "Step 9: Submitting Flink jobs..."
echo "Submitting Aggregator job..."
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/aggregator.py

echo "Waiting 10 seconds before submitting next job..."
sleep 10

echo "Submitting Alert Processor job..."
docker exec flink-jobmanager ./bin/flink run -d -py /opt/flink/jobs/alert_processor.py

# Display status
echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Services are running. Access them at:"
echo "  - Grafana: http://185.241.7.158:3000 (admin/admin123)"
echo "  - Flink Dashboard: http://185.241.7.158:8082"
echo "  - Kafdrop (Kafka UI): http://185.241.7.158:9004"
echo "  - FastAPI: http://185.241.7.158:8000/docs"
echo ""
echo "To check running containers:"
echo "  docker ps"
echo ""
echo "To view Flink jobs:"
echo "  docker exec flink-jobmanager ./bin/flink list"
echo ""
echo "To view logs:"
echo "  docker compose logs -f [service-name]"
echo ""
