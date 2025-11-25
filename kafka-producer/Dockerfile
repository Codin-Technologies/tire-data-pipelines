FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy producer script
COPY producer.py .

CMD ["python", "producer.py"]