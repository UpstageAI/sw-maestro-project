from __future__ import annotations

from models.schema import AgentState, CauseHypothesis

_WEIGHTS = {
    "timing_alignment": 0.30,
    "source_credibility": 0.25,
    "stock_specificity": 0.20,
    "volume_confirmation": 0.15,
    "independent_source_confirmation": 0.10,
}


def _weighted_score(h: CauseHypothesis) -> float:
    sc = h.score_components
    raw = (
        _WEIGHTS["timing_alignment"] * sc.timing_alignment
        + _WEIGHTS["source_credibility"] * sc.source_credibility
        + _WEIGHTS["stock_specificity"] * sc.stock_specificity
        + _WEIGHTS["volume_confirmation"] * sc.volume_confirmation
        + _WEIGHTS["independent_source_confirmation"] * sc.independent_source_confirmation
    )
    return min(1.0, max(0.0, raw))


def _confidence(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def score_hypotheses_node(state: AgentState) -> dict:
    """가설 점수화·신뢰도 분류 후 내림차순 정렬 노드."""
    hypotheses = state.get("hypotheses") or []

    scored = []
    for h in hypotheses:
        score = _weighted_score(h)
        scored.append(h.model_copy(update={"score": score, "confidence": _confidence(score)}))
    scored.sort(key=lambda h: h.score, reverse=True)

    return {"hypotheses": scored}
