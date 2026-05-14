# 페르소나 균형 샘플링 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `selected_100.json`이 연령·직업 두 marginal quota를 동시에 만족하고, 무직·`other` 비중이 캡 아래로 들어오도록 샘플링 파이프라인을 재설계한다.

**Architecture:** `occupation_group` 분류 규칙을 보강하여 `other` 27%를 정상 그룹으로 재분류한 뒤, `make_quotas`를 일반화해 연령·직업 두 축의 marginal quota를 만들고, `select_with_quotas`를 greedy(부족도 + rarity + quality 합산 점수)로 교체한다.

**Tech Stack:** Python 3.11, unittest, ruff. 외부 라이브러리 변경 없음. 데이터 재구축은 기존 `raw_personas.pool_10000.json` 재활용.

**Spec:** `docs/superpowers/specs/2026-05-13-persona-balanced-sampling-design.md`

---

## File Structure

- Modify: `scripts/sample_hf_personas.py` — 상수·분류 규칙·quota 함수·greedy 선택·summary
- Modify: `tests/test_sample_hf_personas.py` — 신규 테스트 + 기존 테스트 시그니처 갱신
- Modify: `data/personas/raw_personas.selected_100.json` — 신규 분포로 재생성
- Modify: `data/personas/raw_personas.candidate_1000.json` — 신규 분포로 재생성
- Modify: `data/personas/persona_selection_summary.json` — 갱신된 summary

---

### Task 1: `occupation_group` 분류 규칙 보강

`other` 27%의 일반 직업을 정상 그룹으로 재분류. 키워드 추가 + 규칙 순서 재배치 (office/professional/arts_media가 field_labor 앞).

**Files:**
- Modify: `scripts/sample_hf_personas.py:168-192` (`occupation_group`)
- Modify: `tests/test_sample_hf_personas.py` (추가 케이스)

- [ ] **Step 1.1: Write failing tests for new keyword mappings**

`tests/test_sample_hf_personas.py`의 `SampleHfPersonasTests` 안에 추가:

```python
def test_occupation_group_classifies_field_labor_extensions(self) -> None:
    self.assertEqual(occupation_group("건물 청소원"), "field_labor")
    self.assertEqual(occupation_group("건물 경비원"), "field_labor")
    self.assertEqual(occupation_group("시설 경비원"), "field_labor")
    self.assertEqual(occupation_group("전기 용접원"), "field_labor")
    self.assertEqual(occupation_group("강구조물 건립원"), "field_labor")
    self.assertEqual(occupation_group("수동 포장원"), "field_labor")
    self.assertEqual(occupation_group("그 외 물품 이동 장비 조작원"), "field_labor")

def test_occupation_group_classifies_service_sales_extensions(self) -> None:
    self.assertEqual(occupation_group("전화 상담원"), "service_sales")
    self.assertEqual(occupation_group("일반 비서"), "service_sales")

def test_occupation_group_classifies_professional_extensions(self) -> None:
    self.assertEqual(occupation_group("범용 소프트웨어 프로그래머"), "professional")
    self.assertEqual(occupation_group("경영 컨설턴트"), "professional")
    self.assertEqual(occupation_group("상품 기획자"), "professional")
    self.assertEqual(occupation_group("정보 시스템 운영자"), "professional")

def test_occupation_group_classifies_self_employed_extensions(self) -> None:
    self.assertEqual(occupation_group("소규모 상점 경영자"), "self_employed")
    self.assertEqual(occupation_group("기업 고위 임원"), "self_employed")

def test_occupation_group_priority_keeps_industry_safety_in_professional(self) -> None:
    # 산업 안전원은 field_labor가 아니라 professional에 잡혀야 한다
    self.assertEqual(occupation_group("산업 안전원"), "professional")

def test_occupation_group_priority_keeps_office_assistant_in_office(self) -> None:
    # 사무 보조원은 field_labor("보조")가 아니라 office("사무")에 잡혀야 한다
    self.assertEqual(occupation_group("사무 보조원"), "office")
```

- [ ] **Step 1.2: Run tests to verify they fail**

```
python -m unittest tests.test_sample_hf_personas -v
```

Expected: 위 6개 케이스가 `AssertionError: 'other' != ...` 또는 `'field_labor' != 'office'` 등으로 FAIL.

- [ ] **Step 1.3: Update `occupation_group` rules**

