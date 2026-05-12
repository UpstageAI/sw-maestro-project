FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# build-essential covers chromadb's C-extension wheels (hnswlib etc.) when prebuilt
# wheels aren't available for the active Python/architecture. curl is used by the
# compose healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependency layer — separated so app/ source changes don't bust the wheel cache.
COPY pyproject.toml ./
RUN uv pip install --system -e . --no-cache

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
