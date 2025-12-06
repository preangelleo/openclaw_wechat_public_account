FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (none needed for now, maybe curl/wget for healthcheck)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements (if any specific, otherwise we install inline for now as this is a simple SDK)
# In real prod we should have requirements.txt. I'll create one.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY wechat_publisher/ ./wechat_publisher/
COPY main.py .

CMD ["python", "main.py"]
