# Small State Quality Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the persona review quality pipeline from the rolled-back baseline by keeping each LLM call small, separating generated text from quality metadata, and preventing weak intermediate artifacts from being treated as reliable facts.

**Architecture:** Keep the current graph shape and persona selection. Add small quality report objects to state, assess f2/f3 artifacts deterministically, make f3 review one target point at a time, and make f4 final decision deterministic while the supervisor LLM writes only the explanatory body.

**Tech Stack:** Python 3.12, LangGraph, LangChain `ChatPromptTemplate`, `ChatUpstage`, Pydantic models, `unittest`, Ruff.

---

## Current Baseline

The branch has been reset to `1a927e2edd51cff94329c4005a4adf28093f529e`.

Current graph:

```text
raw_input
  -> f0_parse: brief
  -> f1_select: persona_a/persona_b/persona_selection_reason
  -> f2_opinion x2: opinion_a/opinion_b
  -> f3_review x2: review_a/review_b
  -> f4_supervisor: final_review_text
```

Observed failure mode from the previous implementation:

```text
LLM call was isolated per node, but state carried weak LLM text forward.
f2 weak text became f3 input.
f3 invented "helpful" functions while reviewing.
f4 summarized conflicting or weak artifacts as if they were reliable.
```

This plan does not add `planning_insight` or `validation_question` directly to `ReactionPoint` yet. Those are second-order planning interpretations and should come after raw persona/review quality is stable.

---

## File Structure

- Modify `schemas.py`
  - Add `QualityFlag`, `OpinionQualityReport`, `ReviewQualityReport`.
  - Keep existing `ReactionPoint`, `Opinion`, `PointFeedback`, and `Review` simple.
- Modify `state.py`
  - Add `opinion_quality_a`, `opinion_quality_b`, `review_quality_a`, `review_quality_b`.
- Create `services/brief_evidence.py`
  - Deterministic helpers for brief grounding and unsupported feature detection.
- Create `services/artifact_quality.py`
  - Deterministic f2/f3 quality scoring helpers.
- Modify `nodes/f2_opinion.py`
  - Keep one f2 LLM call per persona.
  - Add quality report creation after LLM output.
  - Do not repair with LLM in f2.
  - Pass target opinion quality into f3 Send payloads.
- Modify `nodes/f3_review.py`
  - Replace one large review call with one small call per reviewable point.
  - Skip failed f2 points or mark them as skipped.
  - Keep review output in current `Review` schema.
- Modify `nodes/f4_supervisor.py`
  - Deterministically compute `[통과]`, `[보류]`, or `[재검토]`.
  - Ask the supervisor LLM to write body sections only.
  - Strip conflicting decision tokens from generated body.
- Create `scripts/evaluate_node_quality.py`
  - Run one sample and print node-level artifacts and quality reports.
- Add tests:
  - `tests/test_quality_contract.py`
  - `tests/test_brief_evidence.py`
  - `tests/test_artifact_quality.py`
  - update existing f2/f3/f4 tests.

---

### Task 1: Add Quality Report State Contract

**Files:**
- Modify: `schemas.py`
- Modify: `state.py`
- Create: `tests/test_quality_contract.py`

- [ ] **Step 1: Write failing schema/state tests**

Add `tests/test_quality_contract.py`:

```python
import unittest

from schemas import OpinionQualityReport, QualityFlag, ReviewQualityReport
from state import ProjectState


class QualityContractTests(unittest.TestCase):
    def test_quality_flag_contract(self) -> None:
        flag = QualityFlag(
            code="unsupported_feature",
            severity="fail",
            message="서비스 기획안에 없는 기능을 언급했습니다.",
            point_id="abc_pos_01",
        )

        self.assertEqual(flag.code, "unsupported_feature")
        self.assertEqual(flag.severity, "fail")
        self.assertEqual(flag.point_id, "abc_pos_01")

    def test_opinion_quality_report_defaults(self) -> None:
        report = OpinionQualityReport(persona_id="persona_a")

        self.assertEqual(report.pass_point_ids, [])
        self.assertEqual(report.weak_point_ids, [])
        self.assertEqual(report.fail_point_ids, [])
        self.assertEqual(report.flags, [])

    def test_review_quality_report_defaults(self) -> None:
        report = ReviewQualityReport(reviewer_id="persona_a", target_id="persona_b")

        self.assertEqual(report.pass_feedback_ids, [])
        self.assertEqual(report.weak_feedback_ids, [])
        self.assertEqual(report.fail_feedback_ids, [])
        self.assertEqual(report.flags, [])

    def test_project_state_declares_quality_fields(self) -> None:
        annotations = ProjectState.__annotations__

        self.assertIn("opinion_quality_a", annotations)
        self.assertIn("opinion_quality_b", annotations)
        self.assertIn("review_quality_a", annotations)
        self.assertIn("review_quality_b", annotations)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_quality_contract -v
```