`scripts/sample_hf_personas.py:168-192`의 `rules` 튜플을 다음으로 교체. 순서 재배치 + 키워드 보강:

```python
rules = (
    ("student", ("학생", "대학생", "고등학생")),
    ("retired_unemployed", ("무직", "은퇴", "퇴직")),
    ("agriculture", ("농", "어업", "축산", "임업")),
    ("self_employed", ("자영", "상인", "사장", "점주", "가게", "경영자", "임원", "점장")),
    ("care_health", ("간호", "의사", "약사", "치료", "보건", "복지", "돌봄", "요양")),
    ("education", ("교사", "강사", "교육", "교수")),
    ("service_sales", ("서비스", "판매", "매장", "영업", "미용", "조리", "음식", "상담원", "비서", "안내")),
    ("office", ("사무", "회사", "행정", "관리", "공무원")),
    ("professional", (
        "개발", "엔지니어", "연구", "디자이너", "전문", "변호", "회계",
        "프로그래머", "컨설턴트", "기획자", "안전원", "시스템 운영",
    )),
    ("arts_media", ("예술", "작가", "음악", "배우", "방송", "콘텐츠")),
    ("field_labor", (
        "기계", "제조", "건설", "운전", "배송", "배달", "하역", "적재", "단순",
        "청소", "경비", "용접", "건립", "포장", "보조", "조작", "수리",
    )),
    ("homemaker", ("주부", "가사")),
)
```

- [ ] **Step 1.4: Run tests to verify they pass**

```
python -m unittest tests.test_sample_hf_personas -v
```

Expected: 신규 6개 + 기존 분류 테스트 PASS.

- [ ] **Step 1.5: Commit**

```
git add scripts/sample_hf_personas.py tests/test_sample_hf_personas.py
git commit -m "feat(sampling): strengthen occupation_group rules for other-bucket recovery"
```

---

### Task 2: 연령 가중치 평탄화 + `make_quotas` 일반화

`AGE_GROUP_WEIGHTS`를 6군 평탄화(17/17/17/17/16/16)로 바꾸고, `make_age_quotas`를 임의 weights를 받는 `make_quotas`로 일반화.

**Files:**
- Modify: `scripts/sample_hf_personas.py:40-47` (`AGE_GROUP_WEIGHTS`)
- Modify: `scripts/sample_hf_personas.py:366-385` (`make_age_quotas` → `make_quotas`)
- Modify: `scripts/sample_hf_personas.py:449-450` (`build_selection_sets` 호출부)
- Modify: `tests/test_sample_hf_personas.py` (신규 테스트)

- [ ] **Step 2.1: Write failing tests**

`tests/test_sample_hf_personas.py`에 추가:

```python
def test_age_group_weights_sum_to_one_hundred_and_flatten_seniors(self) -> None:
    from scripts.sample_hf_personas import AGE_GROUP_WEIGHTS
    self.assertEqual(sum(AGE_GROUP_WEIGHTS.values()), 100)
    self.assertEqual(AGE_GROUP_WEIGHTS["20s"], 17)
    self.assertEqual(AGE_GROUP_WEIGHTS["30s"], 17)
    self.assertEqual(AGE_GROUP_WEIGHTS["40s"], 17)
    self.assertEqual(AGE_GROUP_WEIGHTS["50s"], 17)
    self.assertEqual(AGE_GROUP_WEIGHTS["60s"], 16)
    self.assertEqual(AGE_GROUP_WEIGHTS["70plus"], 16)

def test_make_quotas_scales_arbitrary_weights_to_target_total(self) -> None:
    from scripts.sample_hf_personas import AGE_GROUP_WEIGHTS, make_quotas
    quotas = make_quotas(100, AGE_GROUP_WEIGHTS)
    self.assertEqual(quotas, {
        "20s": 17, "30s": 17, "40s": 17, "50s": 17, "60s": 16, "70plus": 16,
    })
    half = make_quotas(50, AGE_GROUP_WEIGHTS)
    self.assertEqual(sum(half.values()), 50)
```

- [ ] **Step 2.2: Run tests to verify they fail**

```
python -m unittest tests.test_sample_hf_personas -v
```

Expected: `ImportError: cannot import name 'make_quotas'` 또는 `AssertionError: 17 != 12`.

- [ ] **Step 2.3: Update `AGE_GROUP_WEIGHTS`**

