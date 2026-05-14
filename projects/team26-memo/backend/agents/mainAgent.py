"""LLM 연결 총괄 오케스트레이터.

흐름:
  1. SubAgent에게 분석 요청 (retry_level=0, 기본 프롬프트)
  2. 결과 품질 검사 (summary 길이, action_items 형식)
  3. 품질 불량 또는 오류(타임아웃 포함) → retry_level 올려서 재시도
       - 2차 시도: retry_level=1 ("상세 요청" 힌트)
       - 3차 시도: retry_level=2 ("요청 사항 "추가 힌트)
  4. 모든 재시도 소진 → OfflineProvider 폴백
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

from ..llm import LLMProvider, OfflineProvider
from .subAgent import SubAgent

logger = logging.getLogger(__name__)

MAX_RETRIES = 3       # 최대 재시도 횟수
MIN_SUMMARY_LEN = 20  # summary 최소 길이 (글자)


def _is_quality_ok(result: Dict[str, Any]) -> bool:
    """결과 품질 검사.

    기준:
      - summary가 MIN_SUMMARY_LEN자 이상
      - action_items가 리스트 형식
    """
    summary = result.get("summary", "")
    action_items = result.get("action_items", [])

    if not summary or len(summary.strip()) < MIN_SUMMARY_LEN:
        logger.debug("품질 불량: summary 너무 짧음 (%d자)", len(summary.strip()))
        return False

    if not isinstance(action_items, list):
        logger.debug("품질 불량: action_items 형식 오류")
        return False

    for item in action_items:
        if not isinstance(item, dict):
            logger.debug("품질 불량: action_item 항목 형식 오류")
            return False
        if not (str(item.get("title") or "").strip() or str(item.get("what") or "").strip()):
            logger.debug("품질 불량: 상위 티켓 제목/내용 누락")
            return False
        sub_items = item.get("sub_items", [])
        if sub_items is None:
            continue
        if not isinstance(sub_items, list):
            logger.debug("품질 불량: sub_items 형식 오류")
            return False
        for sub in sub_items:
            if not isinstance(sub, dict) or not str(sub.get("what") or "").strip():
                logger.debug("품질 불량: 하위 티켓 내용 누락")
                return False

    return True


class MainAgent:
    """LLM 연결 보강 오케스트레이터.

    SubAgent를 통해 LLM을 호출하고,
    품질 검사 + 프롬프트 변형 재시도 + 최종 offline 폴백을 담당한다.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._sub = SubAgent(provider)
        self._offline = OfflineProvider()
        self.name = f"main-agent({provider.name})"

    def analyze(
        self,
        agenda: str,
        transcript: str,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """프롬프트 변형 재시도 + 품질 검사 포함 분석. 실패 시 offline 폴백.

        시도별 동작:
          1차 (retry_level=0): 기본 프롬프트
          2차 (retry_level=1): "상세 요청" 힌트 추가
          3차 (retry_level=2): "요청 사항 추가" 힌트 추가
        """
        def _log(msg: str) -> None:
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        _log(f"[INFO] 분석 요청 수신 (안건: {len(agenda)}chars, 녹취록: {len(transcript)}chars)")

        last_result: Optional[Dict[str, Any]] = None
        t_start = time.perf_counter()

        for attempt in range(1, MAX_RETRIES + 1):
            retry_level = attempt - 1  # 0 → 1 → 2

            _log(f"[INFO] 분석 시도 {attempt}/{MAX_RETRIES} 시작")

            try:
                result = self._sub.call(agenda, transcript, retry_level=retry_level, log_callback=_log)

                _log("[INFO] 품질 검사 중...")

                if _is_quality_ok(result):
                    summary_len = len(result.get("summary", ""))
                    action_count = len(result.get("action_items", []))
                    _log(f"[PASS] 품질 검사 통과 - 요약 {summary_len}chars, 액션아이템 {action_count}개")
                    elapsed = time.perf_counter() - t_start
                    _log(f"[INFO] 분석 완료 (총 {elapsed:.1f}s 소요)")
                    logger.info(
                        "분석 성공 (시도 %d/%d, retry_level=%d)",
                        attempt, MAX_RETRIES, retry_level,
                    )
                    return result

                _log(f"[WARN] 품질 검사 실패 - 재시도 ({attempt + 1}/{MAX_RETRIES})")
                logger.warning(
                    "품질 불량 → 재시도 (시도 %d/%d, retry_level=%d → %d)",
                    attempt, MAX_RETRIES, retry_level, retry_level + 1,
                )
                last_result = result

            except TimeoutError as exc:
                _log(f"[WARN] 타임아웃 - 재시도 ({attempt}/{MAX_RETRIES})")
                logger.warning(
                    "타임아웃 → 재시도 (시도 %d/%d): %s", attempt, MAX_RETRIES, exc
                )

            except Exception as exc:
                _log(f"[WARN] 오류 발생 - 재시도 ({attempt}/{MAX_RETRIES}): {type(exc).__name__}")
                logger.warning(
                    "SubAgent 오류 → 재시도 (시도 %d/%d): %s", attempt, MAX_RETRIES, exc
                )

        # 모든 재시도 소진 → offline 폴백
        _log("[WARN] 모든 재시도 실패 - 오프라인 분석으로 전환")
        logger.warning("재시도 %d회 모두 실패 → offline 폴백", MAX_RETRIES)
        fallback = self._offline.analyze(agenda, transcript)
        fallback["_fallback"] = True
        fallback["_fallback_reason"] = "LLM 재시도 한도 초과"
        return fallback