Expected: FAIL because the quality models and state fields do not exist.

- [ ] **Step 3: Add quality models**

In `schemas.py`, add after `Review`:

```python
class QualityFlag(BaseModel):
    """A deterministic quality finding for an intermediate artifact."""

    code: str
    severity: Literal["info", "weak", "fail"]
    message: str
    point_id: str | None = None


class OpinionQualityReport(BaseModel):
    """Quality metadata for one persona's first opinion."""

    persona_id: str
    pass_point_ids: list[str] = Field(default_factory=list)
    weak_point_ids: list[str] = Field(default_factory=list)
    fail_point_ids: list[str] = Field(default_factory=list)
    flags: list[QualityFlag] = Field(default_factory=list)


class ReviewQualityReport(BaseModel):
    """Quality metadata for one cross review."""

    reviewer_id: str
    target_id: str
    pass_feedback_ids: list[str] = Field(default_factory=list)
    weak_feedback_ids: list[str] = Field(default_factory=list)
    fail_feedback_ids: list[str] = Field(default_factory=list)
    flags: list[QualityFlag] = Field(default_factory=list)
```

Also add these names to `__all__`.

- [ ] **Step 4: Add state fields**

In `state.py`, import the new models and add:

```python
    opinion_quality_a: OpinionQualityReport
    opinion_quality_b: OpinionQualityReport
    review_quality_a: ReviewQualityReport
    review_quality_b: ReviewQualityReport
```

- [ ] **Step 5: Verify**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_quality_contract -v
.\.venv\Scripts\python.exe -m ruff check schemas.py state.py tests\test_quality_contract.py --no-cache
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add schemas.py state.py tests/test_quality_contract.py
git commit -m "feat: add artifact quality state contract"
```

---

### Task 2: Add Deterministic Brief Evidence Helpers

**Files:**
- Create: `services/brief_evidence.py`
- Create: `tests/test_brief_evidence.py`

- [ ] **Step 1: Write failing helper tests**

Add `tests/test_brief_evidence.py`:

```python
import unittest

from schemas import ServicePlanInput
from services.brief_evidence import (
    brief_terms,
    has_brief_feature_overlap,
    introduces_unsupported_solution,
    text_terms,
)


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농가는 사진과 음성 설명으로 농산물을 등록하고 소비자는 산지 배송으로 주문한다.",
        title="산지 직거래",
        description="농가와 소비자를 직접 연결한다.",
        target="농촌 생산자, 도시 소비자",
        key_features=["사진·음성 상품 등록", "소비자 주문", "산지 배송"],
        concerns="배송 책임",
    )


class BriefEvidenceTests(unittest.TestCase):
    def test_text_terms_extracts_korean_terms(self) -> None:
        terms = text_terms("사진과 음성으로 상품을 등록하고 배송을 확인한다.")

        self.assertIn("사진", terms)
        self.assertIn("음성", terms)
        self.assertIn("등록", terms)
        self.assertIn("배송", terms)

    def test_brief_terms_include_features_and_concerns(self) -> None:
        terms = brief_terms(_brief())

        self.assertIn("사진", terms)
        self.assertIn("배송", terms)
        self.assertIn("책임", terms)

    def test_has_brief_feature_overlap_requires_feature_term(self) -> None:
        brief = _brief()

        self.assertTrue(has_brief_feature_overlap("사진으로 상품 등록이 쉬운지 본다.", brief))
        self.assertFalse(has_brief_feature_overlap("정산 자동화 대시보드가 필요하다.", brief))

    def test_introduces_unsupported_solution_detects_new_feature(self) -> None:
        brief = _brief()

        self.assertFalse(introduces_unsupported_solution("배송 책임을 확인하고 싶다.", brief))
        self.assertTrue(introduces_unsupported_solution("정산 자동화와 실시간 모니터링이 필요하다.", brief))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_brief_evidence -v
```

Expected: FAIL because `services.brief_evidence` does not exist.

- [ ] **Step 3: Implement helper module**

Create `services/brief_evidence.py`:

```python
"""Deterministic text helpers for grounding artifacts in the service brief."""

from __future__ import annotations

import re

from schemas import ServicePlanInput


STOPWORDS = {
    "서비스",
    "기획",
    "사용자",
    "기능",
    "필요",
    "확인",
    "가능",
    "제공",
    "있는지",
    "합니다",
}

SOLUTION_CUES = {
    "자동화",
    "대시보드",
    "모니터링",
    "인증",
    "추천",
    "알고리즘",
    "챗봇",
    "보험",
    "정산",
    "실시간",
    "추적",
}


def text_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[가-힣A-Za-z0-9]+", text or "")
        if len(token) >= 2 and token not in STOPWORDS
    }


def brief_terms(brief: ServicePlanInput) -> set[str]:
    return text_terms(" ".join([
        brief.raw_text or "",
        brief.title or "",
        brief.description or "",
        brief.target or "",
        " ".join(brief.key_features),
        brief.concerns or "",
    ]))


