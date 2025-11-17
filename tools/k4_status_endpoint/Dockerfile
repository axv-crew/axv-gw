# Dockerfile dla AXV API z K4.1 Status Endpoint
# Build: docker build -t axv-api:0.1.9 .
# Run:   docker run -p 8080:8080 axv-api:0.1.9

FROM python:3.11-slim

LABEL maintainer="AXV Crew <family@axv.life>"
LABEL version="0.1.9"
LABEL description="AXV API with unified status endpoint"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY axv_status_endpoint.py .
COPY main.py .

# Create non-root user
RUN useradd -m -u 1000 axv && \
    chown -R axv:axv /app

USER axv

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/axv/status || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