`scripts/sample_hf_personas.py:40-47`를 다음으로 교체:

```python
AGE_GROUP_WEIGHTS = {
    "20s": 17,
    "30s": 17,
    "40s": 17,
    "50s": 17,
    "60s": 16,
    "70plus": 16,
}
```

- [ ] **Step 2.4: Generalize `make_age_quotas` to `make_quotas`**

`scripts/sample_hf_personas.py:366-385`의 `make_age_quotas` 정의를 다음으로 교체:

```python
def make_quotas(total: int, weights: dict[str, int]) -> dict[str, int]:
    """Scale a weight dict so values sum to total, keeping integer counts."""

    if total <= 0 or not weights:
        return {group: 0 for group in weights}

    weight_sum = sum(weights.values())
    raw = {group: total * weight / weight_sum for group, weight in weights.items()}
    quotas = {group: int(value) for group, value in raw.items()}
    remainder = total - sum(quotas.values())
    fractional_order = sorted(
        weights.keys(),
        key=lambda group: (-(raw[group] - quotas[group]), -weights[group], group),
    )
    for group in fractional_order[:remainder]:
        quotas[group] += 1
    return quotas
```

- [ ] **Step 2.5: Update call sites in `build_selection_sets`**

`scripts/sample_hf_personas.py:449-450`를 다음으로 교체:

```python
    candidates = select_with_quotas(pool, make_quotas(candidate_size, AGE_GROUP_WEIGHTS))
    selected = select_with_quotas(candidates, make_quotas(selected_size, AGE_GROUP_WEIGHTS))
```

(직업 quota는 Task 4에서 추가)

- [ ] **Step 2.6: Update `build_summary` `age_quotas` lines**

`scripts/sample_hf_personas.py:491-494`를 다음으로 교체:

```python
        "age_quotas": {
            "candidate": make_quotas(candidate_size, AGE_GROUP_WEIGHTS),
            "selected": make_quotas(selected_size, AGE_GROUP_WEIGHTS),
        },
```

- [ ] **Step 2.7: Run tests to verify they pass**

```
python -m unittest tests.test_sample_hf_personas -v
```

Expected: 신규 2개 + 기존 quota·summary 테스트 PASS.

- [ ] **Step 2.8: Commit**

```
git add scripts/sample_hf_personas.py tests/test_sample_hf_personas.py
git commit -m "refactor(sampling): flatten age quota and generalize make_quotas"
```

---

### Task 3: `OCCUPATION_GROUP_WEIGHTS` 신규 상수

직업 quota 정의 (총 100).

**Files:**
- Modify: `scripts/sample_hf_personas.py:39-47` 근처 (상수 블록)
- Modify: `tests/test_sample_hf_personas.py` (신규 테스트)

- [ ] **Step 3.1: Write failing test**

```python
def test_occupation_group_weights_define_balanced_distribution(self) -> None:
    from scripts.sample_hf_personas import OCCUPATION_GROUP_WEIGHTS, make_quotas
    self.assertEqual(sum(OCCUPATION_GROUP_WEIGHTS.values()), 100)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["office"], 13)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["service_sales"], 12)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["field_labor"], 12)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["professional"], 11)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["retired_unemployed"], 10)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["education"], 9)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["care_health"], 8)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["self_employed"], 8)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["agriculture"], 6)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["arts_media"], 6)
    self.assertEqual(OCCUPATION_GROUP_WEIGHTS["homemaker"], 5)
    quotas = make_quotas(100, OCCUPATION_GROUP_WEIGHTS)
    self.assertEqual(quotas["office"], 13)
    self.assertEqual(sum(quotas.values()), 100)
```

- [ ] **Step 3.2: Run test to verify it fails**

```
python -m unittest tests.test_sample_hf_personas.SampleHfPersonasTests.test_occupation_group_weights_define_balanced_distribution -v
```

Expected: `ImportError: cannot import name 'OCCUPATION_GROUP_WEIGHTS'`.

- [ ] **Step 3.3: Add `OCCUPATION_GROUP_WEIGHTS` constant**

`scripts/sample_hf_personas.py`의 `AGE_GROUP_WEIGHTS` 정의 아래(line 48 근처)에 추가:

