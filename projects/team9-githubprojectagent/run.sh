#!/usr/bin/env bash
# Local WAS launcher (POSIX). uvicorn으로 FastAPI 실행 → 8000번에서 프론트+API.
set -e

if [ ! -d .venv ]; then
  echo "[setup] 가상환경 생성"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -f .venv/.deps_installed ]; then
  echo "[setup] 의존성 설치"
  pip install -r requirements.txt
  touch .venv/.deps_installed
fi

if [ ! -f .env ]; then
  echo "[error] .env 없음 — .env.example 참고해서 채워주세요"
  exit 1
fi

echo "[run] http://localhost:8000  (프론트 + API)"
exec uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
