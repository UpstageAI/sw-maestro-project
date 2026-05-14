@echo off
REM Local WAS launcher (Windows). uvicorn으로 FastAPI 실행 → 8000번에서 프론트+API.
setlocal

if not exist .venv (
  echo [setup] 가상환경 생성 중...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

if not exist .venv\.deps_installed (
  echo [setup] 의존성 설치 중...
  pip install -r requirements.txt
  echo done > .venv\.deps_installed
)

if not exist .env (
  echo [error] .env 파일이 없습니다. .env.example 보고 채워주세요.
  exit /b 1
)

echo [run] http://localhost:8000 ^(프론트 + API^)
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload

endlocal
