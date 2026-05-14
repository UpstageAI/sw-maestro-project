from __future__ import annotations

import pytest

from agent.agent2.nodes.score_hypotheses import _confidence, _weighted_score, score_hypotheses_node
from models.schema import CauseHypothesis, ScoreComponents


def _make_hypothesis(
    timing=0.0, credibility=0.0, specificity=0.0, volume=0.0, independent=0.0
) -> CauseHypothesis:
    return CauseHypothesis(
        id="h-1",
        title="Test",
        category="unknown",
        explanation="Test explanation.",
        evidence=[],
        counterpoints=[],
        score_components=ScoreComponents(
            timing_alignment=timing,
            source_credibility=credibility,
            stock_specificity=specificity,
            volume_confirmation=volume,
            independent_source_confirmation=independent,
        ),
        score=0.0,
        confidence="Low",
    )


class TestWeightedScore:
    def test_all_zero_gives_zero(self):
        h = _make_hypothesis()
        assert _weighted_score(h) == 0.0

    def test_all_one_gives_one(self):
        h = _make_hypothesis(1.0, 1.0, 1.0, 1.0, 1.0)
        assert _weighted_score(h) == pytest.approx(1.0)

    def test_weights_sum_correctly(self):
        # timing=1 only → 0.30 weight
        h = _make_hypothesis(timing=1.0)
        assert _weighted_score(h) == pytest.approx(0.30)

    def test_clamped_to_zero_one(self):
        h = _make_hypothesis(1.0, 1.0, 1.0, 1.0, 1.0)
        assert 0.0 <= _weighted_score(h) <= 1.0


class TestConfidence:
    def test_high_above_75(self):
        assert _confidence(0.75) == "High"
        assert _confidence(1.0) == "High"

    def test_medium_between_45_and_75(self):
        assert _confidence(0.45) == "Medium"
        assert _confidence(0.74) == "Medium"

    def test_low_below_45(self):
        assert _confidence(0.0) == "Low"
        assert _confidence(0.44) == "Low"


class TestScoreHypothesesNode:
    def test_scores_are_computed(self, hypothesis):
        state = {"hypotheses": [hypothesis]}
        result = score_hypotheses_node(state)
        h = result["hypotheses"][0]
        assert h.score > 0.0
        assert h.confidence in ("High", "Medium", "Low")

    def test_sorted_descending(self):
        low = _make_hypothesis(timing=0.1)
        high = _make_hypothesis(timing=0.9, credibility=0.9, specificity=0.9, volume=0.9, independent=0.9)
        result = score_hypotheses_node({"hypotheses": [low, high]})
        scores = [h.score for h in result["hypotheses"]]
        assert scores == sorted(scores, reverse=True)

    def test_empty_hypotheses(self):
        result = score_hypotheses_node({"hypotheses": []})
        assert result["hypotheses"] == []

    def test_none_hypotheses(self):
        result = score_hypotheses_node({"hypotheses": None})
        assert result["hypotheses"] == []
