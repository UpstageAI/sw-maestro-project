FROM python:3.11-slim

WORKDIR /app

# uv 설치 — multi-stage 캐시로 빠르게
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# curl (HEALTHCHECK 용)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 먼저 — 코드 변경 시 캐시 보존
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 소스 코드
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY data/ ./data/
RUN uv sync --frozen

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["uv", "run", "python", "-m", "streamlit", "run", "src/ui/app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--browser.gatherUsageStats=false", \
            "--server.headless=true"]