def feature_terms(brief: ServicePlanInput) -> set[str]:
    return text_terms(" ".join([
        " ".join(brief.key_features),
        brief.description or "",
        brief.concerns or "",
    ]))


def has_brief_feature_overlap(text: str, brief: ServicePlanInput) -> bool:
    return bool(text_terms(text) & feature_terms(brief))


def introduces_unsupported_solution(text: str, brief: ServicePlanInput) -> bool:
    terms = text_terms(text)
    allowed = brief_terms(brief)
    introduced_solution_terms = (terms & SOLUTION_CUES) - allowed
    if introduced_solution_terms:
        return True
    cue_in_text = any(cue in (text or "") for cue in SOLUTION_CUES)
    introduced_terms = terms - allowed - STOPWORDS
    return cue_in_text and bool(introduced_terms)
```

- [ ] **Step 4: Verify**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_brief_evidence -v
.\.venv\Scripts\python.exe -m ruff check services\brief_evidence.py tests\test_brief_evidence.py --no-cache
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add services/brief_evidence.py tests/test_brief_evidence.py
git commit -m "feat: add brief evidence helpers"
```

---

### Task 3: Add Artifact Quality Helpers

**Files:**
- Create: `services/artifact_quality.py`
- Create: `tests/test_artifact_quality.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_artifact_quality.py`:

```python
import unittest

from schemas import PointFeedback, ReactionPoint, ServicePlanInput, TargetUserPersonaCard
from services.artifact_quality import assess_feedback, assess_reaction_point


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농가는 사진과 음성 설명으로 상품을 등록하고 소비자는 산지 배송으로 주문한다.",
        title="산지 직거래",
        description="농가와 소비자를 직접 연결한다.",
        target="농촌 생산자, 도시 소비자",
        key_features=["사진·음성 상품 등록", "소비자 주문", "산지 배송"],
        concerns="배송 책임",
    )


def _persona() -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id="persona_a",
        source_uuid="source",
        display_name="테스트",
        age_group="50s",
        sex="여자",
        occupation="온라인 판매원",
        region="경남",
        one_line_summary="온라인 판매를 한다.",
        life_context="상품 사진을 자주 올린다.",
        user_goals=["상품 등록 시간을 줄이기"],
        pain_points=["등록 과정이 번거로움"],
        speaking_style="차분한 말투",
    )


class ArtifactQualityTests(unittest.TestCase):
    def test_assess_reaction_point_passes_grounded_point(self) -> None:
        point = ReactionPoint(
            point_id="a_pos_01",
            title="사진 등록이 쉬움",
            detail="나는 상품 사진을 자주 올리기 때문에 사진과 음성으로 등록하는 흐름이 짧으면 좋다.",
        )

        level, flags = assess_reaction_point(point, _brief(), _persona())

        self.assertEqual(level, "pass")
        self.assertEqual(flags, [])

    def test_assess_reaction_point_fails_unsupported_solution(self) -> None:
        point = ReactionPoint(
            point_id="a_pos_01",
            title="정산 자동화",
            detail="나는 실시간 정산 자동화 대시보드가 있으면 좋겠다.",
        )

        level, flags = assess_reaction_point(point, _brief(), _persona())

        self.assertEqual(level, "fail")
        self.assertEqual(flags[0].code, "unsupported_solution")

    def test_assess_feedback_fails_unsupported_solution(self) -> None:
        feedback = PointFeedback(
            target_point_id="b_pos_01",
            agreement="agree",
            comment="품질 인증 알고리즘과 실시간 모니터링을 추가하면 좋겠다.",
        )

        level, flags = assess_feedback(feedback, _brief())

        self.assertEqual(level, "fail")
        self.assertEqual(flags[0].code, "unsupported_solution")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_artifact_quality -v
```

Expected: FAIL because `services.artifact_quality` does not exist.

- [ ] **Step 3: Implement helper module**

Create `services/artifact_quality.py`:

```python
"""Deterministic quality checks for intermediate LLM artifacts."""

from __future__ import annotations

from typing import Literal

from schemas import PointFeedback, QualityFlag, ReactionPoint, ServicePlanInput, TargetUserPersonaCard
from services.brief_evidence import has_brief_feature_overlap, introduces_unsupported_solution

QualityLevel = Literal["pass", "weak", "fail"]


def assess_reaction_point(
    point: ReactionPoint,
    brief: ServicePlanInput,
    persona: TargetUserPersonaCard,
) -> tuple[QualityLevel, list[QualityFlag]]:
    text = f"{point.title} {point.detail}"
    flags: list[QualityFlag] = []
    if introduces_unsupported_solution(text, brief):
        flags.append(QualityFlag(
            code="unsupported_solution",
            severity="fail",
            message="서비스 기획안에 없는 해결책이나 기능을 언급했습니다.",
            point_id=point.point_id,
        ))
    if not has_brief_feature_overlap(text, brief):
        flags.append(QualityFlag(
            code="no_brief_feature_overlap",
            severity="fail",
            message="기획안의 핵심 기능과 직접 연결되지 않았습니다.",
            point_id=point.point_id,
        ))
    persona_terms = " ".join([
        persona.one_line_summary,
        persona.life_context,
        " ".join(persona.user_goals),
        " ".join(persona.pain_points),
    ])
    if not any(term in text for term in persona_terms.split() if len(term) >= 2):
        flags.append(QualityFlag(
            code="weak_persona_context",
            severity="weak",
            message="페르소나의 구체적 맥락 연결이 약합니다.",
            point_id=point.point_id,
        ))
    if any(flag.severity == "fail" for flag in flags):
        return "fail", flags
    if flags:
        return "weak", flags
    return "pass", []


def assess_feedback(
    feedback: PointFeedback,
    brief: ServicePlanInput,
) -> tuple[QualityLevel, list[QualityFlag]]:
    flags: list[QualityFlag] = []
    if introduces_unsupported_solution(feedback.comment, brief):
        flags.append(QualityFlag(
            code="unsupported_solution",
            severity="fail",
            message="교차 리뷰가 기획안에 없는 해결책이나 기능을 제안했습니다.",
            point_id=feedback.target_point_id,
        ))
    if len(feedback.comment.strip()) < 30:
        flags.append(QualityFlag(
            code="too_short",
            severity="weak",
            message="교차 리뷰 코멘트가 너무 짧아 판단 근거가 약합니다.",
            point_id=feedback.target_point_id,
        ))
    if any(flag.severity == "fail" for flag in flags):
        return "fail", flags
    if flags:
        return "weak", flags
    return "pass", []
```

- [ ] **Step 4: Verify**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_artifact_quality -v
.\.venv\Scripts\python.exe -m ruff check services\artifact_quality.py tests\test_artifact_quality.py --no-cache
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add services/artifact_quality.py tests/test_artifact_quality.py
git commit -m "feat: add deterministic artifact quality checks"
```

---

### Task 4: Add f2 Opinion Quality Reports Without LLM Repair

**Files:**
- Modify: `nodes/f2_opinion.py`
- Create or modify: `tests/test_f2_opinion.py`

- [ ] **Step 1: Write failing f2 quality tests**

If `tests/test_f2_opinion.py` does not exist, create it. Add:

```python
import unittest

from nodes.f2_opinion import _build_opinion_quality_report
from schemas import Opinion, ReactionPoint, ServicePlanInput, TargetUserPersonaCard


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농가는 사진과 음성 설명으로 상품을 등록하고 소비자는 산지 배송으로 주문한다.",
        title="산지 직거래",
        description="농가와 소비자를 직접 연결한다.",
        target="농촌 생산자, 도시 소비자",
        key_features=["사진·음성 상품 등록", "소비자 주문", "산지 배송"],
        concerns="배송 책임",
    )


def _persona() -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id="persona_a",
        source_uuid="source",
        display_name="테스트",
        age_group="50s",
        sex="여자",
        occupation="온라인 판매원",
        region="경남",
        one_line_summary="온라인 판매를 한다.",
        life_context="상품 사진을 자주 올린다.",
        user_goals=["상품 등록 시간을 줄이기"],
        pain_points=["등록 과정이 번거로움"],
        speaking_style="차분한 말투",
    )


class OpinionQualityTests(unittest.TestCase):
    def test_build_opinion_quality_report_classifies_points(self) -> None:
        opinion = Opinion(
            persona_id="persona_a",
            positive_points=[
                ReactionPoint(
                    point_id="a_pos_01",
                    title="사진 등록이 쉬움",
                    detail="나는 상품 사진을 자주 올리기 때문에 사진과 음성으로 등록하는 흐름이 짧으면 좋다.",
                )
            ],
            negative_points=[
                ReactionPoint(
                    point_id="a_neg_01",
                    title="정산 자동화",
                    detail="나는 실시간 정산 자동화 대시보드가 있으면 좋겠다.",
                )
            ],
            would_use=True,
            would_use_description="사진 등록이 쉬우면 써볼 수 있다.",
        )

        report = _build_opinion_quality_report(opinion, _brief(), _persona())

        self.assertIn("a_pos_01", report.pass_point_ids)
        self.assertIn("a_neg_01", report.fail_point_ids)
        self.assertTrue(any(flag.code == "unsupported_solution" for flag in report.flags))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f2_opinion -v
