-- Source table for Kafka topic tire.raw (named tire_alerts in Flink)
CREATE TABLE tire_alerts (
    sensor_id STRING,
    vehicle_id STRING,
    pressure_kpa DOUBLE,
    temperature_c DOUBLE,
    battery_voltage DOUBLE,  -- <-- Add this line
    `timestamp` BIGINT,
    ts AS TO_TIMESTAMP_LTZ(`timestamp`, 3),
    WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'tire.raw',
    'properties.bootstrap.servers' = 'kafka:9092',
    'format' = 'json',
    'scan.startup.mode' = 'earliest-offset'
);

-- Create aggregations table in PostgreSQL
CREATE TABLE tire_aggregations (
    sensor_id STRING,
    vehicle_id STRING,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    window_size STRING,
    avg_pressure DOUBLE,
    avg_temperature DOUBLE,
    min_pressure DOUBLE,
    max_pressure DOUBLE,
    min_temperature DOUBLE,
    max_temperature DOUBLE,
    record_count BIGINT
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://postgres:5432/tire_db',
    'table-name' = 'tire_aggregations',
    'username' = 'admin',
    'password' = 'admin123'
);

-- Create 1-minute aggregations
INSERT INTO tire_aggregations
SELECT
    sensor_id,
    vehicle_id,
    TUMBLE_START(ts, INTERVAL '1' MINUTE) as window_start,
    TUMBLE_END(ts, INTERVAL '1' MINUTE) as window_end,
    '1m' as window_size,
    AVG(pressure_kpa) as avg_pressure,
    AVG(temperature_c) as avg_temperature,
    MIN(pressure_kpa) as min_pressure,
    MAX(pressure_kpa) as max_pressure,
    MIN(temperature_c) as min_temperature,
    MAX(temperature_c) as max_temperature,
    COUNT(*) as record_count
FROM tire_alerts
GROUP BY 
    sensor_id,
    vehicle_id,
    TUMBLE(ts, INTERVAL '1' MINUTE);