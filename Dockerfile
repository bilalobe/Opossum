# Multi-stage build for efficiency and security
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Second stage: runtime
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r opossum && useradd -r -g opossum opossum

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    imagemagick \
    libmagickwand-dev \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Copy application code
COPY . .

# Set secure env defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    ENV=production \
    OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces

# Model optimization settings - this is the key improvement
ENV TRANSFORMERS_OFFLINE=1 \
    TRANSFORMERS_CACHE=/app/data/models \
    CHAT2SVG_QUANTIZE_MODELS=true \
    CHAT2SVG_QUANTIZATION_PRECISION=int8

# Create directories for data and set permissions
RUN mkdir -p /app/data/cache /app/data/models && \
    chown -R opossum:opossum /app/data

# Add model quantization script and run it during build
COPY scripts/quantize_models.py /app/scripts/
RUN python /app/scripts/quantize_models.py

# Switch to non-root user
USER opossum

# Expose port that Flask will run on
EXPOSE 8000

# Healthcheck to verify application is running properly
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["python", "main.py"]