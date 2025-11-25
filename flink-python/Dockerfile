FROM flink:1.18.0-scala_2.12

# Install Python and required system dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv openjdk-11-jdk-headless && \
    apt-get clean

# Create a virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python packages
COPY requirements.txt /opt/flink/
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-arm64
RUN pip install --timeout 300 -r /opt/flink/requirements.txt

# Copy Flink jobs
COPY *.py /opt/flink/jobs/

# Download required connectors
RUN wget -P /opt/flink/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.2-1.18/flink-sql-connector-kafka-3.0.2-1.18.jar && \
    wget -P /opt/flink/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar && \
    wget -P /opt/flink/lib/ https://jdbc.postgresql.org/download/postgresql-42.6.0.jar

# Set Python environment for Flink
ENV PYFLINK_CLIENT_EXECUTABLE=/opt/venv/bin/python3
ENV PYTHONPATH=/opt/flink/jobs

WORKDIR /opt/flink