# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API script
COPY anomaly_api.py .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash apiuser && \
    chown -R apiuser:apiuser /app
USER apiuser

# Expose the port that the API runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command to run the API
CMD ["python", "-m", "uvicorn", "anomaly_api:app", "--host", "0.0.0.0", "--port", "8000"]