```python
OCCUPATION_GROUP_ORDER = (
    "office",
    "service_sales",
    "field_labor",
    "professional",
    "retired_unemployed",
    "education",
    "care_health",
    "self_employed",
    "agriculture",
    "arts_media",
    "homemaker",
)
OCCUPATION_GROUP_WEIGHTS = {
    "office": 13,
    "service_sales": 12,
    "field_labor": 12,
    "professional": 11,
    "retired_unemployed": 10,
    "education": 9,
    "care_health": 8,
    "self_employed": 8,
    "agriculture": 6,
    "arts_media": 6,
    "homemaker": 5,
}
```

- [ ] **Step 3.4: Run test to verify it passes**

```
python -m unittest tests.test_sample_hf_personas.SampleHfPersonasTests.test_occupation_group_weights_define_balanced_distribution -v
```

Expected: PASS.

- [ ] **Step 3.5: Commit**

```
git add scripts/sample_hf_personas.py tests/test_sample_hf_personas.py
git commit -m "feat(sampling): add OCCUPATION_GROUP_WEIGHTS quota table"
```

---

### Task 4: Marginal greedy `select_with_quotas` + rarity 조정

`_rarity_score`에서 `occupation_group` 제외(quota가 이미 처리). `select_with_quotas`를 두 quota를 받는 greedy로 교체. `build_selection_sets`도 같이 갱신.

**Files:**
- Modify: `scripts/sample_hf_personas.py:260-298` (`_frequency_maps`, `_rarity_score`, `_rank_rows`)
- Modify: `scripts/sample_hf_personas.py:301-329` (`select_with_quotas`)
- Modify: `scripts/sample_hf_personas.py:430-451` (`build_selection_sets`)
- Modify: `tests/test_sample_hf_personas.py` (신규 테스트 + 기존 quota 테스트 갱신)

- [ ] **Step 4.1: Write failing tests for greedy behavior**

`tests/test_sample_hf_personas.py`의 기존 `test_select_with_quotas_deduplicates_and_balances_age_groups`를 다음으로 교체:

```python
def test_select_with_quotas_deduplicates_and_satisfies_both_quotas(self) -> None:
    rows = [
        enrich_row(_row("old-a", age=71, province="서울", occupation="사무 종사자")),
        enrich_row(_row("old-a", age=71, province="서울", occupation="사무 종사자")),
        enrich_row(_row("old-b", age=78, province="부산", occupation="농업 종사자")),
        enrich_row(_row("young-a", age=28, province="제주", occupation="범용 소프트웨어 프로그래머")),
    ]

    selected = select_with_quotas(
        rows,
        age_quotas={"70plus": 2, "20s": 1},
        occ_quotas={"office": 1, "agriculture": 1, "professional": 1},
    )

    self.assertEqual(sorted(row["uuid"] for row in selected), ["old-a", "old-b", "young-a"])
    self.assertEqual(len({row["uuid"] for row in selected}), 3)
```

추가:

```python
def test_select_with_quotas_spills_supply_shortfall_to_other_groups(self) -> None:
    # agri quota=2지만 풀에 agri 1명. 부족분이 office로 흐른다.
    rows = [
        enrich_row(_row(f"office-{i}", age=40 + i, occupation="사무 종사자")) for i in range(5)
    ] + [
        enrich_row(_row("agri-1", age=64, occupation="농업 종사자")),
    ]

    selected = select_with_quotas(
        rows,
        age_quotas={"40s": 2, "50s": 2, "60s": 2},
        occ_quotas={"office": 4, "agriculture": 2},
    )

    occ_counts = {}
    for row in selected:
        g = row["_selection"]["occupation_group"]
        occ_counts[g] = occ_counts.get(g, 0) + 1
    self.assertEqual(len(selected), 6)
    self.assertEqual(occ_counts.get("agriculture", 0), 1)
    self.assertEqual(occ_counts.get("office", 0), 5)

def test_select_with_quotas_excludes_other_bucket_from_strict_quota(self) -> None:
    # 'other' 그룹은 quota에 포함되지 않아 강제로 채워지지 않는다
    rows = [
        enrich_row(_row(f"office-{i}", age=40 + i, occupation="사무 종사자")) for i in range(3)
    ] + [
        enrich_row(_row(f"other-{i}", age=40 + i, occupation="외계어 미분류 직종"))
        for i in range(3)
    ]

    selected = select_with_quotas(
        rows,
        age_quotas={"40s": 3},
        occ_quotas={"office": 3},
    )

    self.assertEqual(len(selected), 3)
    self.assertTrue(all(row["_selection"]["occupation_group"] == "office" for row in selected))
```

