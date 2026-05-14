# Persona RAG Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fixed persona selection with retrieval-based persona candidate search, LLM pair selection, and visible selection evidence in the Streamlit demo.

**Architecture:** Keep persona review generation unchanged after `persona_a` and `persona_b`. Add a preparation path that samples/cards/indexes personas into Chroma, then add runtime graph nodes for service-plan metadata extraction and candidate retrieval before `select_personas`. Retrieval is high-recall multi-query search; final two-person selection is a structured LLM rerank with deterministic fallback.

**Tech Stack:** Python 3.11, Pydantic v2, LangGraph, LangChain Upstage, Upstage embeddings, ChromaDB, Streamlit, unittest, Ruff.

---

## File Structure

- Modify `schemas.py`: add retrieval metadata and evidence schemas.
- Modify `state.py`: add `brief_meta`, `persona_candidates`, and `persona_selection_reason`.
- Create `services/persona_index.py`: index paths, document/metadata formatting, Chroma status, retrieval helpers, fallback query generation, ranking, and deduplication.
- Modify `services/pipeline_runner.py`: expose persona index status and node labels.
- Create `nodes/f0_meta.py`: extract `ServicePlanMeta` after `f0_parse`.
- Create `nodes/f1_retrieve.py`: retrieve evidence-rich candidate personas.
- Modify `nodes/f1_select.py`: select final two personas from retrieved candidates and store selection reasons.
- Modify `graph.py`: insert `extract_service_meta` and `retrieve_persona_candidates` before `select_personas`.
- Modify `app.py`: show index status, retrieval query evidence, candidate pool, and final selection reasons.
- Complete `scripts/sample_hf_personas.py`: reproducible Hugging Face sample extraction.
- Create `scripts/build_persona_index.py`: generate sample persona cards and build the local Chroma index.
- Modify `.gitignore`: ignore generated sample/index artifacts.
- Modify `pyproject.toml` and `requirements.txt`: add ChromaDB if not already installed.
- Create tests:
  - `tests/test_retrieval_schemas.py`
  - `tests/test_persona_index.py`
  - `tests/test_f0_meta.py`
  - `tests/test_f1_select_rag.py`
  - Update `tests/test_pipeline_runner.py`

---

### Task 1: Retrieval Schemas and State

**Files:**
- Modify: `schemas.py`
- Modify: `state.py`
- Test: `tests/test_retrieval_schemas.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/test_retrieval_schemas.py`:

```python
import unittest

from schemas import (
    PersonaRetrievalQuery,
    PersonaSearchCandidate,
    PersonaSelectionReason,
    ServicePlanMeta,
    TargetUserPersonaCard,
)


def _card(card_id: str = "persona_abc123") -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid="source-abc123",
        display_name="테스트 페르소나",
        age_group="60s",
        sex="여자",
        occupation="시장 상인",
        region="서울",
        one_line_summary="시장 경험이 많은 사용자",
        life_context="동네 시장에서 장사를 오래 해 왔습니다.",
        user_goals=["간단한 등록"],
        pain_points=["복잡한 앱 사용"],
        positive_triggers=["음성 안내"],
        negative_triggers=["작은 글씨"],
        speaking_style="현실적이고 직설적인 말투",
    )


class RetrievalSchemaTests(unittest.TestCase):
    def test_service_plan_meta_records_multi_query_strategy(self) -> None:
        meta = ServicePlanMeta(
            domain="농산물 직거래",
            target_users=["농촌 생산자", "도시 소비자"],
            use_contexts=["상품 등록", "산지 배송"],
            age_groups=["60s", "70plus"],
            regions=["충청남"],
            occupation_keywords=["농업", "시장"],
            digital_literacy="mixed",
            price_sensitivity="high",
            trust_sensitivity="high",
            accessibility_need="medium",
            review_focuses=["등록 난이도", "품질 신뢰"],
            hard_filters={"age_group": ["60s", "70plus"]},
            retrieval_queries=[
                PersonaRetrievalQuery(
                    query_type="primary_fit",
                    query="농산물을 직접 등록하고 판매할 수 있는 고령 생산자",
                    intent="핵심 생산자 관점",
                ),
                PersonaRetrievalQuery(
                    query_type="risk_probe",
                    query="스마트폰 사용이 익숙하지 않아 등록 과정에서 어려움을 겪을 사용자",
                    intent="디지털 접근성 리스크",
                ),
                PersonaRetrievalQuery(
                    query_type="contrast",
                    query="농산물을 구매하는 도시 소비자 관점",
                    intent="소비자 대비 관점",
                ),
            ],
        )

        self.assertEqual(meta.retrieval_queries[0].query_type, "primary_fit")
        self.assertEqual(meta.hard_filters["age_group"], ["60s", "70plus"])
        self.assertEqual(meta.trust_sensitivity, "high")

    def test_search_candidate_preserves_query_hit_evidence(self) -> None:
        candidate = PersonaSearchCandidate(
            card=_card(),
            score=0.12,
            query_hits=["primary_fit", "risk_probe"],
            matched_metadata={"age_group": "60s", "region": "서울"},
            retrieval_reason="핵심 타겟과 접근성 리스크에 모두 걸림",
        )

        self.assertEqual(candidate.card.card_id, "persona_abc123")
        self.assertEqual(candidate.query_hits, ["primary_fit", "risk_probe"])
        self.assertEqual(candidate.matched_metadata["region"], "서울")

    def test_selection_reason_keeps_pair_and_query_coverage(self) -> None:
        reason = PersonaSelectionReason(
            selected_card_ids=["persona_a", "persona_b"],
            per_persona_reasons={
                "persona_a": "생산자 등록 과정을 검증할 수 있음",
                "persona_b": "소비자 신뢰 관점을 검증할 수 있음",
            },
            pair_reason="생산자와 소비자 관점을 동시에 볼 수 있음",
            query_coverage={
                "primary_fit": ["persona_a"],
                "contrast": ["persona_b"],
            },
            expected_review_angles=["등록 난이도", "품질 신뢰"],
        )

        self.assertEqual(reason.selected_card_ids, ["persona_a", "persona_b"])
        self.assertIn("contrast", reason.query_coverage)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m unittest tests.test_retrieval_schemas -v
```

Expected: FAIL with import errors for `PersonaRetrievalQuery`, `ServicePlanMeta`, `PersonaSearchCandidate`, and `PersonaSelectionReason`.

- [ ] **Step 3: Add schemas**

Modify `schemas.py` by adding these type aliases and models after `ServicePlanInput`:

