"""MeetFlow AI 백엔드 (FastAPI).

엔드포인트:
  GET  /healthz   - 헬스체크
  POST /analyze   - 회의 분석

프론트엔드와의 API 계약:
  요청  : {"agenda": str, "transcript": str}
  응답  : {"summary": str, "missed_agenda": str,
           "next_agenda": str,
           "action_items": [{"who": str, "when": str, "what": str}]}
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agents.mainAgent import MainAgent
from .llm import build_primary_provider
from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse

# ---------------------------------------------------------------------------
# 설정 / 로깅
# ---------------------------------------------------------------------------

VERSION = "1.0.0"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("meetflow.backend")

# ---------------------------------------------------------------------------
# 앱 / 의존성
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MeetFlow AI Backend",
    version=VERSION,
    description="회의 안건과 녹취록을 분석해 요약/누락안건/다음안건/액션아이템을 반환",
)

# CORS - 데모/로컬 편의 (환경에서 제한하려면 ALLOWED_ORIGINS 사용)
_allowed = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MainAgent는 앱 기동 시 1회 초기화
_agent = MainAgent(build_primary_provider())
logger.info("MainAgent initialized: %s", _agent.name)


# ---------------------------------------------------------------------------
# 미들웨어
# ---------------------------------------------------------------------------


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok", provider=_agent.name, version=VERSION)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "MeetFlow AI Backend",
        "version": VERSION,
        "provider": _agent.name,
        "endpoints": ["/healthz", "/analyze"],
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """회의 안건 + 녹취록을 분석해 구조화된 결과를 반환."""
    logs: list[str] = []

    def _log(msg: str) -> None:
        logs.append(msg)

    try:
        raw = _agent.analyze(req.agenda, req.transcript, log_callback=_log)
    except Exception as exc:  # 마지막 안전망
        logger.exception("분석 처리 중 예기치 못한 오류")
        raise HTTPException(status_code=500, detail=f"분석 실패: {exc}") from exc

    clean = {k: v for k, v in raw.items() if not k.startswith("_")}
    clean["logs"] = logs
    return AnalyzeResponse(**clean)


# ---------------------------------------------------------------------------
# 글로벌 에러 핸들러 - 항상 JSON 으로 응답
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다.", "error": str(exc)},
    )
