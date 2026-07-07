# syntax=docker/dockerfile:1

# --- Build stage: install Python deps (compiles mysqlclient) ----------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# --- Runtime stage ----------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

# Runtime shared library needed by mysqlclient.
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .
RUN chmod +x deploy/entrypoint.sh && chown -R app:app /app

USER app
EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