- [ ] **Step 4.2: Run tests to verify they fail**

```
python -m unittest tests.test_sample_hf_personas -v
```

Expected: `TypeError: select_with_quotas() got an unexpected keyword argument 'occ_quotas'` 또는 시그니처 mismatch.

- [ ] **Step 4.3: Update `_frequency_maps` and `_rarity_score` to drop occupation**

`scripts/sample_hf_personas.py:260-286`를 다음으로 교체:

```python
def _frequency_maps(rows: list[dict]) -> dict[str, Counter]:
    fields = ("sex", "province", "family_type", "education_level")
    frequencies = {field: Counter() for field in fields}
    frequencies["digital"] = Counter()
    frequencies["review_axes"] = Counter()

    for row in rows:
        selection = row["_selection"]
        for field in fields:
            frequencies[field][selection.get(field) or "unknown"] += 1
        frequencies["digital"][bool(selection.get("has_digital_signal"))] += 1
        for axis in selection.get("review_axes") or ["general_usability"]:
            frequencies["review_axes"][axis] += 1
    return frequencies


def _rarity_score(row: dict, frequencies: dict[str, Counter]) -> float:
    selection = row["_selection"]
    score = 0.0
    for field in ("sex", "province", "family_type", "education_level"):
        value = selection.get(field) or "unknown"
        score += 1 / max(frequencies[field][value], 1)
    digital = bool(selection.get("has_digital_signal"))
    score += 1 / max(frequencies["digital"][digital], 1)
    for axis in selection.get("review_axes") or ["general_usability"]:
        score += 1 / max(frequencies["review_axes"][axis], 1)
    return score
```

- [ ] **Step 4.4: Replace `select_with_quotas` with marginal greedy**

`scripts/sample_hf_personas.py:301-329`를 다음으로 교체:

```python
_W_AGE_DEFICIT = 10.0
_W_OCC_DEFICIT = 10.0
_W_QUALITY = 0.1


def select_with_quotas(
    rows: list[dict],
    age_quotas: dict[str, int] | None = None,
    occ_quotas: dict[str, int] | None = None,
) -> list[dict]:
    """Select rows by marginal age and occupation quotas using greedy scoring."""

    age_quotas = age_quotas or {}
    occ_quotas = occ_quotas or {}
    target_count = max(sum(age_quotas.values()), sum(occ_quotas.values()))
    if target_count <= 0:
        return []

    deduped = _dedupe_by_uuid(rows)
    remaining = list(deduped)
    selected: list[dict] = []
    age_counts: Counter = Counter()
    occ_counts: Counter = Counter()

    while remaining and len(selected) < target_count:
        frequencies = _frequency_maps(selected) if selected else _frequency_maps([])
        best_index = -1
        best_score = float("-inf")
        for index, row in enumerate(remaining):
            sel = row["_selection"]
            age_g = sel.get("age_group")
            occ_g = sel.get("occupation_group")
            age_deficit = max(0, age_quotas.get(age_g, 0) - age_counts[age_g])
            occ_deficit = max(0, occ_quotas.get(occ_g, 0) - occ_counts[occ_g])
            score = (
                _W_AGE_DEFICIT * age_deficit
                + _W_OCC_DEFICIT * occ_deficit
                + _rarity_score(row, frequencies)
                + _W_QUALITY * _quality_score(row)
            )
            if score > best_score:
                best_score = score
                best_index = index

        if best_index < 0:
            break
        chosen = remaining.pop(best_index)
        selected.append(chosen)
        sel = chosen["_selection"]
        age_counts[sel.get("age_group")] += 1
        occ_counts[sel.get("occupation_group")] += 1

    return selected
```

(`_rank_rows`는 사용처가 사라지므로 제거)

`scripts/sample_hf_personas.py:289-298`의 `_rank_rows` 정의를 삭제.

- [ ] **Step 4.5: Update `build_selection_sets` to pass both quotas**

`scripts/sample_hf_personas.py:430-451`의 함수 본문을 다음으로 교체:

```python
def build_selection_sets(
    source_rows: Iterable[dict],
    *,
    pool_size: int,
    candidate_size: int,
    selected_size: int,
    start_row: int = 0,
    source_window_size: int | None = None,
    max_source_rows: int | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Build pool, candidate, and selected row sets from source rows."""

    pool = collect_pool(
        source_rows,
        pool_size=pool_size,
        start_row=start_row,
        source_window_size=source_window_size,
        max_source_rows=max_source_rows,
    )
    candidates = select_with_quotas(
        pool,
        age_quotas=make_quotas(candidate_size, AGE_GROUP_WEIGHTS),
        occ_quotas=make_quotas(candidate_size, OCCUPATION_GROUP_WEIGHTS),
    )
    selected = select_with_quotas(
        candidates,
        age_quotas=make_quotas(selected_size, AGE_GROUP_WEIGHTS),
        occ_quotas=make_quotas(selected_size, OCCUPATION_GROUP_WEIGHTS),
    )
    return pool, candidates, selected
```

- [ ] **Step 4.6: Run tests to verify they pass**

```
python -m unittest tests.test_sample_hf_personas -v
```

Expected: 신규 3개 + 갱신된 dual-quota 테스트 PASS.

- [ ] **Step 4.7: Commit**

```
git add scripts/sample_hf_personas.py tests/test_sample_hf_personas.py
git commit -m "feat(sampling): select with marginal greedy across age and occupation quotas"
```

---

### Task 5: `build_summary`에 직업 quota 노출

summary JSON에 `occupation_quotas` 포함.

**Files:**
- Modify: `scripts/sample_hf_personas.py:454-498` (`build_summary`)
- Modify: `tests/test_sample_hf_personas.py` (신규 테스트)

- [ ] **Step 5.1: Write failing test**

```python
def test_build_summary_includes_age_and_occupation_quotas(self) -> None:
    from scripts.sample_hf_personas import build_summary
    summary = build_summary(
        seed=1,
        source="file",
        start_row=0,
        source_window_size=None,
        batch_size=0,
        pool_size=10,
        candidate_size=10,
        selected_size=10,
        pool=[],
        candidates=[],
        selected=[],
        max_source_rows=None,
    )
    self.assertIn("age_quotas", summary)
    self.assertIn("occupation_quotas", summary)
    self.assertEqual(sum(summary["age_quotas"]["selected"].values()), 10)
    self.assertEqual(sum(summary["occupation_quotas"]["selected"].values()), 10)
```

- [ ] **Step 5.2: Run test to verify it fails**

```
python -m unittest tests.test_sample_hf_personas.SampleHfPersonasTests.test_build_summary_includes_age_and_occupation_quotas -v
```

Expected: `AssertionError: 'occupation_quotas' not found`.

- [ ] **Step 5.3: Update `build_summary`**

`scripts/sample_hf_personas.py:491-494`의 `age_quotas` 블록 뒤에 추가:

```python
        "age_quotas": {
            "candidate": make_quotas(candidate_size, AGE_GROUP_WEIGHTS),
            "selected": make_quotas(selected_size, AGE_GROUP_WEIGHTS),
        },
        "occupation_quotas": {
            "candidate": make_quotas(candidate_size, OCCUPATION_GROUP_WEIGHTS),
            "selected": make_quotas(selected_size, OCCUPATION_GROUP_WEIGHTS),
        },
```

또한 `scripts/sample_hf_personas.py:484-490`의 `criteria` 리스트를 다음으로 교체:

```python
        "criteria": [
            "필수 persona 텍스트와 핵심 메타데이터가 있는 row만 통과",
            "연령대 6군 평탄화 quota (각 16~17명)",
            "직업군 11군 marginal quota (사무·서비스·기능·전문직 균등 + 무직 캡)",
            "성별·지역·가족형태·학력·디지털 시그널은 rarity score로 균형",
            "접근성·가격·신뢰·개인정보·시간 절약·가족 돌봄·지역 생활·건강·복잡도·고객지원 관점 확보",
        ],
```

- [ ] **Step 5.4: Run tests to verify they pass**

```
python -m unittest tests.test_sample_hf_personas -v
```

Expected: 모든 테스트 PASS.

- [ ] **Step 5.5: Commit**

```
git add scripts/sample_hf_personas.py tests/test_sample_hf_personas.py
git commit -m "feat(sampling): expose occupation quotas in selection summary"
```

---

### Task 6: 기존 풀에서 재선정 + 분포 검증

기존 `raw_personas.pool_10000.json`을 source로 재사용해 candidate/selected를 재생성하고, spec §10 검증 기준을 만족하는지 확인.

