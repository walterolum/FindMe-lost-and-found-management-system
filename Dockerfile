# FindMe - Production Dockerfile (Render/Railway/Fly/DigitalOcean/AWS)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps for Pillow + mysqlclient (if used) + building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (cache)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . .

# Ensure upload dirs exist
RUN mkdir -p static/uploads/avatars static/uploads/lost static/uploads/found

EXPOSE 5000

# Use gunicorn via wsgi:application (pymysql patch inside wsgi.py)
CMD ["sh", "-c", "gunicorn wsgi:application --bind 0.0.0.0:${PORT:-5000} --workers 3 --timeout 120"]
