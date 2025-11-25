-- Create Kafka source table for raw tire data
CREATE TABLE tire_raw (
    sensor_id STRING,
    vehicle_id STRING,
    `timestamp` BIGINT,
    pressure_kpa DOUBLE,
    temperature_c DOUBLE,
    battery_voltage DOUBLE
) WITH (
    'connector' = 'kafka',
    'topic' = 'tire.raw',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-alerts',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);

-- Create alerts table in PostgreSQL
CREATE TABLE tire_alerts (
    alert_id STRING,
    sensor_id STRING,
    vehicle_id STRING,
    `timestamp` BIGINT,
    alert_type STRING,
    severity STRING,
    description STRING,
    triggering_value DOUBLE
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://postgres:5432/tire_db',
    'table-name' = 'tire_alerts',
    'username' = 'admin',
    'password' = 'admin123'
);

-- Create alerts Kafka topic
CREATE TABLE kafka_alerts (
    alert_id STRING,
    sensor_id STRING,
    vehicle_id STRING,
    `timestamp` BIGINT,
    alert_type STRING,
    severity STRING,
    description STRING,
    triggering_value DOUBLE
) WITH (
    'connector' = 'kafka',
    'topic' = 'tire.alerts',
    'properties.bootstrap.servers' = 'kafka:9092',
    'format' = 'json'
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
    record_count INT
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://postgres:5432/tire_db',
    'table-name' = 'tire_aggregations',
    'username' = 'admin',
    'password' = 'admin123'
);

-- Insert alerts into both PostgreSQL and Kafka
INSERT INTO tire_alerts
SELECT 
    CONCAT(sensor_id, '_', CAST(`timestamp` AS STRING)) as alert_id,
    sensor_id,
    vehicle_id,
    `timestamp`,
    CASE 
        WHEN pressure_kpa < 180 THEN 'LOW_PRESSURE'
        WHEN pressure_kpa > 300 THEN 'HIGH_PRESSURE' 
        WHEN temperature_c > 80 THEN 'HIGH_TEMPERATURE'
    END as alert_type,
    CASE 
        WHEN pressure_kpa < 180 OR pressure_kpa > 300 THEN 'HIGH'
        WHEN temperature_c > 80 THEN 'MEDIUM'
    END as severity,
    CASE 
        WHEN pressure_kpa < 180 THEN CONCAT('Pressure ', CAST(pressure_kpa AS STRING), ' kPa is below threshold 180 kPa')
        WHEN pressure_kpa > 300 THEN CONCAT('Pressure ', CAST(pressure_kpa AS STRING), ' kPa is above threshold 300 kPa')
        WHEN temperature_c > 80 THEN CONCAT('Temperature ', CAST(temperature_c AS STRING), '°C is above threshold 80°C')
    END as description,
    CASE 
        WHEN pressure_kpa < 180 THEN pressure_kpa
        WHEN pressure_kpa > 300 THEN pressure_kpa
        WHEN temperature_c > 80 THEN temperature_c
    END as triggering_value
FROM tire_raw
WHERE pressure_kpa < 180 OR pressure_kpa > 300 OR temperature_c > 80;

-- Also insert into Kafka alerts
INSERT INTO kafka_alerts
SELECT * FROM tire_alerts;