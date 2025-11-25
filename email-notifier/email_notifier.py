import json
import os
import smtplib
import time
import logging
import psycopg2
from kafka import KafkaConsumer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'tire.alerts')
POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'postgres')
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'tire_db')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'admin')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'admin123')

# SMTP Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

def get_db_connection():
    """Create a database connection."""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def get_vehicle_contacts(vehicle_id):
    """Fetch owner and driver emails for a vehicle."""
    conn = get_db_connection()
    if not conn:
        return None, None
    
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT owner_email, driver_email FROM vehicles WHERE vehicle_id = %s",
            (vehicle_id,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return result[0], result[1]
        return None, None
    except Exception as e:
        logger.error(f"Error fetching vehicle contacts: {e}")
        if conn:
            conn.close()
        return None, None

def send_email(to_emails, subject, body):
    """Send an email or log it if credentials are missing."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.info("=== DRY RUN MODE (No SMTP Credentials) ===")
        logger.info(f"To: {', '.join(to_emails)}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body}")
        logger.info("==========================================")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Email sent successfully to {to_emails}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def process_alert(alert):
    """Process a single alert."""
    try:
        vehicle_id = alert.get('vehicle_id')
        alert_type = alert.get('alert_type')
        description = alert.get('description')
        severity = alert.get('severity')
        
        logger.info(f"Processing alert: {alert_type} for vehicle {vehicle_id}")
        
        # Get contacts
        owner_email, driver_email = get_vehicle_contacts(vehicle_id)
        
        if not owner_email:
            logger.warning(f"No contact info found for vehicle {vehicle_id}")
            return

        # Prepare email
        subject = f"[{severity}] Tire Alert for Vehicle {vehicle_id}: {alert_type}"
        body = f"""
        TIRE ALERT NOTIFICATION
        =======================
        
        Vehicle ID: {vehicle_id}
        Alert Type: {alert_type}
        Severity:   {severity}
        Time:       {alert.get('timestamp')}
        
        Description:
        {description}
        
        Please check the dashboard for more details.
        """
        
        # Send email to both owner and driver
        recipients = list(set([owner_email, driver_email]))
        send_email(recipients, subject, body)
        
    except Exception as e:
        logger.error(f"Error processing alert: {e}")

def main():
    """Main consumer loop."""
    logger.info("Starting Email Notifier Service...")
    
    # Wait for Kafka to be ready
    time.sleep(20)
    
    while True:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='email-notifier-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info(f"Connected to Kafka topic: {KAFKA_TOPIC}")
            
            for message in consumer:
                process_alert(message.value)
                
        except Exception as e:
            logger.error(f"Kafka connection error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
