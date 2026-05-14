# Persona Embedding Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded keyword pre-rank with a small embedding-cache retrieval layer so any service brief can surface semantically relevant persona candidates before LLM selection.

**Architecture:** Keep `select_personas` and the LLM structured-output flow intact. Add `services/persona_retrieval.py` for selection text, JSON embedding cache loading, pure-Python cosine ranking, and query embedding fallback behavior. Add one offline script to build `data/personas/persona_cards.selected.embeddings.json` using existing `langchain-upstage`.

**Tech Stack:** Python 3.11, Pydantic v2, LangChain Upstage `UpstageEmbeddings`, unittest, JSON cache, no Chroma/numpy/new dependency.

---

## File Structure

- Create: `services/persona_retrieval.py`
  - `brief_selection_text`
  - `persona_selection_text`
  - `persona_text_hash`
  - `cosine_similarity`
  - `rank_personas_for_brief`
- Create: `scripts/build_persona_embedding_cache.py`
  - Builds the JSON cache from `services.persona_repository.load_personas`
- Modify: `nodes/f1_select.py`
  - Remove hardcoded keyword rank helpers
  - Call `rank_personas_for_brief(brief, load_personas())`
- Modify: `tests/test_f1_select.py`
  - Remove keyword-rank tests
  - Verify `select_personas` uses `rank_personas_for_brief`
- Create: `tests/test_persona_retrieval.py`
  - Unit-test cache loading, cosine, missing cache fallback, and ranked order with fake embeddings
- Modify: `.gitignore`
  - Ignore generated embedding cache

---

## Task 1: Retrieval Service Tests

**Files:**
- Create: `tests/test_persona_retrieval.py`

- [ ] **Step 1: Write failing tests**

Create tests for:

```python
import json
import tempfile
import unittest
from pathlib import Path

from schemas import ServicePlanInput, TargetUserPersonaCard
from services.persona_retrieval import (
    brief_selection_text,
    cosine_similarity,
    persona_selection_text,
    persona_text_hash,
    rank_personas_for_brief,
)


def _card(card_id: str, summary: str) -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=f"name-{card_id}",
        age_group="60s",
        sex="남",
        occupation="테스트 직업",
        region="서울",
        one_line_summary=summary,
        life_context="생활 맥락",
        user_goals=["목표"],
        pain_points=["불편"],
        positive_triggers=[],
        negative_triggers=[],
        speaking_style="간결함",
    )


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농산물 산지 직거래",
        title="산지 직거래",
        target="고령 생산자",
        description="사진과 음성으로 상품 등록",
        key_features=["산지 배송"],
        concerns="등록 난이도",
    )


class PersonaRetrievalTests(unittest.TestCase):
    def test_selection_texts_include_core_fields(self) -> None:
        card = _card("persona_a", "농산물 판매자")

        self.assertIn("고령 생산자", brief_selection_text(_brief()))
        self.assertIn("농산물 판매자", persona_selection_text(card))
        self.assertNotIn("name-persona_a", persona_selection_text(card))

    def test_cosine_similarity_orders_vectors(self) -> None:
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_missing_cache_keeps_original_order(self) -> None:
        cards = [_card("persona_a", "A"), _card("persona_b", "B")]

        ranked = rank_personas_for_brief(_brief(), cards, cache_path=Path("missing.json"))

        self.assertEqual([c.card_id for c in ranked], ["persona_a", "persona_b"])

    def test_rank_uses_cached_embeddings_and_fake_query_embedding(self) -> None:
        farm = _card("persona_farm", "농산물 생산자")
        unrelated = _card("persona_other", "게임 이용자")

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "embeddings.json"
            cache_path.write_text(
                json.dumps({
                    "model": "test-model",
                    "items": [
                        {
                            "card_id": farm.card_id,
                            "text_hash": persona_text_hash(persona_selection_text(farm)),
                            "embedding": [1.0, 0.0],
                        },
                        {
                            "card_id": unrelated.card_id,
                            "text_hash": persona_text_hash(persona_selection_text(unrelated)),
                            "embedding": [0.0, 1.0],
                        },
                    ],
                }),
                encoding="utf-8",
            )

            ranked = rank_personas_for_brief(
                _brief(),
                [unrelated, farm],
                cache_path=cache_path,
                embed_query=lambda _text: [1.0, 0.0],
            )

        self.assertEqual([c.card_id for c in ranked], ["persona_farm", "persona_other"])
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_retrieval -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.persona_retrieval'`.