```

Expected: FAIL because `_build_opinion_quality_report` does not exist.

- [ ] **Step 3: Implement quality report builder**

In `nodes/f2_opinion.py`, import:

```python
from schemas import OpinionQualityReport
from services.artifact_quality import assess_reaction_point
```

Add before `generate_opinion`:

```python
def _build_opinion_quality_report(
    opinion: Opinion,
    brief: ServicePlanInput,
    persona: TargetUserPersonaCard,
) -> OpinionQualityReport:
    report = OpinionQualityReport(persona_id=opinion.persona_id)
    for point in [*opinion.positive_points, *opinion.negative_points]:
        level, flags = assess_reaction_point(point, brief, persona)
        report.flags.extend(flags)
        if level == "pass":
            report.pass_point_ids.append(point.point_id)
        elif level == "weak":
            report.weak_point_ids.append(point.point_id)
        else:
            report.fail_point_ids.append(point.point_id)
    return report
```

In `generate_opinion`, after `opinion = Opinion(...)`, return both:

```python
    quality = _build_opinion_quality_report(opinion, brief, persona)
    return {
        f"opinion_{slot}": opinion,
        f"opinion_quality_{slot}": quality,
    }
```

- [ ] **Step 4: Pass target quality to f3 route**

In `route_reviews`, include the opposite quality report:

```python
        Send("generate_review", {
            "reviewer": state["persona_a"],
            "target_opinion": state["opinion_b"],
            "target_opinion_quality": state.get("opinion_quality_b"),
            "brief": state["brief"],
            "slot": "a",
        }),
```

and:

```python
        Send("generate_review", {
            "reviewer": state["persona_b"],
            "target_opinion": state["opinion_a"],
            "target_opinion_quality": state.get("opinion_quality_a"),
            "brief": state["brief"],
            "slot": "b",
        }),
```

- [ ] **Step 5: Verify**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f2_opinion tests.test_artifact_quality -v
.\.venv\Scripts\python.exe -m ruff check nodes\f2_opinion.py tests\test_f2_opinion.py --no-cache
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add nodes/f2_opinion.py tests/test_f2_opinion.py
git commit -m "feat: attach quality reports to first opinions"
```

---

### Task 5: Make f3 Review One Point At A Time

**Files:**
- Modify: `nodes/f3_review.py`
- Create or modify: `tests/test_f3_review.py`

- [ ] **Step 1: Write failing f3 tests**

Add `tests/test_f3_review.py`:

```python
import unittest
from unittest.mock import patch

from nodes.f3_review import _reviewable_points, generate_review
from schemas import (
    Opinion,
    OpinionQualityReport,
    PointFeedback,
    ReactionPoint,
    ServicePlanInput,
    TargetUserPersonaCard,
)


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농가는 사진과 음성 설명으로 상품을 등록하고 소비자는 산지 배송으로 주문한다.",
        title="산지 직거래",
        description="농가와 소비자를 직접 연결한다.",
        target="농촌 생산자, 도시 소비자",
        key_features=["사진·음성 상품 등록", "소비자 주문", "산지 배송"],
        concerns="배송 책임",
    )


def _persona() -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id="persona_reviewer",
        source_uuid="source",
        display_name="리뷰어",
        age_group="50s",
        sex="여자",
        occupation="온라인 판매원",
        region="경남",
        one_line_summary="온라인 판매를 한다.",
        life_context="상품 사진을 자주 올린다.",
        user_goals=["상품 등록 시간을 줄이기"],
        pain_points=["등록 과정이 번거로움"],
        speaking_style="차분한 말투",
    )


def _opinion() -> Opinion:
    return Opinion(
        persona_id="persona_target",
        positive_points=[
            ReactionPoint(point_id="target_pos_01", title="사진 등록", detail="사진과 음성 등록이 쉽다."),
            ReactionPoint(point_id="target_pos_02", title="정산 자동화", detail="정산 자동화가 있으면 좋다."),
        ],
        negative_points=[],
        would_use=True,
        would_use_description="써볼 수 있다.",
    )


class ReviewQualityTests(unittest.TestCase):
    def test_reviewable_points_excludes_failed_opinion_points(self) -> None:
        quality = OpinionQualityReport(
            persona_id="persona_target",
            pass_point_ids=["target_pos_01"],
            fail_point_ids=["target_pos_02"],
        )

        points = _reviewable_points(_opinion(), quality)

        self.assertEqual([point.point_id for point in points], ["target_pos_01"])

    def test_generate_review_calls_llm_once_per_reviewable_point(self) -> None:
        quality = OpinionQualityReport(
            persona_id="persona_target",
            pass_point_ids=["target_pos_01"],
            fail_point_ids=["target_pos_02"],
        )
        feedback = PointFeedback(
            target_point_id="target_pos_01",
            agreement="agree",
            comment="사진 등록이 짧아지면 실제 판매 준비 시간이 줄어들어 공감된다.",
        )

        with patch("nodes.f3_review._generate_point_feedback", return_value=feedback) as call:
            update = generate_review({
                "reviewer": _persona(),
                "target_opinion": _opinion(),
                "target_opinion_quality": quality,
                "brief": _brief(),
                "slot": "a",
            })

        call.assert_called_once()
        review = update["review_a"]
        report = update["review_quality_a"]
        self.assertEqual([item.target_point_id for item in review.point_feedbacks], ["target_pos_01"])
        self.assertIn("target_pos_01", report.pass_feedback_ids)
        self.assertTrue(any(flag.code == "skipped_failed_opinion_point" for flag in report.flags))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f3_review -v
```

