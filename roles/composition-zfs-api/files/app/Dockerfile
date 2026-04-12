FROM ubuntu:24.04

LABEL maintainer="ZFS API"
LABEL description="REST API for ZFS pool, dataset, and snapshot monitoring"

# Install Python, ZFS utilities, and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 \
        python3-pip \
        zfsutils-linux \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR .

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
