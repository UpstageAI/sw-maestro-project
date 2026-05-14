FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*

RUN pip install uv

ENV UV_SYSTEM_PYTHON=1

# 의존성 파일만 먼저 복사 → 소스 변경 시 이 레이어 캐시 재사용
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 소스는 나중에 복사 (변경 빈도 높음)
COPY src/ src/
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "newspick_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