```python
RetrievalQueryType = Literal["primary_fit", "risk_probe", "contrast"]
AgeGroup = Literal["20s", "30s", "40s", "50s", "60s", "70plus"]
SensitivityLevel = Literal["low", "medium", "high", "mixed"]
HardFilterValue = str | int | bool | list[str] | list[int]


class PersonaRetrievalQuery(BaseModel):
    """Vector search query for one persona retrieval intent."""

    query_type: RetrievalQueryType
    query: str
    intent: str


class ServicePlanMeta(BaseModel):
    """Retrieval strategy extracted from the service plan."""

    domain: str | None = None
    target_users: list[str] = Field(default_factory=list)
    use_contexts: list[str] = Field(default_factory=list)

    age_groups: list[AgeGroup] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    occupation_keywords: list[str] = Field(default_factory=list)

    digital_literacy: SensitivityLevel | None = None
    price_sensitivity: SensitivityLevel | None = None
    trust_sensitivity: SensitivityLevel | None = None
    accessibility_need: SensitivityLevel | None = None

    review_focuses: list[str] = Field(default_factory=list)
    hard_filters: dict[str, HardFilterValue] = Field(default_factory=dict)
    retrieval_queries: list[PersonaRetrievalQuery] = Field(default_factory=list)


class PersonaSearchCandidate(BaseModel):
    """Persona candidate retrieved from the vector index."""

    card: TargetUserPersonaCard
    score: float | None = None
    query_hits: list[RetrievalQueryType] = Field(default_factory=list)
    matched_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    retrieval_reason: str | None = None


class PersonaSelectionReason(BaseModel):
    """Structured reason for the final two-person panel selection."""

    selected_card_ids: list[str]
    per_persona_reasons: dict[str, str] = Field(default_factory=dict)
    pair_reason: str
    query_coverage: dict[str, list[str]] = Field(default_factory=dict)
    expected_review_angles: list[str] = Field(default_factory=list)
```

Add these names to `__all__`:

```python
    "RetrievalQueryType",
    "AgeGroup",
    "SensitivityLevel",
    "HardFilterValue",
    "PersonaRetrievalQuery",
    "ServicePlanMeta",
    "PersonaSearchCandidate",
    "PersonaSelectionReason",
```

- [ ] **Step 4: Update graph state typing**

Modify `state.py` imports:

```python
from schemas import (
    Opinion,
    PersonaSearchCandidate,
    PersonaSelectionReason,
    Review,
    ServicePlanInput,
    ServicePlanMeta,
    TargetUserPersonaCard,
)
```

Add fields to `ProjectState`:

```python
    brief_meta: ServicePlanMeta
    persona_candidates: list[PersonaSearchCandidate]
    persona_selection_reason: PersonaSelectionReason
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m unittest tests.test_retrieval_schemas -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add schemas.py state.py tests/test_retrieval_schemas.py
git commit -m "feat: add persona retrieval schemas"
```

---

### Task 2: Pure Persona Index Utilities

**Files:**
- Create: `services/persona_index.py`
- Test: `tests/test_persona_index.py`

- [ ] **Step 1: Write failing utility tests**

Create `tests/test_persona_index.py`:

```python
import unittest

from schemas import (
    PersonaRetrievalQuery,
    PersonaSearchCandidate,
    ServicePlanInput,
    ServicePlanMeta,
    TargetUserPersonaCard,
)
from services.persona_index import (
    build_persona_document,
    build_persona_metadata,
    build_where_filter,
    ensure_retrieval_queries,
    merge_candidate_batches,
)


def _card(card_id: str, age_group: str = "60s") -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=f"사용자 {card_id}",
        age_group=age_group,
        sex="남자",
        occupation="농업 종사자",
        region="충청남",
        one_line_summary="농산물 판매 경험이 있습니다.",
        life_context="스마트폰으로 사진을 찍어 가족에게 보내곤 합니다.",
        user_goals=["농산물 판매"],
        pain_points=["작은 글씨", "복잡한 가입"],
        positive_triggers=["간단한 등록"],
        negative_triggers=["배송 책임"],
        speaking_style="차분하고 현실적인 말투",
    )


class PersonaIndexUtilityTests(unittest.TestCase):
    def test_build_persona_document_contains_searchable_card_fields(self) -> None:
        document = build_persona_document(_card("persona_a"))

        self.assertIn("농산물 판매 경험", document)
        self.assertIn("작은 글씨", document)
        self.assertIn("간단한 등록", document)

    def test_build_persona_metadata_uses_simple_filter_values(self) -> None:
        metadata = build_persona_metadata(_card("persona_a"))

        self.assertEqual(metadata["card_id"], "persona_a")
        self.assertEqual(metadata["age_group"], "60s")
        self.assertEqual(metadata["province"], "충청남")

    def test_build_where_filter_supports_exact_and_inclusion_filters(self) -> None:
        where = build_where_filter({"age_group": ["60s", "70plus"], "sex": "남자"})

        self.assertEqual(
            where,
            {
                "$and": [
                    {"age_group": {"$in": ["60s", "70plus"]}},
                    {"sex": "남자"},
                ]
            },
        )

    def test_ensure_retrieval_queries_fills_missing_query_types(self) -> None:
        brief = ServicePlanInput(
            raw_text="농산물 직거래 앱",
            title="농산물 직거래",
            description="농촌 생산자와 도시 소비자를 연결합니다.",
            target="고령 생산자와 도시 소비자",
            key_features=["상품 등록", "산지 배송"],
            concerns="스마트폰 등록이 어려울 수 있습니다.",
        )
        meta = ServicePlanMeta(
            retrieval_queries=[
                PersonaRetrievalQuery(
                    query_type="primary_fit",
                    query="농산물을 직접 판매하려는 생산자",
                    intent="핵심 타겟",
                )
            ]
        )

        completed = ensure_retrieval_queries(meta, brief)
        query_types = [query.query_type for query in completed.retrieval_queries]

        self.assertEqual(query_types, ["primary_fit", "risk_probe", "contrast"])

    def test_merge_candidate_batches_deduplicates_and_preserves_query_hits(self) -> None:
        first = PersonaSearchCandidate(
            card=_card("persona_a"),
            score=0.30,
            query_hits=["primary_fit"],
        )
        duplicate = PersonaSearchCandidate(
            card=_card("persona_a"),
            score=0.10,
            query_hits=["risk_probe"],
        )
        second = PersonaSearchCandidate(
            card=_card("persona_b", age_group="70plus"),
            score=0.20,
            query_hits=["contrast"],
        )

        merged = merge_candidate_batches([[first], [duplicate], [second]])

        self.assertEqual([candidate.card.card_id for candidate in merged], ["persona_a", "persona_b"])
        self.assertEqual(merged[0].score, 0.10)
        self.assertEqual(merged[0].query_hits, ["primary_fit", "risk_probe"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_persona_index -v
```

Expected: FAIL because `services.persona_index` does not exist.

- [ ] **Step 3: Implement pure utilities**

Create `services/persona_index.py`:

```python
"""Persona vector index helpers for retrieval-based selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from schemas import (
    HardFilterValue,
    PersonaRetrievalQuery,
    PersonaSearchCandidate,
    RetrievalQueryType,
    ServicePlanInput,
    ServicePlanMeta,
    TargetUserPersonaCard,
)

ROOT_DIR = Path(__file__).parent.parent
PERSONA_SAMPLE_CARDS_PATH = ROOT_DIR / "data" / "personas" / "persona_cards.sample.json"
PERSONA_CHROMA_PATH = ROOT_DIR / "data" / "personas" / "chroma"
PERSONA_COLLECTION_NAME = "nemotron_persona_cards"
REQUIRED_QUERY_TYPES: tuple[RetrievalQueryType, ...] = (
    "primary_fit",
    "risk_probe",
    "contrast",
)


@dataclass(frozen=True)
class PersonaIndexStatus:
    exists: bool
    count: int
    path: Path
    collection_name: str
    message: str


def build_persona_document(card: TargetUserPersonaCard) -> str:
    parts = [
        f"이름: {card.display_name}",
        f"연령대: {card.age_group or '-'}",
        f"성별: {card.sex or '-'}",
        f"직업: {card.occupation or '-'}",
        f"지역: {card.region or '-'}",
        f"한 줄 요약: {card.one_line_summary}",
        f"생활 맥락: {card.life_context}",
        "목표: " + " / ".join(card.user_goals),
        "불편함: " + " / ".join(card.pain_points),
        "긍정 트리거: " + " / ".join(card.positive_triggers),
        "부정 트리거: " + " / ".join(card.negative_triggers),
        f"말투: {card.speaking_style}",
    ]
    return "\n".join(parts)


def build_persona_metadata(card: TargetUserPersonaCard) -> dict[str, str | int | float | bool]:
    metadata: dict[str, str | int | float | bool] = {
        "card_id": card.card_id,
        "source_uuid": card.source_uuid,
    }
    if card.age_group:
        metadata["age_group"] = card.age_group
    if card.sex:
        metadata["sex"] = card.sex
    if card.occupation:
        metadata["occupation"] = card.occupation
    if card.region:
        metadata["province"] = card.region
    return metadata


def build_where_filter(hard_filters: dict[str, HardFilterValue]) -> dict[str, Any] | None:
    clauses: list[dict[str, Any]] = []
    for key in sorted(hard_filters):
        value = hard_filters[key]
        if isinstance(value, list):
            clauses.append({key: {"$in": value}})
        else:
            clauses.append({key: value})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _fallback_query(query_type: RetrievalQueryType, brief: ServicePlanInput) -> PersonaRetrievalQuery:
    title = brief.title or "입력 서비스"
    target = brief.target or "잠재 사용자"
    concerns = brief.concerns or "사용성, 신뢰, 가격, 접근성"
    features = ", ".join(brief.key_features) if brief.key_features else brief.description or brief.raw_text

    if query_type == "primary_fit":
        return PersonaRetrievalQuery(
            query_type="primary_fit",
            query=f"{title}의 핵심 타겟인 {target} 관점에서 {features}를 사용할 사람",
            intent="핵심 타겟 적합도",
        )
    if query_type == "risk_probe":
        return PersonaRetrievalQuery(
            query_type="risk_probe",
            query=f"{title}에서 {concerns} 문제를 민감하게 드러낼 사용자",
            intent="주요 리스크 검증",
        )
    return PersonaRetrievalQuery(
        query_type="contrast",
        query=f"{title}에 대해 핵심 타겟과 다른 관점을 줄 수 있지만 여전히 관련 있는 사용자",
        intent="상반된 검토 관점",
    )


def ensure_retrieval_queries(meta: ServicePlanMeta, brief: ServicePlanInput) -> ServicePlanMeta:
    existing = {query.query_type: query for query in meta.retrieval_queries if query.query.strip()}
    completed = [existing.get(query_type) or _fallback_query(query_type, brief) for query_type in REQUIRED_QUERY_TYPES]
    return meta.model_copy(update={"retrieval_queries": completed})


def _query_priority(query_hits: list[RetrievalQueryType]) -> int:
    if "primary_fit" in query_hits:
        return 0
    if "risk_probe" in query_hits:
        return 1
    return 2


def _rank_key(candidate: PersonaSearchCandidate) -> tuple[int, int, float, str]:
    score = candidate.score if candidate.score is not None else 999999.0
    return (-len(candidate.query_hits), _query_priority(candidate.query_hits), score, candidate.card.card_id)


def merge_candidate_batches(
    batches: list[list[PersonaSearchCandidate]],
) -> list[PersonaSearchCandidate]:
    by_card_id: dict[str, PersonaSearchCandidate] = {}
    for batch in batches:
        for candidate in batch:
            card_id = candidate.card.card_id
            existing = by_card_id.get(card_id)
            if existing is None:
                by_card_id[card_id] = candidate
                continue

            query_hits = list(dict.fromkeys([*existing.query_hits, *candidate.query_hits]))
            scores = [score for score in [existing.score, candidate.score] if score is not None]
            best_score = min(scores) if scores else None
            matched_metadata = {**existing.matched_metadata, **candidate.matched_metadata}
            by_card_id[card_id] = existing.model_copy(
                update={
                    "score": best_score,
                    "query_hits": query_hits,
                    "matched_metadata": matched_metadata,
                    "retrieval_reason": existing.retrieval_reason or candidate.retrieval_reason,
                }
            )

    return sorted(by_card_id.values(), key=_rank_key)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_persona_index -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add services/persona_index.py tests/test_persona_index.py
git commit -m "feat: add persona index utilities"
```

---

### Task 3: Chroma Dependency, Generated Artifacts, and Index Status

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Modify: `services/persona_index.py`
- Test: `tests/test_persona_index.py`

- [ ] **Step 1: Add failing index status test**

Append this test to `tests/test_persona_index.py`:

```python
from pathlib import Path
from unittest.mock import patch

from services.persona_index import get_persona_index_status
```

Add this method to `PersonaIndexUtilityTests`:

```python
    def test_get_persona_index_status_reports_missing_path(self) -> None:
        missing_path = Path("C:/tmp/persona-index-test-missing")

        with patch("services.persona_index.PERSONA_CHROMA_PATH", missing_path):
            status = get_persona_index_status()

        self.assertFalse(status.exists)
        self.assertEqual(status.count, 0)
        self.assertIn("missing", status.message)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m unittest tests.test_persona_index.PersonaIndexUtilityTests.test_get_persona_index_status_reports_missing_path -v
```

Expected: FAIL because `get_persona_index_status` does not exist.

- [ ] **Step 3: Add Chroma dependency**

Modify `pyproject.toml` dependencies:

```toml
    "chromadb==1.5.9",
```

Modify `requirements.txt`:

```text
chromadb==1.5.9
```

If lockfile refresh is part of the execution environment, run:

```powershell
uv lock
```

Expected: `uv.lock` updates without dependency resolution errors.

- [ ] **Step 4: Ignore generated persona RAG artifacts**

Append to `.gitignore`:

```gitignore

# Persona RAG generated artifacts
data/personas/raw_personas.sample.json
data/personas/persona_cards.sample.json
data/personas/chroma/
```

- [ ] **Step 5: Implement index status**

Append to `services/persona_index.py`:

```python
def get_persona_index_status() -> PersonaIndexStatus:
    if not PERSONA_CHROMA_PATH.exists():
        return PersonaIndexStatus(
            exists=False,
            count=0,
            path=PERSONA_CHROMA_PATH,
            collection_name=PERSONA_COLLECTION_NAME,
            message="missing index path",
        )

    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(PERSONA_CHROMA_PATH))
        collection = client.get_collection(PERSONA_COLLECTION_NAME)
        count = collection.count()
    except Exception as exc:
        return PersonaIndexStatus(
            exists=False,
            count=0,
            path=PERSONA_CHROMA_PATH,
            collection_name=PERSONA_COLLECTION_NAME,
            message=f"unavailable index: {exc}",
        )

    return PersonaIndexStatus(
        exists=count >= 2,
        count=count,
        path=PERSONA_CHROMA_PATH,
        collection_name=PERSONA_COLLECTION_NAME,
        message=f"{count} indexed persona cards",
    )
```

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m unittest tests.test_persona_index -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add pyproject.toml requirements.txt uv.lock .gitignore services/persona_index.py tests/test_persona_index.py
git commit -m "feat: add chroma index status"
```

---

### Task 4: Offline Sampling and Index Build Scripts

**Files:**
- Modify: `scripts/sample_hf_personas.py`
- Create: `scripts/build_persona_index.py`
- Modify: `services/persona_index.py`
- Test: `tests/test_persona_index.py`

- [ ] **Step 1: Add document batch helper test**

Append imports to `tests/test_persona_index.py`:

```python
from services.persona_index import build_chroma_records
```

Add this method:

```python
    def test_build_chroma_records_creates_parallel_lists(self) -> None:
        cards = [_card("persona_a"), _card("persona_b", age_group="70plus")]

        records = build_chroma_records(cards)

        self.assertEqual(records["ids"], ["persona_a", "persona_b"])
        self.assertEqual(len(records["documents"]), 2)
        self.assertEqual(records["metadatas"][0]["card_id"], "persona_a")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m unittest tests.test_persona_index.PersonaIndexUtilityTests.test_build_chroma_records_creates_parallel_lists -v
```

Expected: FAIL because `build_chroma_records` does not exist.

- [ ] **Step 3: Add Chroma record helper**

Append to `services/persona_index.py`:

```python
def build_chroma_records(cards: list[TargetUserPersonaCard]) -> dict[str, list[Any]]:
    return {
        "ids": [card.card_id for card in cards],
        "documents": [build_persona_document(card) for card in cards],
        "metadatas": [build_persona_metadata(card) for card in cards],
    }
```

- [ ] **Step 4: Complete Hugging Face sampling script**

Replace `scripts/sample_hf_personas.py` with:

```python
"""Sample Nemotron Korean personas from Hugging Face into a local JSON artifact."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import load_dataset

from schemas import RawNemotronPersona

ROOT_DIR = Path(__file__).parent.parent
OUT_PATH = ROOT_DIR / "data" / "personas" / "raw_personas.sample.json"
DATASET_NAME = "nvidia/Nemotron-Personas-Korea"


def _load_rows(limit: int, seed: int) -> list[dict[str, Any]]:
    dataset = load_dataset(DATASET_NAME, split="train", streaming=True)
    rng = random.Random(seed)
    reservoir: list[dict[str, Any]] = []

    for index, row in enumerate(dataset):
        item = dict(row)
        if len(reservoir) < limit:
            reservoir.append(item)
            continue
        replacement_index = rng.randint(0, index)
        if replacement_index < limit:
            reservoir[replacement_index] = item

    return reservoir


def sample_personas(limit: int, seed: int, out_path: Path) -> list[RawNemotronPersona]:
    rows = _load_rows(limit=limit, seed=seed)
    personas = [RawNemotronPersona(**row) for row in rows]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([persona.model_dump() for persona in personas], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return personas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--seed", type=int, default=40)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    personas = sample_personas(limit=args.limit, seed=args.seed, out_path=args.out)
    print(f"saved {len(personas)} raw personas to {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create Chroma index build script**

Create `scripts/build_persona_index.py`:

```python
"""Build a local Chroma index for sampled persona cards."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from dotenv import load_dotenv
from langchain_upstage import UpstageEmbeddings

from schemas import RawNemotronPersona, TargetUserPersonaCard
from scripts.generate_user_cards import generate_cards
from services.persona_index import (
    PERSONA_CHROMA_PATH,
    PERSONA_COLLECTION_NAME,
    PERSONA_SAMPLE_CARDS_PATH,
    build_chroma_records,
)

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
RAW_SAMPLE_PATH = ROOT_DIR / "data" / "personas" / "raw_personas.sample.json"


def _load_raws(path: Path) -> list[RawNemotronPersona]:
    raw_list = json.loads(path.read_text(encoding="utf-8"))
    return [RawNemotronPersona(**item) for item in raw_list]


def _load_cards(path: Path) -> list[TargetUserPersonaCard]:
    raw_cards = json.loads(path.read_text(encoding="utf-8"))
    return [TargetUserPersonaCard(**item) for item in raw_cards]


async def _ensure_cards(raw_path: Path, cards_path: Path, regenerate: bool) -> list[TargetUserPersonaCard]:
    if cards_path.exists() and not regenerate:
        return _load_cards(cards_path)

    raws = _load_raws(raw_path)
    return await generate_cards(raws, cards_path)


def _embed_documents(documents: list[str], batch_size: int) -> list[list[float]]:
    embeddings = UpstageEmbeddings(model="embedding-passage", embed_batch_size=batch_size)
    return embeddings.embed_documents(documents)


