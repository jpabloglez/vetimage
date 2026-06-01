FROM python:3.11-slim

LABEL maintainer="OpenMedLab Team"
LABEL description="DICOM Gateway Service for PACS integration"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gateway/ gateway/
COPY main.py .

# Create storage directory
RUN mkdir -p /app/storage/dicom-temp

# Create non-root user
RUN useradd -m -u 1000 gateway && \
    chown -R gateway:gateway /app

USER gateway

# Expose ports
# 11112: DICOM SCP
# 8001: API/Monitoring
EXPOSE 11112 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health')"

# Run the application
CMD ["python", "main.py"]
