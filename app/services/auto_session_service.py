import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, cast

from app.config import Settings
from app.database import SessionLocal
from app.models.requests import AutoOrderRequest, AutoSessionStartRequest
from app.models.responses import AutoOrderRunResponse, AutoTradingSessionResponse
from app.services import order_service

logger = logging.getLogger(__name__)

_DEFAULT_TICK_INTERVAL_SECONDS = 300
_FAST_TICK_INTERVAL_SECONDS = 180
_SLOW_TICK_INTERVAL_SECONDS = 600
_CONTINUABLE_HOLD_REASONS = {
    "HOLD_INPUT_AMBIGUOUS",
    "HOLD_LOW_CONVICTION",
    "HOLD_RISK_AGENT_FLAGGED",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _select_tick_interval_seconds(raw_text: str) -> int:
    lowered = raw_text.lower()
    fast_keywords = ("빠르게", "짧게", "스캘", "scalp", "fast", "high frequency")
    slow_keywords = ("천천히", "느리게", "보수적", "long", "slow", "swing")

    if any(keyword in lowered for keyword in fast_keywords):
        return _FAST_TICK_INTERVAL_SECONDS
    if any(keyword in lowered for keyword in slow_keywords):
        return _SLOW_TICK_INTERVAL_SECONDS
    return _DEFAULT_TICK_INTERVAL_SECONDS


@dataclass
class _AutoSessionState:
    session_id: str | None = None
    session_status: Literal["IDLE", "ACTIVE", "STOPPING", "STOPPED"] = "IDLE"
    stop_requested: bool = False
    selected_tick_interval_seconds: int | None = None
    raw_text: str | None = None
    selected_trader_id: str | None = None
    tick_count: int = 0
    started_at: str | None = None
    stopped_at: str | None = None
    last_tick_started_at: str | None = None
    last_tick_completed_at: str | None = None
    stop_reason: str | None = None
    latest_error: str | None = None
    latest_run: AutoOrderRunResponse | None = None


_state = _AutoSessionState()
_task: asyncio.Task[None] | None = None
_wake_event: asyncio.Event | None = None
_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def get_auto_session_status() -> AutoTradingSessionResponse:
    return AutoTradingSessionResponse(
        session_id=_state.session_id,
        session_status=cast(Literal["IDLE", "ACTIVE", "STOPPING", "STOPPED"], _state.session_status),
        stop_requested=_state.stop_requested,
        selected_tick_interval_seconds=_state.selected_tick_interval_seconds,
        raw_text=_state.raw_text,
        selected_trader_id=_state.selected_trader_id,
        tick_count=_state.tick_count,
        started_at=_state.started_at,
        stopped_at=_state.stopped_at,
        last_tick_started_at=_state.last_tick_started_at,
        last_tick_completed_at=_state.last_tick_completed_at,
        stop_reason=_state.stop_reason,
        latest_error=_state.latest_error,
        latest_run=_state.latest_run,
    )


async def start_auto_session(payload: AutoSessionStartRequest, settings: Settings) -> AutoTradingSessionResponse:
    global _task, _wake_event

    async with _get_lock():
        if _task and not _task.done() and _state.session_status in {"ACTIVE", "STOPPING"}:
            raise ValueError("ACTIVE_AUTO_SESSION_EXISTS")

        interval_seconds = _select_tick_interval_seconds(payload.raw_text)
        _wake_event = asyncio.Event()
        _state.session_id = f"session_{uuid.uuid4().hex}"
        _state.session_status = "ACTIVE"
        _state.stop_requested = False
        _state.selected_tick_interval_seconds = interval_seconds
        _state.raw_text = payload.raw_text.strip()
        _state.selected_trader_id = None
        _state.tick_count = 0
        _state.started_at = _now_iso()
        _state.stopped_at = None
        _state.last_tick_started_at = None
        _state.last_tick_completed_at = None
        _state.stop_reason = None
        _state.latest_error = None
        _state.latest_run = None
        _task = asyncio.create_task(_run_session_loop(settings))

    return get_auto_session_status()


async def stop_auto_session() -> AutoTradingSessionResponse:
    async with _get_lock():
        if _state.session_status == "ACTIVE":
            _state.session_status = "STOPPING"
            _state.stop_requested = True
            _state.stop_reason = "USER_STOP_REQUESTED"
            if _wake_event is not None:
                _wake_event.set()
        elif _state.session_status == "STOPPING":
            _state.stop_requested = True
            if _wake_event is not None:
                _wake_event.set()

    return get_auto_session_status()


async def shutdown_auto_session() -> None:
    global _task
    async with _get_lock():
        if _task and not _task.done():
            _state.stop_requested = True
            _state.session_status = "STOPPING"
            _state.stop_reason = _state.stop_reason or "APP_SHUTDOWN"
            if _wake_event is not None:
                _wake_event.set()
            running_task = _task
        else:
            running_task = None

    if running_task is not None:
        try:
            await running_task
        except asyncio.CancelledError:
            pass
    _task = None


async def _run_session_loop(settings: Settings) -> None:
    global _task

    try:
        while True:
            async with _get_lock():
                if _state.stop_requested and _state.tick_count > 0:
                    _finalize_stop("USER_STOPPED")
                    break
                raw_text = _state.raw_text
                selected_trader_id = _state.selected_trader_id
                interval_seconds = _state.selected_tick_interval_seconds or _DEFAULT_TICK_INTERVAL_SECONDS
                _state.last_tick_started_at = _now_iso()

            response = await _run_auto_tick(raw_text or "", selected_trader_id, settings)

            async with _get_lock():
                _state.latest_run = response
                _state.tick_count += 1
                _state.last_tick_completed_at = _now_iso()
                if response.trader_id and not _state.selected_trader_id:
                    _state.selected_trader_id = response.trader_id

                if not _should_continue_session(response):
                    _finalize_stop(response.lifecycle_status)
                    break

                if _state.stop_requested:
                    _finalize_stop("USER_STOPPED")
                    break

            woke_early = await _wait_for_next_tick(interval_seconds)

            async with _get_lock():
                if _state.stop_requested or woke_early:
                    _finalize_stop("USER_STOPPED")
                    break
    except Exception as exc:
        logger.exception("Continuous auto-trading session failed")
        async with _get_lock():
            _state.latest_error = str(exc)
            _finalize_stop("FAILED")
    finally:
        _task = None


async def _run_auto_tick(raw_text: str, trader_id: str | None, settings: Settings) -> AutoOrderRunResponse:
    db = SessionLocal()
    try:
        return await order_service.create_auto_order(
            db,
            AutoOrderRequest(raw_text=raw_text, trader_id=trader_id),
            settings,
        )
    finally:
        db.close()


async def _wait_for_next_tick(interval_seconds: int) -> bool:
    if _wake_event is None:
        await asyncio.sleep(interval_seconds)
        return False

    _wake_event.clear()
    try:
        await asyncio.wait_for(_wake_event.wait(), timeout=interval_seconds)
        return True
    except TimeoutError:
        return False


def _finalize_stop(reason: str) -> None:
    _state.session_status = "STOPPED"
    _state.stop_requested = False
    _state.stop_reason = reason
    _state.stopped_at = _now_iso()


def _should_continue_session(response: AutoOrderRunResponse) -> bool:
    if response.lifecycle_status in {"REPORT_READY", "NO_ORDER"}:
        return True
    if response.lifecycle_status == "HOLD" and response.hold_reason in _CONTINUABLE_HOLD_REASONS:
        return True
    return False


async def _reset_auto_session_state_for_tests() -> None:
    global _task, _wake_event
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
    _wake_event = None
    _state.session_id = None
    _state.session_status = "IDLE"
    _state.stop_requested = False
    _state.selected_tick_interval_seconds = None
    _state.raw_text = None
    _state.selected_trader_id = None
    _state.tick_count = 0
    _state.started_at = None
    _state.stopped_at = None
    _state.last_tick_started_at = None
    _state.last_tick_completed_at = None
    _state.stop_reason = None
    _state.latest_error = None
    _state.latest_run = None
