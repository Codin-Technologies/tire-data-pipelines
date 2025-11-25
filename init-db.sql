-- Drop existing tables and views if they exist
DROP VIEW IF EXISTS current_alerts CASCADE;
DROP VIEW IF EXISTS recent_aggregations CASCADE;
DROP TABLE IF EXISTS tire_aggregations CASCADE;
DROP TABLE IF EXISTS tire_alerts CASCADE;

-- Create alerts table with correct schema
CREATE TABLE tire_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) UNIQUE NOT NULL,
    sensor_id VARCHAR(100) NOT NULL,
    vehicle_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    triggering_value FLOAT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create aggregations table with correct schema
CREATE TABLE tire_aggregations (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(100) NOT NULL,
    vehicle_id VARCHAR(100) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    window_size VARCHAR(10) NOT NULL,
    avg_pressure FLOAT NOT NULL,
    avg_temperature FLOAT NOT NULL,
    min_pressure FLOAT NOT NULL,
    max_pressure FLOAT NOT NULL,
    min_temperature FLOAT NOT NULL,
    max_temperature FLOAT NOT NULL,
    record_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_alerts_sensor_id ON tire_alerts(sensor_id);
CREATE INDEX idx_alerts_vehicle_id ON tire_alerts(vehicle_id);
CREATE INDEX idx_alerts_timestamp ON tire_alerts(timestamp);
CREATE INDEX idx_alerts_severity ON tire_alerts(severity);

CREATE INDEX idx_agg_sensor_id ON tire_aggregations(sensor_id);
CREATE INDEX idx_agg_vehicle_id ON tire_aggregations(vehicle_id);
CREATE INDEX idx_agg_window_start ON tire_aggregations(window_start);
CREATE INDEX idx_agg_window_end ON tire_aggregations(window_end);

-- Create views
CREATE VIEW current_alerts AS
SELECT * FROM tire_alerts 
WHERE is_resolved = FALSE 
ORDER BY timestamp DESC;

CREATE VIEW recent_aggregations AS
SELECT * FROM tire_aggregations 
WHERE window_start >= NOW() - INTERVAL '1 hour'
ORDER BY window_start DESC;

-- Insert sample data
INSERT INTO tire_alerts (alert_id, sensor_id, vehicle_id, timestamp, alert_type, severity, description, triggering_value) VALUES
('sample_alert_1', 'V001-FL', 'V001', NOW() - INTERVAL '10 minutes', 'LOW_PRESSURE', 'HIGH', 'Pressure 175.5 kPa is below threshold 180 kPa', 175.5),
('sample_alert_2', 'V002-RR', 'V002', NOW() - INTERVAL '5 minutes', 'HIGH_TEMPERATURE', 'MEDIUM', 'Temperature 82.3°C is above threshold 80°C', 82.3)
ON CONFLICT (alert_id) DO NOTHING;

-- Verify tables were created
\dt