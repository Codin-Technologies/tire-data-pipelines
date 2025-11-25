FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy consumer script
COPY consumer.py .

CMD ["python", "consumer.py"]