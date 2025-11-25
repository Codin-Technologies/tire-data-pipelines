from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.postgres.operators.postgres import PostgresOperator
import requests
import json

default_args = {
    'owner': 'frank',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1)
}

def check_flink_health():
    """Check if Flink cluster is healthy"""
    try:
        response = requests.get('http://flink-jobmanager:8081/taskmanagers', timeout=10)
        response.raise_for_status()
        taskmanagers = response.json().get('taskmanagers', [])
        if len(taskmanagers) == 0:
            raise Exception("No taskmanagers registered in Flink cluster")
        print(f"Flink cluster healthy. Taskmanagers: {len(taskmanagers)}")
        return True
    except Exception as e:
        raise Exception(f"Flink cluster not healthy: {str(e)}")

def check_kafka_health():
    """Check if Kafka is healthy"""
    try:
        # This would require kafka-python in Airflow worker
        # For now, we'll use a simple approach
        import subprocess
        result = subprocess.run([
            'docker', 'exec', 'project-root-kafka-1',
            'kafka-topics', '--list', '--bootstrap-server', 'localhost:9092'
        ], capture_output=True, text=True, timeout=30)
        
        if 'tire.raw' in result.stdout:
            print("Kafka is healthy and tire.raw topic exists")
            return True
        else:
            raise Exception("Kafka topics not found")
    except Exception as e:
        raise Exception(f"Kafka health check failed: {str(e)}")

def generate_test_data():
    """Generate test data for the pipeline"""
    import subprocess
    try:
        # Run the test data generator
        result = subprocess.run(['python', '/opt/airflow/flink-jobs/test_data_generator.py'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("Test data generated successfully")
        else:
            raise Exception(f"Test data generation failed: {result.stderr}")
    except Exception as e:
        raise Exception(f"Failed to generate test data: {str(e)}")

with DAG(
    'tire_monitoring_pipeline',
    default_args=default_args,
    description='Real-time tire monitoring with Flink and Kafka',
    schedule_interval=timedelta(hours=1),  # Run hourly
    catchup=False,
    tags=['tire', 'flink', 'kafka']
) as dag:

    # Task 1: Check infrastructure health
    check_infrastructure = PythonOperator(
        task_id='check_infrastructure_health',
        python_callable=check_flink_health
    )

    # Task 2: Setup database tables
    setup_database = PostgresOperator(
        task_id='setup_database_tables',
        postgres_conn_id='tire_postgres',
        sql='''
        CREATE TABLE IF NOT EXISTS tire_alerts (
            id SERIAL PRIMARY KEY,
            alert_id VARCHAR(255) UNIQUE NOT NULL,
            sensor_id VARCHAR(100) NOT NULL,
            vehicle_id VARCHAR(100) NOT NULL,
            timestamp BIGINT NOT NULL,
            alert_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            description TEXT,
            triggering_value FLOAT,
            is_resolved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS tire_aggregations (
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
        '''
    )

    # Task 3: Submit Flink alert job
    submit_alert_job = BashOperator(
        task_id='submit_flink_alert_job',
        bash_command='docker exec flink-jobmanager /opt/flink/bin/sql-client.sh -f /opt/flink/jobs/alerts_final.sql ',
        retries=3
    )

    # Task 4: Submit Flink aggregation job
    submit_aggregation_job = BashOperator(
        task_id='submit_flink_aggregation_job',
        bash_command='docker exec flink-jobmanager /opt/flink/bin/sql-client.sh -f /opt/flink/jobs/aggregations_fixed.sql ',
        retries=3
    )

    # Task 5: Generate test data
    generate_test_data_task = PythonOperator(
        task_id='generate_test_data',
        python_callable=generate_test_data
    )

    # Task 6: Monitor pipeline health
    monitor_pipeline = BashOperator(
        task_id='monitor_pipeline_health',
        bash_command='''
        echo "Checking pipeline health..."
        docker exec project-root-postgres-1 psql -U admin -d tire_db -c "SELECT COUNT(*) as alert_count FROM tire_alerts;"
        docker exec project-root-postgres-1 psql -U admin -d tire_db -c "SELECT COUNT(*) as agg_count FROM tire_aggregations;"
        '''
    )

    # Task 7: Send notifications for critical alerts
    send_alerts_notification = BashOperator(
        task_id='send_alerts_notification',
        bash_command='''
        CRITICAL_ALERTS=$(docker exec project-root-postgres-1 psql -U admin -d tire_db -t -c "SELECT COUNT(*) FROM tire_alerts WHERE severity='HIGH' AND created_at > NOW() - INTERVAL '1 hour';")
        echo "Critical alerts in last hour: $CRITICAL_ALERTS"
        if [ $CRITICAL_ALERTS -gt 0 ]; then
            echo "ALERT: $CRITICAL_ALERTS critical tire alerts detected in the last hour"
        fi
        '''
    )

    # Define task dependencies
    check_infrastructure >> setup_database
    setup_database >> [submit_alert_job, submit_aggregation_job]
    [submit_alert_job, submit_aggregation_job] >> generate_test_data_task
    generate_test_data_task >> monitor_pipeline
    monitor_pipeline >> send_alerts_notification