async def build_index(
    raw_path: Path,
    cards_path: Path,
    chroma_path: Path,
    *,
    regenerate_cards: bool,
    reset_index: bool,
    batch_size: int,
) -> int:
    cards = await _ensure_cards(raw_path, cards_path, regenerate_cards)
    if reset_index and chroma_path.exists():
        shutil.rmtree(chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)

    records = build_chroma_records(cards)
    vectors = _embed_documents(records["documents"], batch_size=batch_size)

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(PERSONA_COLLECTION_NAME)
    collection.upsert(
        ids=records["ids"],
        documents=records["documents"],
        embeddings=vectors,
        metadatas=records["metadatas"],
    )
    return collection.count()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_SAMPLE_PATH)
    parser.add_argument("--cards", type=Path, default=PERSONA_SAMPLE_CARDS_PATH)
    parser.add_argument("--chroma", type=Path, default=PERSONA_CHROMA_PATH)
    parser.add_argument("--regenerate-cards", action="store_true")
    parser.add_argument("--reset-index", action="store_true")
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()

    count = asyncio.run(
        build_index(
            raw_path=args.raw,
            cards_path=args.cards,
            chroma_path=args.chroma,
            regenerate_cards=args.regenerate_cards,
            reset_index=args.reset_index,
            batch_size=args.batch_size,
        )
    )
    print(f"indexed {count} persona cards into {args.chroma}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run unit tests**

Run:

```powershell
python -m unittest tests.test_persona_index -v
```

Expected: PASS.

- [ ] **Step 7: Run import check**

Run:

```powershell
python -c "import scripts.sample_hf_personas; import scripts.build_persona_index; print('script imports ok')"
```

Expected: prints `script imports ok`.

- [ ] **Step 8: Commit**

```powershell
git add scripts/sample_hf_personas.py scripts/build_persona_index.py services/persona_index.py tests/test_persona_index.py
git commit -m "feat: add persona index build scripts"
```

---

### Task 5: Runtime Chroma Retrieval Service

**Files:**
- Modify: `services/persona_index.py`
- Test: `tests/test_persona_index.py`

- [ ] **Step 1: Add fake collection retrieval tests**

Append these classes and tests to `tests/test_persona_index.py`:

```python
from services.persona_index import retrieve_candidates_from_collection


class FakeCollection:
    def __init__(self) -> None:
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        query_text = kwargs["query_texts"][0]
        where = kwargs.get("where")
        if where and "risk" in query_text:
            return {"ids": [[]], "distances": [[]], "metadatas": [[]]}
        if "primary" in query_text:
            return {
                "ids": [["persona_a"]],
                "distances": [[0.1]],
                "metadatas": [[{"card_id": "persona_a", "age_group": "60s"}]],
            }
        if "risk" in query_text:
            return {
                "ids": [["persona_b"]],
                "distances": [[0.2]],
                "metadatas": [[{"card_id": "persona_b", "age_group": "70plus"}]],
            }
        return {
            "ids": [["persona_a", "persona_c"]],
            "distances": [[0.3, 0.4]],
            "metadatas": [[
                {"card_id": "persona_a", "age_group": "60s"},
                {"card_id": "persona_c", "age_group": "40s"},
            ]],
        }
```

Add this method:

```python
    def test_retrieve_candidates_from_collection_runs_multi_query_and_fallback(self) -> None:
        cards = {
            "persona_a": _card("persona_a"),
            "persona_b": _card("persona_b", age_group="70plus"),
            "persona_c": _card("persona_c", age_group="40s"),
        }
        brief = ServicePlanInput(raw_text="raw", title="서비스", description="설명")
        meta = ServicePlanMeta(
            hard_filters={"age_group": ["60s", "70plus"]},
            retrieval_queries=[
                PersonaRetrievalQuery(query_type="primary_fit", query="primary user", intent="primary"),
                PersonaRetrievalQuery(query_type="risk_probe", query="risk user", intent="risk"),
                PersonaRetrievalQuery(query_type="contrast", query="contrast user", intent="contrast"),
            ],
        )
        collection = FakeCollection()

        candidates = retrieve_candidates_from_collection(
            collection=collection,
            cards_by_id=cards,
            brief=brief,
            meta=meta,
            k_per_query=3,
            min_results_per_query=1,
        )

        self.assertEqual(
            [candidate.card.card_id for candidate in candidates],
            ["persona_a", "persona_b", "persona_c"],
        )
        self.assertEqual(candidates[0].query_hits, ["primary_fit", "contrast"])
        self.assertGreaterEqual(len(collection.calls), 4)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m unittest tests.test_persona_index.PersonaIndexUtilityTests.test_retrieve_candidates_from_collection_runs_multi_query_and_fallback -v
```

Expected: FAIL because `retrieve_candidates_from_collection` does not exist.

- [ ] **Step 3: Implement retrieval from injected collection**

Append to `services/persona_index.py`:

```python
def _result_to_candidates(
    result: dict[str, Any],
    cards_by_id: dict[str, TargetUserPersonaCard],
    query_type: RetrievalQueryType,
) -> list[PersonaSearchCandidate]:
    ids = result.get("ids", [[]])[0]
    distances = result.get("distances", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    candidates: list[PersonaSearchCandidate] = []
    for index, card_id in enumerate(ids):
        card = cards_by_id.get(card_id)
        if card is None:
            continue
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        score = distances[index] if index < len(distances) else None
        candidates.append(
            PersonaSearchCandidate(
                card=card,
                score=score,
                query_hits=[query_type],
                matched_metadata=metadata,
                retrieval_reason=f"{query_type} query match",
            )
        )
    return candidates


def retrieve_candidates_from_collection(
    *,
    collection: Any,
    cards_by_id: dict[str, TargetUserPersonaCard],
    brief: ServicePlanInput,
    meta: ServicePlanMeta,
    k_per_query: int = 8,
    min_results_per_query: int = 2,
) -> list[PersonaSearchCandidate]:
    meta = ensure_retrieval_queries(meta, brief)
    where = build_where_filter(meta.hard_filters)
    batches: list[list[PersonaSearchCandidate]] = []

    for retrieval_query in meta.retrieval_queries:
        result = collection.query(
            query_texts=[retrieval_query.query],
            n_results=k_per_query,
            where=where,
        )
        candidates = _result_to_candidates(result, cards_by_id, retrieval_query.query_type)
        if len(candidates) < min_results_per_query and where is not None:
            result = collection.query(
                query_texts=[retrieval_query.query],
                n_results=k_per_query,
            )
            candidates = _result_to_candidates(result, cards_by_id, retrieval_query.query_type)
        batches.append(candidates)

    return merge_candidate_batches(batches)
```

- [ ] **Step 4: Add local Chroma loader function**

Append:

```python
def load_sample_cards(path: Path = PERSONA_SAMPLE_CARDS_PATH) -> list[TargetUserPersonaCard]:
    import json

    raw_cards = json.loads(path.read_text(encoding="utf-8"))
    return [TargetUserPersonaCard(**item) for item in raw_cards]


def retrieve_persona_candidates(
    brief: ServicePlanInput,
    meta: ServicePlanMeta,
) -> list[PersonaSearchCandidate]:
    import chromadb

    cards = load_sample_cards()
    cards_by_id = {card.card_id: card for card in cards}
    client = chromadb.PersistentClient(path=str(PERSONA_CHROMA_PATH))
    collection = client.get_collection(PERSONA_COLLECTION_NAME)
    return retrieve_candidates_from_collection(
        collection=collection,
        cards_by_id=cards_by_id,
        brief=brief,
        meta=meta,
    )
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m unittest tests.test_persona_index -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add services/persona_index.py tests/test_persona_index.py
git commit -m "feat: add runtime persona retrieval"
```

---

### Task 6: Service Plan Metadata Node

**Files:**
- Create: `nodes/f0_meta.py`
- Test: `tests/test_f0_meta.py`

- [ ] **Step 1: Write tests for metadata completion**

Create `tests/test_f0_meta.py`:

```python
import unittest

from nodes.f0_meta import complete_service_plan_meta
from schemas import PersonaRetrievalQuery, ServicePlanInput, ServicePlanMeta


class ServicePlanMetaTests(unittest.TestCase):
    def test_complete_service_plan_meta_fills_missing_queries(self) -> None:
        brief = ServicePlanInput(
            raw_text="농산물 직거래 앱",
            title="농산물 직거래",
            description="농촌 생산자와 도시 소비자를 연결합니다.",
            target="고령 생산자와 도시 소비자",
            key_features=["사진 등록", "산지 배송"],
            concerns="스마트폰 등록과 품질 신뢰가 걱정됩니다.",
        )
        meta = ServicePlanMeta(
            domain="농산물",
            retrieval_queries=[
                PersonaRetrievalQuery(
                    query_type="primary_fit",
                    query="농산물을 직접 판매하는 고령 생산자",
                    intent="핵심 사용자",
                )
            ],
        )

        completed = complete_service_plan_meta(meta, brief)

        self.assertEqual(
            [query.query_type for query in completed.retrieval_queries],
            ["primary_fit", "risk_probe", "contrast"],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m unittest tests.test_f0_meta -v
```

Expected: FAIL because `nodes.f0_meta` does not exist.

- [ ] **Step 3: Implement metadata node**

Create `nodes/f0_meta.py`:

```python
"""f0_meta — extract retrieval metadata from the parsed service plan."""

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage

from schemas import ServicePlanInput, ServicePlanMeta
from services.persona_index import ensure_retrieval_queries
from state import ProjectState

load_dotenv()

_llm = ChatUpstage(model="solar-pro3").with_structured_output(ServicePlanMeta)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획안을 페르소나 검색 전략으로 바꾸는 분석가입니다. "
        "hard_filters에는 입력에 명시된 확실한 조건만 넣으세요. "
        "retrieval_queries는 primary_fit, risk_probe, contrast 세 종류를 모두 작성하세요.",
    ),
    (
        "human",
        "원문:\n{raw_text}\n\n"
        "제목: {title}\n"
        "설명: {description}\n"
        "타겟: {target}\n"
        "핵심 기능:\n{key_features}\n"
        "우려사항: {concerns}",
    ),
])


def complete_service_plan_meta(meta: ServicePlanMeta, brief: ServicePlanInput) -> ServicePlanMeta:
    return ensure_retrieval_queries(meta, brief)


def f0_meta(state: ProjectState) -> dict:
    brief = state["brief"]
    chain = _PROMPT | _llm
    meta: ServicePlanMeta = chain.invoke({
        "raw_text": brief.raw_text,
        "title": brief.title or "",
        "description": brief.description or "",
        "target": brief.target or "",
        "key_features": "\n".join(f"- {feature}" for feature in brief.key_features),
        "concerns": brief.concerns or "",
    })
    return {"brief_meta": complete_service_plan_meta(meta, brief)}
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_f0_meta -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add nodes/f0_meta.py tests/test_f0_meta.py
git commit -m "feat: add service plan metadata node"
```

---

### Task 7: Retrieval Node and Fallback to Seed Personas

**Files:**
- Create: `nodes/f1_retrieve.py`
- Modify: `graph.py`
- Modify: `services/pipeline_runner.py`
- Modify: `services/persona_index.py`
- Test: `tests/test_persona_index.py`

- [ ] **Step 1: Add node fallback test**

Append to `tests/test_persona_index.py`:

```python
from unittest.mock import Mock

from nodes.f1_retrieve import retrieve_persona_candidates_node
```

Add this method:

```python
    def test_retrieve_persona_candidates_node_uses_seed_fallback(self) -> None:
        brief = ServicePlanInput(raw_text="raw", title="서비스", description="설명")
        meta = ServicePlanMeta()
        fallback_cards = [_card("persona_a"), _card("persona_b")]

        retrieval = Mock(return_value=[])
        fallback_loader = Mock(return_value=fallback_cards)

        update = retrieve_persona_candidates_node(
            {"brief": brief, "brief_meta": meta},
            retriever=retrieval,
            fallback_loader=fallback_loader,
        )

        self.assertEqual(len(update["persona_candidates"]), 2)
        self.assertEqual(update["persona_candidates"][0].card.card_id, "persona_a")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m unittest tests.test_persona_index.PersonaIndexUtilityTests.test_retrieve_persona_candidates_node_uses_seed_fallback -v
```

Expected: FAIL because `nodes.f1_retrieve` does not exist.

- [ ] **Step 3: Implement retrieval node**

Create `nodes/f1_retrieve.py`:

```python
"""f1_retrieve — retrieve persona candidates before final selection."""

from collections.abc import Callable

from schemas import PersonaSearchCandidate, ServicePlanInput, ServicePlanMeta, TargetUserPersonaCard
from services.persona_index import retrieve_persona_candidates
from services.persona_repository import load_personas
from state import ProjectState


def _fallback_candidates(cards: list[TargetUserPersonaCard]) -> list[PersonaSearchCandidate]:
    return [
        PersonaSearchCandidate(
            card=card,
            score=None,
            query_hits=[],
            matched_metadata={},
            retrieval_reason="seed persona fallback",
        )
        for card in cards[:2]
    ]


def retrieve_persona_candidates_node(
    state: ProjectState,
    *,
    retriever: Callable[[ServicePlanInput, ServicePlanMeta], list[PersonaSearchCandidate]] = retrieve_persona_candidates,
    fallback_loader: Callable[[], list[TargetUserPersonaCard]] = load_personas,
) -> dict:
    brief = state["brief"]
    meta = state["brief_meta"]
    try:
        candidates = retriever(brief, meta)
    except Exception:
        candidates = []

    if len(candidates) < 2:
        candidates = _fallback_candidates(fallback_loader())

    return {"persona_candidates": candidates}
```

- [ ] **Step 4: Wire graph**

Modify `graph.py` imports:

```python
from nodes.f0_meta import f0_meta
from nodes.f1_retrieve import retrieve_persona_candidates_node
```

Register nodes:

```python
builder.add_node("extract_service_meta", f0_meta)
builder.add_node("retrieve_persona_candidates", retrieve_persona_candidates_node)
```

Replace edge:

```python
builder.add_edge("f0_parse", "select_personas")
```

with:

```python
builder.add_edge("f0_parse", "extract_service_meta")
builder.add_edge("extract_service_meta", "retrieve_persona_candidates")
builder.add_edge("retrieve_persona_candidates", "select_personas")
```

- [ ] **Step 5: Update node labels**

Modify `NODE_LABELS` in `services/pipeline_runner.py`:

```python
    "extract_service_meta": "검색 전략 생성",
    "retrieve_persona_candidates": "페르소나 후보 검색",
```

- [ ] **Step 6: Run tests and graph import**

Run:

```powershell
python -m unittest tests.test_persona_index tests.test_f0_meta -v
python -c "import graph; print('graph import ok')"
```

Expected: tests pass and import prints `graph import ok`.

- [ ] **Step 7: Commit**

```powershell
git add graph.py services/pipeline_runner.py nodes/f0_meta.py nodes/f1_retrieve.py tests/test_f0_meta.py tests/test_persona_index.py
git commit -m "feat: wire persona retrieval graph nodes"
```

---

### Task 8: Final Persona Pair Selection from Candidates

**Files:**
- Modify: `nodes/f1_select.py`
- Test: `tests/test_f1_select_rag.py`

- [ ] **Step 1: Write selection tests**

Create `tests/test_f1_select_rag.py`:

```python
import unittest

from nodes.f1_select import select_personas_from_candidates
from schemas import (
    PersonaSearchCandidate,
    PersonaSelectionReason,
    ServicePlanInput,
    TargetUserPersonaCard,
)


def _card(card_id: str) -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=card_id,
        age_group="60s",
        sex="여자",
        occupation="농업 종사자",
        region="충청남",
        one_line_summary="테스트 사용자",
        life_context="테스트 맥락",
        user_goals=["목표"],
        pain_points=["불편"],
        positive_triggers=["긍정"],
        negative_triggers=["부정"],
        speaking_style="간결한 말투",
    )


class PersonaRagSelectionTests(unittest.TestCase):
    def test_select_personas_from_candidates_uses_valid_selector_ids(self) -> None:
        brief = ServicePlanInput(raw_text="raw", title="서비스")
        candidates = [
            PersonaSearchCandidate(card=_card("persona_a"), query_hits=["primary_fit"]),
            PersonaSearchCandidate(card=_card("persona_b"), query_hits=["contrast"]),
            PersonaSearchCandidate(card=_card("persona_c"), query_hits=["risk_probe"]),
        ]
        reason = PersonaSelectionReason(
            selected_card_ids=["persona_c", "persona_a"],
            per_persona_reasons={
                "persona_c": "리스크 관점",
                "persona_a": "핵심 타겟",
            },
            pair_reason="핵심 타겟과 리스크 관점을 함께 본다",
            expected_review_angles=["등록 난이도"],
        )

        selected, selection_reason = select_personas_from_candidates(
            brief=brief,
            candidates=candidates,
            selector=lambda _brief, _candidates: reason,
        )

        self.assertEqual([card.card_id for card in selected], ["persona_c", "persona_a"])
        self.assertEqual(selection_reason.pair_reason, reason.pair_reason)

    def test_select_personas_from_candidates_fills_invalid_ids_from_ranked_candidates(self) -> None:
        brief = ServicePlanInput(raw_text="raw", title="서비스")
        candidates = [
            PersonaSearchCandidate(card=_card("persona_a"), query_hits=["primary_fit"]),
            PersonaSearchCandidate(card=_card("persona_b"), query_hits=["contrast"]),
        ]
        reason = PersonaSelectionReason(
            selected_card_ids=["missing"],
            pair_reason="invalid id test",
        )

        selected, selection_reason = select_personas_from_candidates(
            brief=brief,
            candidates=candidates,
            selector=lambda _brief, _candidates: reason,
        )

        self.assertEqual([card.card_id for card in selected], ["persona_a", "persona_b"])
        self.assertEqual(selection_reason.selected_card_ids, ["persona_a", "persona_b"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m unittest tests.test_f1_select_rag -v
```

Expected: FAIL because `select_personas_from_candidates` does not exist.

- [ ] **Step 3: Refactor `nodes/f1_select.py` selection**

Add imports:

```python
from collections.abc import Callable

from schemas import (
    PersonaSearchCandidate,
    PersonaSelectionReason,
    ServicePlanInput,
    TargetUserPersonaCard,
)
```

Add selector formatting and selection helpers:

```python
Selector = Callable[
    [ServicePlanInput, list[PersonaSearchCandidate]],
    PersonaSelectionReason,
]


def _format_candidate_list(candidates: list[PersonaSearchCandidate]) -> str:
    lines = []
    for candidate in candidates:
        card = candidate.card
        lines.append(
            "\n".join([
                f"- card_id: {card.card_id}",
                f"  이름: {card.display_name}",
                f"  메타: {card.age_group or '-'} / {card.sex or '-'} / {card.occupation or '-'} / {card.region or '-'}",
                f"  요약: {card.one_line_summary}",
                f"  생활 맥락: {card.life_context}",
                f"  검색 히트: {', '.join(candidate.query_hits) or '-'}",
                f"  검색 이유: {candidate.retrieval_reason or '-'}",
            ])
        )
    return "\n\n".join(lines)


_SELECTION_LLM = ChatUpstage(model="solar-pro3").with_structured_output(PersonaSelectionReason)

_SELECTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획 검토를 위한 두 명의 페르소나 패널을 고르는 전문가입니다. "
        "후보 중 정확히 2명을 고르세요. 단순히 유사도 상위 2명이 아니라 "
        "핵심 타겟 적합성, 주요 리스크 검증, 두 사람의 관점 차이를 함께 고려하세요.",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "타겟: {target}\n"
        "설명: {description}\n"
        "핵심 기능:\n{key_features}\n"
        "우려사항: {concerns}\n\n"
        "## 검색된 후보\n{candidate_list}",
    ),
])


def _llm_select_from_candidates(
    brief: ServicePlanInput,
    candidates: list[PersonaSearchCandidate],
) -> PersonaSelectionReason:
    chain = _SELECTION_PROMPT | _SELECTION_LLM
    return chain.invoke({
        "title": brief.title or "",
        "target": brief.target or "",
        "description": brief.description or "",
        "key_features": "\n".join(f"- {feature}" for feature in brief.key_features),
        "concerns": brief.concerns or "",
        "candidate_list": _format_candidate_list(candidates),
    })


def select_personas_from_candidates(
    *,
    brief: ServicePlanInput,
    candidates: list[PersonaSearchCandidate],
    selector: Selector = _llm_select_from_candidates,
) -> tuple[list[TargetUserPersonaCard], PersonaSelectionReason]:
    reason = selector(brief, candidates)
    by_id = {candidate.card.card_id: candidate.card for candidate in candidates}

    selected_ids: list[str] = []
    for card_id in reason.selected_card_ids:
        if card_id in by_id and card_id not in selected_ids:
            selected_ids.append(card_id)

    for candidate in candidates:
        if len(selected_ids) >= _SELECT_COUNT:
            break
        if candidate.card.card_id not in selected_ids:
            selected_ids.append(candidate.card.card_id)

    selected_ids = selected_ids[:_SELECT_COUNT]
    selected = [by_id[card_id] for card_id in selected_ids]
    normalized_reason = reason.model_copy(update={"selected_card_ids": selected_ids})
    return selected, normalized_reason
```

Update `select_personas`:

```python
def select_personas(state: ProjectState) -> dict:
    brief: ServicePlanInput = state["brief"]
    candidates = state.get("persona_candidates", [])

    if candidates:
        selected, reason = select_personas_from_candidates(brief=brief, candidates=candidates)
        return {
            "persona_a": selected[0],
            "persona_b": selected[1],
            "persona_selection_reason": reason,
        }

    pool = load_personas()
    if len(pool) <= _SELECT_COUNT:
        selected = pool
    else:
        selected = _llm_select(brief, pool)

    return {"persona_a": selected[0], "persona_b": selected[1]}
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_f1_select_rag -v
python -m unittest tests.test_persona_index tests.test_f0_meta -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add nodes/f1_select.py tests/test_f1_select_rag.py
git commit -m "feat: select personas from retrieved candidates"
```

---

### Task 9: Pipeline Runner and Streamlit Evidence UI

**Files:**
- Modify: `services/pipeline_runner.py`
- Modify: `app.py`
- Test: `tests/test_pipeline_runner.py`

- [ ] **Step 1: Add pipeline runner index status test**

Append to `tests/test_pipeline_runner.py` imports:

```python
from unittest.mock import Mock

from services.pipeline_runner import get_persona_index_status
```

Add:

```python
    def test_get_persona_index_status_returns_service_status(self) -> None:
        fake_status = Mock(exists=True, count=12, path="index-path", collection_name="cards")

        with patch("services.pipeline_runner.get_index_status", return_value=fake_status):
            status = get_persona_index_status()

        self.assertTrue(status.exists)
        self.assertEqual(status.count, 12)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m unittest tests.test_pipeline_runner.PipelineRunnerTests.test_get_persona_index_status_returns_service_status -v
```

Expected: FAIL because `get_persona_index_status` is not exported from pipeline runner.

- [ ] **Step 3: Update pipeline runner**

Modify imports in `services/pipeline_runner.py`:

```python
from services.persona_index import get_persona_index_status as get_index_status
```

Add function:

```python
def get_persona_index_status():
    return get_index_status()
```

Update `NODE_LABELS` with:

```python
    "extract_service_meta": "검색 전략 생성",
    "retrieve_persona_candidates": "페르소나 후보 검색",
```

- [ ] **Step 4: Update Streamlit imports**

Modify `app.py` import list:

```python
    get_persona_index_status,
```

- [ ] **Step 5: Update sidebar**

Inside `_render_sidebar`, after persona card status:

```python
        index_status = get_persona_index_status()
        st.divider()
        st.subheader("페르소나 검색 인덱스")
        if index_status.exists:
            st.success(f"{index_status.count}개 인덱싱됨")
        else:
            st.warning("검색 인덱스가 준비되지 않았습니다")
        st.caption(str(index_status.path))
        st.caption(index_status.message)
```

- [ ] **Step 6: Add evidence renderers**

Add to `app.py`:

```python
def _render_retrieval_tab(state: dict[str, Any]) -> None:
    meta = state.get("brief_meta")
    candidates = _as_list(state.get("persona_candidates"))
    reason = state.get("persona_selection_reason")

    st.markdown("#### 검색 전략")
    queries = _as_list(_get(meta, "retrieval_queries", []))
    for query in queries:
        st.markdown(f"**{_get(query, 'query_type', '-')}**")
        st.write(_get(query, "query", "-"))
        st.caption(_get(query, "intent", "-"))

    st.markdown("#### 후보 풀")
    if not candidates:
        st.caption("표시할 후보가 없습니다.")
    for candidate in candidates:
        card = _get(candidate, "card")
        with st.container(border=True):
            st.subheader(_get(card, "display_name", "-"))
            st.caption(
                " / ".join(
                    str(item)
                    for item in [
                        _get(card, "age_group"),
                        _get(card, "sex"),
                        _get(card, "occupation"),
                        _get(card, "region"),
                    ]
                    if item
                )
            )
            st.write(_get(card, "one_line_summary", "-"))
            st.caption("query hits: " + ", ".join(_as_list(_get(candidate, "query_hits", []))))
            if _get(candidate, "score") is not None:
                st.caption(f"score: {_get(candidate, 'score')}")

    st.markdown("#### 최종 선택 근거")
    if reason is None:
        st.caption("선택 근거가 없습니다.")
        return
    st.write("페어 구성:", _get(reason, "pair_reason", "-"))
    for card_id, text in dict(_get(reason, "per_persona_reasons", {})).items():
        st.markdown(f"- **{card_id}**: {text}")
```

Update tab list in `_render_results`:

```python
    tabs = st.tabs(["요약 리포트", "후보 검색", "사용자 패널", "1차 반응", "교차 리뷰", "근거 보기"])
```

Update tab body order:

```python
    with tabs[0]:
        _render_summary_report(state)
    with tabs[1]:
        _render_retrieval_tab(state)
    with tabs[2]:
        _render_persona_tab(persona_a, persona_b)
    with tabs[3]:
        _render_opinion_tab(state)
    with tabs[4]:
        _render_review_tab(state)
    with tabs[5]:
        _render_debug_tab(state, events)
```

- [ ] **Step 7: Run tests and import checks**

Run:

```powershell
python -m unittest tests.test_pipeline_runner -v
python -c "import app; import graph; print('imports ok')"
```

Expected: PASS and prints `imports ok`.

- [ ] **Step 8: Commit**

```powershell
git add services/pipeline_runner.py app.py tests/test_pipeline_runner.py
git commit -m "feat: show persona retrieval evidence"
```

---

### Task 10: Full Verification and Manual Demo Path

**Files:**
- No required source changes unless verification reveals a concrete bug.

- [ ] **Step 1: Run unit tests**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run Ruff**

Run:

```powershell
ruff check . --no-cache
```

Expected: no lint errors.

- [ ] **Step 3: Run import check**

Run:

```powershell
python -c "import graph; import app; print('imports ok')"
```

Expected: prints `imports ok`.

- [ ] **Step 4: Build a tiny local index for manual smoke test**

If network/API access is available and approved, run:

```powershell
python scripts/sample_hf_personas.py --limit 20 --seed 40
python scripts/build_persona_index.py --reset-index
```

Expected: first command writes `data/personas/raw_personas.sample.json`; second command prints a line beginning with `indexed ` and ending with ` persona cards into data\\personas\\chroma`.

- [ ] **Step 5: Run Streamlit manually**

Run:

```powershell
.\scripts\run_demo_streamlit.ps1 -NoTrace
```

Expected: Streamlit starts. Sidebar shows persona card status and persona search index status. Running the sample input shows the `후보 검색` tab before the persona/opinion/review tabs.

- [ ] **Step 6: Stop on verification failure**

If any verification command fails, stop execution and record the failing command and error output before changing code. Create a focused follow-up fix task for that concrete failure.

---

## Self-Review Notes

- Spec coverage:
  - Offline sampling/indexing is covered by Task 4.
  - Retrieval schemas and state are covered by Task 1.
  - Conservative filters, multi-query retrieval, dedupe, and ranking are covered by Tasks 2 and 5.
  - Graph integration is covered by Tasks 6 and 7.
  - LLM final pair selection is covered by Task 8.
  - Streamlit evidence is covered by Task 9.
  - Verification is covered by Task 10.
- Placeholder scan:
  - No open-ended implementation steps remain in this plan.
- Type consistency:
  - `PersonaRetrievalQuery`, `ServicePlanMeta`, `PersonaSearchCandidate`, and `PersonaSelectionReason` are defined in Task 1 and reused consistently in later tasks.
  - `retrieval_queries`, `query_hits`, and `hard_filters` match the approved spec.
