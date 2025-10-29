# Multi-stage build for Django application
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements/ /app/requirements/

# Install Python dependencies
# Note: We'll install dev dependencies at runtime if needed
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements/prod.txt

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

# Create non-root user
RUN groupadd -r django && useradd -r -g django django

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements /app/requirements

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /wheels/*

# Copy project
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/mediafiles \
    && chown -R django:django /app

# Copy and make scripts executable
RUN chmod +x /app/scripts/*.sh

# Switch to non-root user
USER django

# Run entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--worker-class", "sync", "--worker-connections", "1000", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]