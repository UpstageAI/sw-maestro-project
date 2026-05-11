from __future__ import annotations

import json
import logging

from models.schema import AgentState

logger = logging.getLogger(__name__)


def save_to_db_node(state: AgentState) -> dict:
    """분석 결과를 DB에 저장하는 노드. 저장 실패 시 경고만 남기고 파이프라인 계속."""
    report = state.get("report")
    collected = state.get("collected_data")

    if not report or not collected:
        return {}

    # TODO: SQLAlchemy + PostgreSQL 구현 — DATABASE_URL 환경변수 사용
    # 현재는 콘솔 로깅으로 저장 성공 여부 확인
    logger.info(
        "DB save placeholder — ticker=%s, conclusion=%s",
        collected.ticker,
        report.one_line_conclusion,
    )

    return {}
