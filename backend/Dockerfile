# ======================================================
# AI News Studio — Backend Dockerfile
# ======================================================

# ── Development Stage ──────────────────────────────────
FROM python:3.12-slim AS development

# System dependencies for FFmpeg, Whisper, and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries 10 --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 --retries 10 -r requirements.txt

# Copy source
COPY . .

# Create base media directory (runtime subdirectories are created by entrypoint.sh)
RUN mkdir -p /app/media

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ── Production Stage ───────────────────────────────────
FROM python:3.12-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries 10 --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 --retries 10 -r requirements.txt

COPY . .

# Create base media directory (runtime subdirectories are created by entrypoint.sh) and set ownership
RUN mkdir -p /app/media && \
    chown -R appuser:appuser /app

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# NOTE: No USER directive — entrypoint runs as root, creates/chowns
# volume dirs, then drops to appuser via gosu.

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
