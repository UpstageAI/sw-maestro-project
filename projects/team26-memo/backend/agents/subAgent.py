"""단일 LLM 호출 담당.

책임:
  - 실제 LLM API 1회 호출
  - 타임아웃 처리 (TIMEOUT_SEC 초 초과 시 TimeoutError)
  - Rate Limit 감지 후 exponential backoff 재시도 (1초 → 2초 → 4초)
  - 토큰 초과 에러 감지 시 청킹으로 자동 전환
  - 토큰 초과 시 transcript 청킹 후 결과 병합
  - retry_level에 따라 transcript에 프롬프트 힌트 추가
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from ..llm import LLMProvider, _coerce_response
from ..prompts import RETRY_HINTS

logger = logging.getLogger(__name__)

# 설정
TIMEOUT_SEC = 30          # LLM 응답 타임아웃 (초)
MAX_CHARS_PER_CALL = 100000  # 청킹 기준 (약 5,000 토큰)
MAX_RL_RETRIES = 3        # Rate Limit 재시도 횟수


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _is_rate_limit_error(exc: Exception) -> bool:
    """프로바이더별 Rate Limit 에러 감지."""
    cls_name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return (
        "ratelimit" in cls_name
        or "rate_limit" in cls_name
        or "resource exhausted" in msg
        or "rate limit" in msg
        or "429" in msg
    )


def _is_token_limit_error(exc: Exception) -> bool:
    """프로바이더별 토큰 초과 에러 감지."""
    cls_name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return (
        "contextwindow" in cls_name
        or "contextlength" in cls_name
        or "context_length" in msg
        or "context length" in msg
        or "maximum context" in msg
        or "token limit" in msg
        or "too many tokens" in msg
        or "max_tokens" in msg
        or "input too long" in msg
        or "400" in msg and "token" in msg
    )


def _build_retry_transcript(transcript: str, retry_level: int) -> str:
    """retry_level에 따라 transcript 끝에 프롬프트 힌트를 추가."""
    if retry_level <= 0 or not RETRY_HINTS:
        return transcript
    hint = RETRY_HINTS[min(retry_level, len(RETRY_HINTS) - 1)]
    return transcript + hint if hint else transcript


def _split_transcript(transcript: str, max_chars: int) -> List[str]:
    """transcript를 줄 단위로 max_chars 이하 청크로 분할."""
    lines = transcript.splitlines()
    chunks: List[str] = []
    current_lines: List[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > max_chars and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += len(line) + 1

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks if chunks else [transcript]


def _merge_sub_items(
    target: List[Dict[str, str]], incoming: List[Dict[str, str]], seen: set[str]
) -> None:
    for sub in incoming:
        key = (sub.get("what") or "").strip()[:80]
        if key and key not in seen:
            seen.add(key)
            target.append(sub)


def _merge_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """청크별 분석 결과를 하나로 병합."""
    summaries: List[str] = []
    missed_parts: List[str] = []
    next_parts: List[str] = []
    action_items: List[Dict[str, Any]] = []
    item_index: Dict[str, Dict[str, Any]] = {}
    seen_sub_items: Dict[str, set[str]] = {}

    for r in results:
        if r.get("summary"):
            summaries.append(r["summary"])
        if r.get("missed_agenda"):
            missed_parts.append(r["missed_agenda"])
        if r.get("next_agenda"):
            next_parts.append(r["next_agenda"])
        for item in r.get("action_items", []):
            if not isinstance(item, dict):
                continue
            key = ((item.get("title") or item.get("what") or "")).strip()[:80]
            if not key:
                continue

            if key not in item_index:
                item_index[key] = {
                    "title": item.get("title") or "",
                    "who": item.get("who") or "",
                    "when": item.get("when") or "",
                    "what": item.get("what") or "",
                    "sub_items": [],
                }
                seen_sub_items[key] = set()
                action_items.append(item_index[key])

            current = item_index[key]
            for field in ("title", "who", "when", "what"):
                if not current.get(field) and item.get(field):
                    current[field] = item.get(field)
            _merge_sub_items(
                current["sub_items"],
                item.get("sub_items") or [],
                seen_sub_items[key],
            )

    return _coerce_response({
        "summary": " ".join(summaries),
        "missed_agenda": "\n".join(missed_parts),
        "next_agenda": "\n".join(next_parts),
        "action_items": action_items,
    })


# ---------------------------------------------------------------------------
# SubAgent
# ---------------------------------------------------------------------------

class SubAgent:
    """단일 LLM 호출 + 타임아웃 / Rate Limit / 청킹 / 프롬프트 변형 처리."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def call(
        self,
        agenda: str,
        transcript: str,
        retry_level: int = 0,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """agenda + transcript 분석.

        Args:
            retry_level: 0=기본, 1 = 상세 요청, 2 = 요청 사항 추가 (프롬프트 변형)
        """
        # 프롬프트 힌트 추가 (청킹 전 원본 transcript 기준으로만 적용)
        modified_transcript = _build_retry_transcript(transcript, retry_level)

        provider_name = self._provider.name
        model_name = (
            getattr(self._provider, "_model", None)
            or getattr(self._provider, "_model_name", None)
            or "unknown"
        )
        if log_callback:
            log_callback(f"[INFO] LLM 제공자: {provider_name} / 모델: {model_name}")

        if len(modified_transcript) > MAX_CHARS_PER_CALL:
            logger.info(
                "transcript 길이 %d자 > 한도 %d자 → 청킹 시작 (retry_level=%d)",
                len(modified_transcript), MAX_CHARS_PER_CALL, retry_level,
            )
            if log_callback:
                log_callback(f"[INFO] 대용량 입력 감지 - 청킹 시작 ({len(modified_transcript):,}chars)")
            # 청킹 시에는 원본 transcript 기준으로 분할 후 힌트를 마지막 청크에만 추가
            return self._call_chunked(agenda, transcript, retry_level, log_callback=log_callback)

        logger.info(
            "LLM 호출 (transcript %d자, retry_level=%d)", len(modified_transcript), retry_level
        )
        return self._call_with_timeout_and_backoff(agenda, modified_transcript, retry_level, log_callback=log_callback)

    # ------------------------------------------------------------------
    # 타임아웃 + Rate Limit backoff
    # ------------------------------------------------------------------

    def _call_with_timeout_and_backoff(
        self,
        agenda: str,
        transcript: str,
        retry_level: int = 0,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """타임아웃 + Rate Limit exponential backoff + 토큰 초과 청킹 처리."""
        for attempt in range(MAX_RL_RETRIES):
            try:
                if log_callback:
                    log_callback("[INFO] LLM API 요청 전송 중...")
                t0 = time.perf_counter()
                result = self._call_with_timeout(agenda, transcript)
                elapsed = time.perf_counter() - t0
                if log_callback:
                    log_callback(f"[INFO] LLM API 응답 수신 ({elapsed:.1f}s)")
                return result

            except TimeoutError:
                logger.warning(
                    "타임아웃 (%d초 초과), 재시도 %d/%d",
                    TIMEOUT_SEC, attempt + 1, MAX_RL_RETRIES,
                )
                if attempt == MAX_RL_RETRIES - 1:
                    raise TimeoutError(
                        f"LLM이 {TIMEOUT_SEC}초 내에 응답하지 않았습니다. ({MAX_RL_RETRIES}회 시도)"
                    )

            except Exception as exc:
                if _is_token_limit_error(exc):
                    logger.warning(
                        "토큰 초과 감지 → 청킹으로 자동 전환 (transcript %d자)",
                        len(transcript),
                    )
                    if log_callback:
                        log_callback("[WARN] 토큰 초과 - 청킹 전환")
                    # 현재 transcript를 절반으로 줄여서 청킹
                    half = max(len(transcript) // 2, 1000)
                    return self._call_chunked(agenda, transcript, retry_level, chunk_size=half, log_callback=log_callback)

                elif _is_rate_limit_error(exc):
                    wait = 2 ** attempt  # 1초 → 2초 → 4초
                    logger.warning(
                        "Rate Limit 감지 → %d초 후 재시도 (%d/%d)",
                        wait, attempt + 1, MAX_RL_RETRIES,
                    )
                    if log_callback:
                        log_callback(f"[WARN] Rate limit 감지 - {wait}s 후 재시도")
                    time.sleep(wait)
                    if attempt == MAX_RL_RETRIES - 1:
                        raise RuntimeError(
                            f"Rate Limit 재시도 한도({MAX_RL_RETRIES}회) 초과"
                        ) from exc
                else:
                    raise  # 그 외 에러는 바로 올림

        raise RuntimeError("예상치 못한 재시도 루프 종료")

    def _call_with_timeout(self, agenda: str, transcript: str) -> Dict[str, Any]:
        """ThreadPoolExecutor로 TIMEOUT_SEC 타임아웃 적용."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._provider.analyze, agenda, transcript)
            try:
                return future.result(timeout=TIMEOUT_SEC)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"LLM 응답 {TIMEOUT_SEC}초 초과")

    # ------------------------------------------------------------------
    # 청킹
    # ------------------------------------------------------------------

    def _call_chunked(
        self,
        agenda: str,
        transcript: str,
        retry_level: int,
        chunk_size: int = MAX_CHARS_PER_CALL,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """transcript를 청킹해 각각 분석 후 결과 병합.

        힌트는 마지막 청크에만 추가해 컨텍스트 오염을 최소화한다.
        chunk_size: 토큰 초과 감지 시 절반 크기로 줄여서 재청킹 가능.
        """
        chunks = _split_transcript(transcript, chunk_size)
        total = len(chunks)
        logger.info("청크 %d개로 분할 (청크 크기: %d자)", total, chunk_size)

        results: List[Dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            if log_callback:
                log_callback(f"[INFO] 청킹 처리 중 (청크 {i + 1}/{total})")
            is_last = i == total - 1
            final_chunk = _build_retry_transcript(chunk, retry_level) if is_last else chunk
            logger.info("청크 %d/%d 분석 중 (%d자)", i + 1, total, len(final_chunk))
            result = self._call_with_timeout_and_backoff(agenda, final_chunk, retry_level, log_callback=log_callback)
            results.append(result)

        return _merge_results(results)
