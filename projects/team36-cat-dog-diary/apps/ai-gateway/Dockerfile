FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

# config.py가 ROOT_DIR을 parents[4]로 계산 — monorepo root 가정. 동일 깊이 유지해야 .env.local 미존재 분기가 정상 동작.
WORKDIR /workspace/apps/ai-gateway

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/workspace/apps/ai-gateway/.venv/bin:${PATH}"

EXPOSE 8000

CMD uvicorn ai_gateway.main:app --host 0.0.0.0 --port ${PORT:-8000}
