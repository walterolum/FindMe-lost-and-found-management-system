# FindMe - Production Dockerfile (Render free web service)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps (gcc/pkg-config for any C extension fallback, MySQL client headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . .

# Ensure upload dirs exist (local disk fallback; Cloudinary is used in production)
RUN mkdir -p static/uploads/lost static/uploads/found static/uploads/avatars

EXPOSE 10000

# Single worker on purpose: the AI-matcher background threads run inside one
# process. ${PORT} is provided by Render (defaults to 10000 locally).
CMD ["sh", "-c", "gunicorn wsgi:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-10000}"]