Expected: FAIL because `_reviewable_points`, `_generate_point_feedback`, and `review_quality_a` return behavior do not exist.

- [ ] **Step 3: Add point-level draft and prompt**

In `nodes/f3_review.py`, replace `_ReviewDraft` usage with a point-level draft:

```python
class _PointReviewDraft(BaseModel):
    agreement: Literal["agree", "disagree"]
    comment: str = Field(
        description="상대 포인트 하나에 대한 반응. 새 기능을 제안하지 말고 내 사용 판단 변화만 2~3문장으로 설명."
    )
    effect_on_would_use: Literal["increase", "decrease", "same"] = "same"
```

Create:

```python
_point_llm = ChatUpstage(model="solar-pro3").with_structured_output(_PointReviewDraft)

_POINT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 아래 페르소나입니다. 상대 의견의 포인트 하나만 읽고 반응하세요. "
        "서비스 기획안에 없는 새 기능, 인증, 자동화, 모니터링, 알고리즘을 제안하지 마세요. "
        "상대 의견을 반복하지 말고 내 사용 판단이 어떻게 달라지는지만 말하세요.\n\n"
        "## 내 페르소나\n"
        "이름: {display_name}\n"
        "요약: {one_line_summary}\n"
        "생활 맥락: {life_context}\n"
        "목표: {user_goals}\n"
        "불편함: {pain_points}\n"
        "말투: {speaking_style}\n\n"
        "## 준수사항\n{guardrails}",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "설명: {description}\n"
        "핵심 기능:\n{key_features}\n"
        "우려사항: {concerns}\n\n"
        "## 상대 포인트\n"
        "point_id: {point_id}\n"
        "title: {point_title}\n"
        "detail: {point_detail}\n\n"
        "이 포인트에 대해 동의/반대와 이유를 작성하세요.",
    ),
])
```

- [ ] **Step 4: Implement reviewable point selection**

Add:

```python
def _reviewable_points(
    target: Opinion,
    quality: OpinionQualityReport | None,
) -> list[ReactionPoint]:
    points = [*target.positive_points, *target.negative_points]
    if quality is None:
        return points
    blocked = set(quality.fail_point_ids)
    return [point for point in points if point.point_id not in blocked]
```

- [ ] **Step 5: Implement point feedback generation**

Add:

```python
def _generate_point_feedback(
    reviewer: TargetUserPersonaCard,
    brief: ServicePlanInput,
    point: ReactionPoint,
) -> PointFeedback:
    chain = _POINT_PROMPT | _point_llm
    draft: _PointReviewDraft = chain.invoke({
        "display_name": reviewer.display_name,
        "one_line_summary": reviewer.one_line_summary,
        "life_context": reviewer.life_context,
        "user_goals": "\n".join(f"- {g}" for g in reviewer.user_goals),
        "pain_points": "\n".join(f"- {p}" for p in reviewer.pain_points),
        "speaking_style": reviewer.speaking_style,
        "guardrails": "\n".join(f"- {g}" for g in reviewer.guardrails),
        "title": brief.title or "",
        "description": brief.description or "",
        "key_features": "\n".join(f"- {f}" for f in brief.key_features),
        "concerns": brief.concerns or "",
        "point_id": point.point_id,
        "point_title": point.title,
        "point_detail": point.detail,
    })
    return PointFeedback(
        target_point_id=point.point_id,
        agreement=draft.agreement,
        comment=draft.comment,
    )
```

- [ ] **Step 6: Rewrite generate_review quality flow**

In `generate_review`:

```python
    target_quality = state.get("target_opinion_quality")
    reviewable = _reviewable_points(target, target_quality)
    feedbacks = [
        _generate_point_feedback(reviewer, brief, point)
        for point in reviewable
    ]
    quality = _build_review_quality_report(
        reviewer_id=reviewer.card_id,
        target=target,
        target_quality=target_quality,
        feedbacks=feedbacks,
        brief=brief,
    )
    review = Review(
        reviewer_id=reviewer.card_id,
        target_id=target.persona_id,
        point_feedbacks=feedbacks,
        overall_comment=_review_overall_comment(feedbacks),
        revised_would_use=_revised_would_use(feedbacks),
    )
    return {
        f"review_{slot}": review,
        f"review_quality_{slot}": quality,
    }
```

Add deterministic helpers:

