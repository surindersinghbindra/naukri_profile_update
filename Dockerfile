# ============================================================
# Naukri Profile Updater — Dockerfile
# Base: Microsoft's official Playwright image with Chromium
# ============================================================

FROM mcr.microsoft.com/playwright/python:v1.52.0-noble

# Set timezone to IST
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install cron
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY dashboard.py .

# Make scripts executable
RUN chmod +x scripts/*.sh

# Create necessary directories
RUN mkdir -p /app/logs /app/resumes /app/session_storage

# Set default environment variables
ENV HEADLESS=true
ENV LOG_LEVEL=INFO
ENV LOG_DIR=/app/logs
ENV SCREENSHOT_DIR=/app/logs
ENV SESSION_DIR=/app/session_storage
ENV RESUME_PATH=/app/resumes/resume.pdf
ENV PYTHONUNBUFFERED=1

# Healthcheck — verifies the cron daemon is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD bash /app/scripts/healthcheck.sh

# Entrypoint — sets up cron and keeps the container alive
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
