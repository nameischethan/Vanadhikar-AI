# Vanadhikar AI - Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Seed mock database if not already populated
RUN python3 seed_data.py

EXPOSE 8000

# Default command: Runs the zero-dependency or FastAPI server
CMD ["python3", "server.py", "8000"]