```python
def _review_overall_comment(feedbacks: list[PointFeedback]) -> str:
    if not feedbacks:
        return "리뷰 가능한 포인트가 부족해 종합 판단을 보류합니다."
    disagree_count = sum(1 for item in feedbacks if item.agreement == "disagree")
    if disagree_count > len(feedbacks) / 2:
        return "상대 의견을 검토한 결과 사용 판단을 낮추는 우려가 더 많았습니다."
    return "상대 의견을 검토한 결과 일부 우려는 있지만 사용 판단을 크게 낮추지는 않았습니다."


def _revised_would_use(feedbacks: list[PointFeedback]) -> bool:
    if not feedbacks:
        return False
    disagree_count = sum(1 for item in feedbacks if item.agreement == "disagree")
    return disagree_count <= len(feedbacks) / 2
```

Add `_build_review_quality_report` using `assess_feedback`; include `skipped_failed_opinion_point` flags for `target_quality.fail_point_ids`.

- [ ] **Step 7: Verify**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f3_review tests.test_artifact_quality -v
.\.venv\Scripts\python.exe -m ruff check nodes\f3_review.py tests\test_f3_review.py --no-cache
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add nodes/f3_review.py tests/test_f3_review.py
git commit -m "feat: review opinion points one at a time"
```

---

### Task 6: Deterministic f4 Decision Gate

**Files:**
- Modify: `nodes/f4_supervisor.py`
- Modify: `tests/test_f4_supervisor.py`

- [ ] **Step 1: Write failing f4 tests**

Append to `tests/test_f4_supervisor.py`:

```python
from nodes.f4_supervisor import _decision_from_quality, _strip_decision_tokens
from schemas import OpinionQualityReport, QualityFlag, ReviewQualityReport
```

Add tests:

```python
    def test_decision_from_quality_rechecks_review_failures(self) -> None:
        state = {
            "opinion_quality_a": OpinionQualityReport(persona_id="persona_a"),
            "opinion_quality_b": OpinionQualityReport(persona_id="persona_b"),
            "review_quality_a": ReviewQualityReport(
                reviewer_id="persona_a",
                target_id="persona_b",
                flags=[
                    QualityFlag(
                        code="unsupported_solution",
                        severity="fail",
                        message="없는 기능 제안",
                        point_id="b_pos_01",
                    )
                ],
            ),
            "review_quality_b": ReviewQualityReport(reviewer_id="persona_b", target_id="persona_a"),
        }

        self.assertEqual(_decision_from_quality(state), "[재검토]")

    def test_decision_from_quality_holds_opinion_weakness(self) -> None:
        state = {
            "opinion_quality_a": OpinionQualityReport(
                persona_id="persona_a",
                flags=[
                    QualityFlag(
                        code="weak_persona_context",
                        severity="weak",
                        message="맥락 약함",
                        point_id="a_pos_01",
                    )
                ],
            ),
            "opinion_quality_b": OpinionQualityReport(persona_id="persona_b"),
            "review_quality_a": ReviewQualityReport(reviewer_id="persona_a", target_id="persona_b"),
            "review_quality_b": ReviewQualityReport(reviewer_id="persona_b", target_id="persona_a"),
        }

        self.assertEqual(_decision_from_quality(state), "[보류]")

    def test_strip_decision_tokens_removes_conflicting_llm_tokens(self) -> None:
        text = "[통과]\n1. 종합 판단\n좋습니다.\n[재검토] 다시 봐야 합니다."

        cleaned = _strip_decision_tokens(text)

        self.assertNotIn("[통과]", cleaned)
        self.assertNotIn("[재검토]", cleaned)
        self.assertIn("종합 판단", cleaned)
```

- [ ] **Step 2: Run failing f4 tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f4_supervisor -v
```

Expected: FAIL because helpers do not exist.

- [ ] **Step 3: Implement deterministic decision helpers**

In `nodes/f4_supervisor.py`, add:

```python
def _quality_flags(state: ProjectState) -> list[QualityFlag]:
    flags: list[QualityFlag] = []
    for key in ("opinion_quality_a", "opinion_quality_b", "review_quality_a", "review_quality_b"):
        report = state.get(key)
        if report:
            flags.extend(report.flags)
    return flags


def _decision_from_quality(state: ProjectState) -> str:
    flags = _quality_flags(state)
    review_fail = any(
        flag.severity == "fail"
        for key in ("review_quality_a", "review_quality_b")
        for flag in (state.get(key).flags if state.get(key) else [])
    )
    if review_fail:
        return "[재검토]"
    if any(flag.severity == "fail" for flag in flags):
        return "[재검토]"
    if any(flag.severity == "weak" for flag in flags):
        return "[보류]"
    return "[통과]"


def _strip_decision_tokens(text: str) -> str:
    for token in ("[통과]", "[보류]", "[재검토]"):
        text = text.replace(token, "")
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip()).strip()
```

- [ ] **Step 4: Update supervisor prompt**

Change the system prompt to say:

```python
"최종 판단 토큰 [통과], [보류], [재검토]는 작성하지 마세요. "
"당신은 판단의 본문 근거만 작성합니다. "
```

- [ ] **Step 5: Apply deterministic prefix in supervisor_finalize**

