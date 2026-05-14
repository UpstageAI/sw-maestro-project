"""실행당 토큰 사용량 추적. LangChain의 usage_metadata에서 집계.

가격은 추정치 — 실제 청구는 Upstage 콘솔에서 확인 필요.
키는 'model:effort' 형태 (예: solar-pro3:low / solar-pro3:high).
"""
import logging
from collections import defaultdict
from contextlib import contextmanager
from threading import Lock

log = logging.getLogger(__name__)

# Upstage solar-pro3 (USD per 1M tokens) — 추정치
PRICING = {
    "solar-pro3:low": {"in": 0.5, "out": 1.5},
    "solar-pro3:high": {"in": 0.5, "out": 1.5},
    "solar-pro3": {"in": 0.5, "out": 1.5},
}


class CostTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._usage: dict[str, dict[str, int]] = defaultdict(lambda: {"in": 0, "out": 0})

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        with self._lock:
            self._usage[model]["in"] += input_tokens
            self._usage[model]["out"] += output_tokens

    def record_from_response(self, model: str, response) -> None:
        meta = getattr(response, "usage_metadata", None) or {}
        self.record(
            model,
            meta.get("input_tokens", 0),
            meta.get("output_tokens", 0),
        )

    def report(self) -> dict:
        out = {"by_model": {}, "total_usd_estimate": 0.0}
        for model, u in self._usage.items():
            price = PRICING.get(model) or PRICING.get(model.split(":")[0], {"in": 0, "out": 0})
            usd = (u["in"] * price["in"] + u["out"] * price["out"]) / 1_000_000
            out["by_model"][model] = {**u, "usd": round(usd, 5)}
            out["total_usd_estimate"] += usd
        out["total_usd_estimate"] = round(out["total_usd_estimate"], 5)
        return out


_GLOBAL = CostTracker()


def tracker() -> CostTracker:
    return _GLOBAL


@contextmanager
def fresh_tracker():
    """실행 단위로 새 트래커를 쓰고 싶을 때."""
    global _GLOBAL
    old = _GLOBAL
    _GLOBAL = CostTracker()
    try:
        yield _GLOBAL
    finally:
        _GLOBAL = old
