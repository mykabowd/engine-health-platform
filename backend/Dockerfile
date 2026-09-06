# Lightweight image for the Engine Health API.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install -r requirements.txt

COPY src ./src
RUN pip install -e .

# The model artifact (src/engine_health/artifacts/model.joblib) is committed
# to the repo and copied in with `src`, so no training step is needed at
# image build or container start-up (see engine_health/model.py fallback).

ENV ENGINE_HEALTH_ALLOWED_ORIGINS="*"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import socket; socket.create_connection(('localhost', 8000), timeout=3)" || exit 1

CMD ["uvicorn", "engine_health.main:app", "--host", "0.0.0.0", "--port", "8000"]