---

## Task 2: Implement Retrieval Service

**Files:**
- Create: `services/persona_retrieval.py`

- [ ] **Step 1: Add minimal implementation**

Implement:
- JSON cache load
- text hash
- pure Python cosine
- cache-missing fallback to original order
- optional `embed_query` injection for tests
- default `UpstageEmbeddings(model="solar-embedding-1-large")`

- [ ] **Step 2: Run retrieval tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_retrieval -v
```

Expected: PASS.

---

## Task 3: Wire `f1_select`

**Files:**
- Modify: `nodes/f1_select.py`
- Modify: `tests/test_f1_select.py`

- [ ] **Step 1: Remove keyword-rank tests**

Delete `RankPersonaPoolTests` and remove `_rank_persona_pool` import from `tests/test_f1_select.py`.

- [ ] **Step 2: Add integration test**

Patch `nodes.f1_select.rank_personas_for_brief` to return a known order, then assert `_llm_select` receives that order.

- [ ] **Step 3: Replace hardcoded rank code**

In `nodes/f1_select.py`:
- remove `_RELATED_TERM_GROUPS`
- remove `_brief_terms`, `_expanded_brief_terms`, `_card_rank_text`, `_score_card_for_brief`, `_rank_persona_pool`
- import `rank_personas_for_brief`
- change `pool = _rank_persona_pool(brief, load_personas())` to `pool = rank_personas_for_brief(brief, load_personas())`

- [ ] **Step 4: Run f1 tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select -v
```

Expected: PASS.

---

## Task 4: Cache Build Script

**Files:**
- Create: `scripts/build_persona_embedding_cache.py`
- Modify: `.gitignore`

- [ ] **Step 1: Add script**

The script:
- loads default personas
- uses `persona_selection_text`
- embeds documents using `UpstageEmbeddings(model="solar-embedding-1-large")`
- writes `data/personas/persona_cards.selected.embeddings.json`

- [ ] **Step 2: Ignore generated cache**

Add:

```gitignore
data/personas/persona_cards.selected.embeddings.json
```

- [ ] **Step 3: Verify import only**

```powershell
.\.venv\Scripts\python.exe -c "import scripts.build_persona_embedding_cache; print('cache script import ok')"
```

Expected: `cache script import ok`.

---

## Task 5: Final Verification

**Files:** No additional source changes unless verification fails.

- [ ] **Step 1: Run target tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_retrieval tests.test_persona_selection_reason tests.test_f1_select -v
```

Expected: PASS.

- [ ] **Step 2: Run imports**

```powershell
.\.venv\Scripts\python.exe -c "import graph; import app; print('imports ok')"
```

Expected: `imports ok`.

- [ ] **Step 3: Run full unittest**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add .gitignore nodes/f1_select.py services/persona_retrieval.py scripts/build_persona_embedding_cache.py tests/test_f1_select.py tests/test_persona_retrieval.py
git commit -m "feat: use embedding cache for persona retrieval"
```

---

## Self-Review Notes

- **Spec coverage:** Replaces hardcoded keyword groups with embedding retrieval while preserving existing LLM selection.
- **Placeholder scan:** No placeholders; steps are concrete.
- **Type consistency:** Retrieval uses existing `ServicePlanInput` and `TargetUserPersonaCard`.
- **Scope:** No Chroma, no numpy, no pair-policy engine, no runtime cache generation.