**Files:**
- Modify: `data/personas/raw_personas.selected_100.json`
- Modify: `data/personas/raw_personas.candidate_1000.json`
- Modify: `data/personas/persona_selection_summary.json`

- [ ] **Step 6.1: Resample from existing pool**

Run (한 줄 명령, 인라인 파이썬):

```powershell
python -c "import json; from scripts.sample_hf_personas import build_selection_sets, build_summary, write_outputs, DEFAULT_OUTPUT_DIR; rows = json.load(open('data/personas/raw_personas.pool_10000.json', encoding='utf-8')); pool, candidates, selected = build_selection_sets(iter(rows), pool_size=10000, candidate_size=1000, selected_size=100, source_window_size=None); summary = build_summary(seed=40, source='file', start_row=0, source_window_size=None, batch_size=0, pool_size=10000, candidate_size=1000, selected_size=100, pool=pool, candidates=candidates, selected=selected, max_source_rows=None); paths = write_outputs(output_dir=DEFAULT_OUTPUT_DIR, pool=pool, candidates=candidates, selected=selected, summary=summary); print('done', len(selected))"
```

Expected: `done 100` 출력.

- [ ] **Step 6.2: Verify acceptance criteria from summary**

```powershell
python -c "import json,sys,io; sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8'); s=json.load(open('data/personas/persona_selection_summary.json',encoding='utf-8'))['selected']; print('count',s['count']); print('age',s['age_groups']); print('occ',s['occupation_groups']); print('sex',s['sex']); print('prov',s['provinces'])"
```

Expected 출력에서 확인할 수치 (spec §10):

- `count` == 100
- `age_groups`: `{20s:17, 30s:17, 40s:17, 50s:17, 60s:16, 70plus:16}`
- `occupation_groups`: §5 표 ±1 (공급 부족 군 제외)
- 무직(`retired_unemployed`) ≤ 10
- 단일 province 최대값 ≤ 12 (rarity 효과 — 검증만)
- `other` 비중 ≤ 5 (5명 이하)
- 성별: 남·여 각각 45~55명 범위

위 기준 중 하나라도 어긋나면 멈추고 사용자에게 보고. quota 수치 또는 가중치를 조정.

- [ ] **Step 6.3: Commit data files**

```
git add data/personas/raw_personas.selected_100.json data/personas/raw_personas.candidate_1000.json data/personas/persona_selection_summary.json
git commit -m "data: regenerate balanced selected_100 with marginal age and occupation quotas"
```

---

## Self-Review

### Spec coverage

| Spec section | Task |
|---|---|
| §4 연령 quota 평탄화 | Task 2 |
| §5 직업 quota 11군 | Task 3 |
| §6 분류 규칙 보강 + 순서 | Task 1 |
| §7 marginal greedy 알고리즘 | Task 4 |
| §8 변경 범위(`build_summary`) | Task 5 |
| §9 운영 명령 (풀 재활용) | Task 6 |
| §10 검증 기준 | Task 6 Step 6.2 |
| §11 YAGNI 항목 | (구현에 의도적으로 빠짐 — OK) |

### Placeholder scan

- "TBD/TODO/implement later": 없음
- "Add appropriate error handling": 없음
- "Similar to Task N (code 생략)": 없음 — 각 Task가 완성 코드 포함
- 모든 step에 실제 명령·코드·예상 출력 포함

### Type/name 일관성

- `make_quotas(total, weights)` 시그니처는 Task 2에서 정의, Task 4·5에서 동일하게 사용
- `select_with_quotas(rows, age_quotas=..., occ_quotas=...)` 시그니처는 Task 4에서 정의, Task 4 build_selection_sets·테스트에서 동일하게 사용
- `OCCUPATION_GROUP_WEIGHTS` 키 11종은 Task 3 정의와 `occupation_group` Task 1 반환 그룹과 일치(student/homemaker는 quota에 없음 — Task 1 분류는 유지하되 quota에서 student는 명시적 제외, homemaker는 quota 5)
  - **검증**: Task 1 분류 그룹 12종(student, retired_unemployed, agriculture, self_employed, care_health, education, service_sales, office, professional, arts_media, field_labor, homemaker) 중 student는 풀에 0건이므로 quota에서 빠짐. OCCUPATION_GROUP_WEIGHTS 11종은 나머지 11종과 정확히 일치.
