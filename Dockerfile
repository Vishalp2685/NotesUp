# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12.0
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libreoffice \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/temp /app/uploads /app/processing
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD gunicorn 'app:app' --bind=0.0.0.0:8000 --workers=2 --timeout=300 --max-requests=50 --max-requests-jitter=10 --limit-request-line=8190 --limit-request-field_size=32768