Replace final return logic:

```python
    body = chain.invoke(_build_supervisor_prompt_vars(state))
    body = _strip_decision_tokens(body)
    decision = _decision_from_quality(state)
    return {"final_review_text": f"{decision}\n{body}".strip()}
```

- [ ] **Step 6: Verify**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f4_supervisor -v
.\.venv\Scripts\python.exe -m ruff check nodes\f4_supervisor.py tests\test_f4_supervisor.py --no-cache
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add nodes/f4_supervisor.py tests/test_f4_supervisor.py
git commit -m "feat: make final decision deterministic"
```

---

### Task 7: Add Node Quality Evaluation Script

**Files:**
- Create: `scripts/evaluate_node_quality.py`

- [ ] **Step 1: Create evaluation script**

Create `scripts/evaluate_node_quality.py`:

```python
"""Run one sample through the graph and print node-level quality artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import graph
from scripts.run_brief_eval import BRIEFS


def _flag_summary(report) -> str:
    if report is None:
        return "none"
    parts = [f"{flag.severity}:{flag.code}:{flag.point_id or '-'}" for flag in report.flags]
    return ", ".join(parts) if parts else "clean"


def run(sample_key: str) -> int:
    if sample_key not in BRIEFS:
        print(f"unknown sample: {sample_key}")
        return 2
    result = {}
    print(f"SAMPLE {sample_key}")
    for chunk in graph.stream({"raw_input": BRIEFS[sample_key]}, stream_mode="updates"):
        for node_name, update in chunk.items():
            keys = [key for key, value in (update or {}).items() if value is not None]
            print(f"NODE {node_name}: {', '.join(keys) if keys else '-'}")
            if update:
                result.update(update)
    print("\nQUALITY")
    for key in ("opinion_quality_a", "opinion_quality_b", "review_quality_a", "review_quality_b"):
        print(f"{key}: {_flag_summary(result.get(key))}")
    print("\nFINAL")
    print((result.get("final_review_text") or "")[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1] if len(sys.argv) > 1 else "farm_direct"))
```

- [ ] **Step 2: Smoke test imports**

Run:

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\evaluate_node_quality.py
```

Expected: PASS.

- [ ] **Step 3: Commit**

```powershell
git add scripts/evaluate_node_quality.py
git commit -m "chore: add node quality evaluation script"
```

---

### Task 8: Full Verification And Sample Quality Check

**Files:**
- No source changes unless verification exposes a defect in files changed by this plan.

- [ ] **Step 1: Run focused tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_quality_contract tests.test_brief_evidence tests.test_artifact_quality tests.test_f2_opinion tests.test_f3_review tests.test_f4_supervisor -v
```

Expected: PASS.

- [ ] **Step 2: Run full tests**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Expected: PASS.

- [ ] **Step 3: Run Ruff**

```powershell
.\.venv\Scripts\python.exe -m ruff check schemas.py state.py services nodes scripts tests --no-cache
```

Expected: PASS.

- [ ] **Step 4: Run one live sample**

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_node_quality.py farm_direct
```

Expected:

```text
NODE f0_parse: brief
NODE select_personas: persona_a, persona_b, persona_selection_reason
NODE generate_opinion: opinion_*, opinion_quality_*
NODE generate_review: review_*, review_quality_*
NODE supervisor_finalize: final_review_text
```

Quality acceptance criteria:

```text
- f1 selected personas fit the brief.
- f2 has at least two pass or weak points per persona.
- f3 does not propose new features such as 정산 자동화, 실시간 모니터링, 인증 unless present in brief.
- f4 final text starts with exactly one decision token.
- If any fail flag exists, final text does not start with [통과].
```

- [ ] **Step 5: Record residual risk**

If the live sample fails due to `RateLimitError` or timeout, do not patch the code. Record:

```text
Live sample not completed due to external API rate limit.
Unit tests and deterministic quality checks passed.
```

- [ ] **Step 6: Final commit only if verification fixes were needed**

If a source/test fix was required during verification:

```powershell
git add schemas.py state.py services/brief_evidence.py services/artifact_quality.py nodes/f2_opinion.py nodes/f3_review.py nodes/f4_supervisor.py scripts/evaluate_node_quality.py tests
git commit -m "test: verify small state quality pipeline"
```

If no source changes were needed, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage: The plan preserves isolated node LLM calls, adds quality reports to state, prevents weak state artifacts from being treated as reliable facts, makes f3 point-level, and makes f4 decision deterministic.
- Scope check: `f1_select` is intentionally not modified.
- Type consistency: `QualityFlag`, `OpinionQualityReport`, and `ReviewQualityReport` are defined before f2/f3/f4 tasks use them.
- Risk control: No f2 repair LLM is introduced. f3 uses more LLM calls, but each call is smaller and constrained to one target point.
- No placeholders: Every task has exact files, commands, expected outcomes, and code snippets.
