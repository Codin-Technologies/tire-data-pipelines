# Email Notifier Deployment Guide

Since automated deployment is blocked by your server's security, please follow these steps to deploy the email notifier manually.

## Step 1: SSH into Server
```bash
ssh root@185.241.7.158
# Password: Codinourvps@2025
```

## Step 2: Update Code
```bash
cd /opt/tire-data-pipelines

# Pull latest changes (including email-notifier)
git pull
```

## Step 3: Update Database Schema
We need to add the `vehicles` table. Run this command:

```bash
docker exec -i tire-data-pipelines-postgres-1 psql -U admin -d tire_db << 'EOF'
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id VARCHAR(100) PRIMARY KEY,
    owner_email VARCHAR(255) NOT NULL,
    driver_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO vehicles (vehicle_id, owner_email, driver_email) VALUES
('V001', 'frankkiruma05@gmail.com', 'frankkiruma05@gmail.com'),
('V002', 'frankkiruma05@gmail.com', 'frankkiruma05@gmail.com'),
('V003', 'frankkiruma05@gmail.com', 'frankkiruma05@gmail.com'),
('V004', 'frankkiruma05@gmail.com', 'frankkiruma05@gmail.com'),
('V005', 'frankkiruma05@gmail.com', 'frankkiruma05@gmail.com')
ON CONFLICT (vehicle_id) DO UPDATE 
SET owner_email = EXCLUDED.owner_email,
    driver_email = EXCLUDED.driver_email;
EOF
```

## Step 4: Deploy Email Service
```bash
# Build and start the new service
docker compose up -d --build email-notifier
```

## Step 5: Verify Deployment
Check the logs to see the "Dry Run" emails:

```bash
docker logs -f email-notifier
```

You should see logs like:
```
INFO - Starting Email Notifier Service...
INFO - Connected to Kafka topic: tire.alerts
...
INFO - === DRY RUN MODE (No SMTP Credentials) ===
INFO - To: frankkiruma05@gmail.com
INFO - Subject: [HIGH] Tire Alert for Vehicle V001: LOW_PRESSURE
```

## Step 6: (Optional) Enable Real Emails
If you later get an App Password from Google:

1. Edit `docker-compose.yml`:
   ```bash
   nano docker-compose.yml
   ```
2. Find `email-notifier` service and update:
   ```yaml
   - SMTP_EMAIL=frankkiruma05@gmail.com
   - SMTP_PASSWORD=your-app-password-here
   ```
3. Restart the service:
   ```bash
   docker compose up -d email-notifier
   ```
