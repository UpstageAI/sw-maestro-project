"""Sample and narrow raw personas from nvidia/Nemotron-Personas-Korea.

The generated raw JSON files keep the source row shape. Derived selection
metadata is used internally and summarized separately.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

DATASET_NAME = "nvidia/Nemotron-Personas-Korea"
DATASET_CONFIG = "default"
DATASET_SPLIT = "train"
DATASET_ROWS_ENDPOINT = "https://datasets-server.huggingface.co/rows"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "personas"
DEFAULT_SEED = 40
DEFAULT_SHUFFLE_BUFFER_SIZE = 100
DEFAULT_API_BATCH_SIZE = 100
DEFAULT_BATCH_DELAY_SECONDS = 0.5
DEFAULT_RETRY_BASE_DELAY_SECONDS = 2.0
DEFAULT_MAX_RETRIES = 6
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}

POOL_FILE_NAME = "raw_personas.pool_10000.json"
CANDIDATE_FILE_NAME = "raw_personas.candidate_1000.json"
SELECTED_FILE_NAME = "raw_personas.selected_100.json"
SUMMARY_FILE_NAME = "persona_selection_summary.json"

AGE_GROUP_ORDER = ("20s", "30s", "40s", "50s", "60s", "70plus")
AGE_GROUP_WEIGHTS = {
    "20s": 17,
    "30s": 17,
    "40s": 17,
    "50s": 17,
    "60s": 16,
    "70plus": 16,
}

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

REQUIRED_FIELDS = (
    "uuid",
    "persona",
    "cultural_background",
    "skills_and_expertise",
    "hobbies_and_interests",
    "career_goals_and_ambitions",
    "age",
    "sex",
    "occupation",
    "province",
)
TEXT_FIELDS = (
    "persona",
    "professional_persona",
    "cultural_background",
    "sports_persona",
    "arts_persona",
    "travel_persona",
    "culinary_persona",
    "family_persona",
    "skills_and_expertise",
    "skills_and_expertise_list",
    "hobbies_and_interests",
    "hobbies_and_interests_list",
    "career_goals_and_ambitions",
)
MIN_PERSONA_CHARS = 60
MIN_TEXT_CHARS = 450

DIGITAL_KEYWORDS = (
    "스마트폰",
    "유튜브",
    "블로그",
    "앱",
    "온라인",
    "키오스크",
    "SNS",
    "음성 입력",
    "인터넷",
    "모바일",
)

REVIEW_AXIS_KEYWORDS = (
    ("accessibility", ("복잡", "가입", "작은 글씨", "키오스크", "음성", "접근", "피로")),
    ("price_sensitivity", ("가격", "비용", "결제", "할인", "부담")),
    ("trust_safety", ("신뢰", "사기", "조심", "확인", "안전")),
    ("privacy_security", ("개인정보", "보안", "인증")),
    ("time_saving", ("시간", "빠르게", "간편", "아끼")),
    ("family_care", ("가족", "자녀", "배우자", "손주", "돌봄")),
    ("local_life", ("동네", "지역", "시장", "생활권", "농촌")),
    ("health_safety", ("건강", "안전", "병원", "약", "운동")),
    ("complexity_resistance", ("복잡", "절차", "가입", "설치", "어려")),
    ("customer_support", ("고객지원", "상담", "문의", "도움", "센터")),
)


def age_group(age: int | None) -> str | None:
    """Return the review-panel age bucket for an age."""

    if age is None:
        return None
    try:
        value = int(age)
    except (TypeError, ValueError):
        return None

    if 20 <= value <= 29:
        return "20s"
    if 30 <= value <= 39:
        return "30s"
    if 40 <= value <= 49:
        return "40s"
    if 50 <= value <= 59:
        return "50s"
    if 60 <= value <= 69:
        return "60s"
    if 70 <= value <= 100:
        return "70plus"
    return None


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def text_blob(row: dict) -> str:
    """Join searchable persona text fields into one text blob."""

    return " ".join(_stringify(row.get(field)).strip() for field in TEXT_FIELDS).strip()


def _has_value(row: dict, field: str) -> bool:
    value = row.get(field)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def is_quality_row(row: dict) -> bool:
    """Return True when a source row has enough metadata and review context."""

    if not all(_has_value(row, field) for field in REQUIRED_FIELDS):
        return False
    if age_group(row.get("age")) is None:
        return False
    if len(_stringify(row.get("persona")).strip()) < MIN_PERSONA_CHARS:
        return False
    return len(text_blob(row)) >= MIN_TEXT_CHARS


def occupation_group(occupation: str | None) -> str:
    """Map raw Korean occupation text to a coarse review-diversity group."""

    text = (occupation or "").strip()
    if not text:
        return "unknown"

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
    for group, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return group
    return "other"


def has_digital_signal(row: dict) -> bool:
    """Return True when row text suggests digital service touchpoints."""

    blob = text_blob(row)
    return any(keyword in blob for keyword in DIGITAL_KEYWORDS)


def review_axes(row: dict) -> list[str]:
    """Return ordered review angles likely represented by a raw persona row."""

    blob = text_blob(row)
    axes = [
        axis
        for axis, keywords in REVIEW_AXIS_KEYWORDS
        if any(keyword in blob for keyword in keywords)
    ]
    return axes or ["general_usability"]


def enrich_row(row: dict) -> dict:
    """Add deterministic selection metadata to a source row copy."""

    enriched = dict(row)
    axes = review_axes(row)
    enriched["_selection"] = {
        "age_group": age_group(row.get("age")),
        "sex": row.get("sex"),
        "province": row.get("province"),
        "occupation_group": occupation_group(row.get("occupation")),
        "family_type": row.get("family_type") or "unknown",
        "education_level": row.get("education_level") or "unknown",
        "has_digital_signal": has_digital_signal(row),
        "review_axes": axes,
        "text_length": len(text_blob(row)),
    }
    return enriched


def _dedupe_by_uuid(rows: Iterable[dict]) -> list[dict]:
    best_by_uuid: dict[str, dict] = {}
    first_index: dict[str, int] = {}
    for index, row in enumerate(rows):
        uuid = str(row.get("uuid") or "")
        if not uuid:
            continue
        enriched = row if "_selection" in row else enrich_row(row)
        first_index.setdefault(uuid, index)
        previous = best_by_uuid.get(uuid)
        if previous is None:
            best_by_uuid[uuid] = enriched
            continue
        if _quality_score(enriched) > _quality_score(previous):
            best_by_uuid[uuid] = enriched

    return sorted(best_by_uuid.values(), key=lambda row: first_index[str(row.get("uuid"))])


def _quality_score(row: dict) -> float:
    selection = row.get("_selection", {})
    text_length = int(selection.get("text_length") or 0)
    axes = selection.get("review_axes") or []
    digital_bonus = 0.25 if selection.get("has_digital_signal") else 0.0
    return min(text_length, 6000) / 1000 + len(axes) * 0.2 + digital_bonus


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
        frequencies = _frequency_maps(selected)
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


def _count(rows: list[dict], selector) -> dict[str, int]:
    values = Counter(selector(row) for row in rows)
    values.pop(None, None)
    return {str(key): values[key] for key in sorted(values)}


def summarize_rows(rows: list[dict]) -> dict:
    """Return count and distribution summary for enriched or raw rows."""

    enriched = [row if "_selection" in row else enrich_row(row) for row in rows]
    axis_counter: Counter = Counter()
    for row in enriched:
        axis_counter.update(row["_selection"].get("review_axes") or ["general_usability"])

    return {
        "count": len(enriched),
        "age_groups": {
            group: count
            for group in AGE_GROUP_ORDER
            if (count := sum(1 for row in enriched if row["_selection"].get("age_group") == group))
        },
        "sex": _count(enriched, lambda row: row["_selection"].get("sex")),
        "provinces": _count(enriched, lambda row: row["_selection"].get("province")),
        "occupation_groups": _count(enriched, lambda row: row["_selection"].get("occupation_group")),
        "family_types": _count(enriched, lambda row: row["_selection"].get("family_type")),
        "education_levels": _count(enriched, lambda row: row["_selection"].get("education_level")),
        "digital_signal": _count(
            enriched,
            lambda row: "yes" if row["_selection"].get("has_digital_signal") else "no",
        ),
        "review_axes": {str(key): axis_counter[key] for key in sorted(axis_counter)},
    }


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


def strip_selection(row: dict) -> dict:
    """Remove internal selection metadata before writing raw output files."""

    raw = dict(row)
    raw.pop("_selection", None)
    return raw


def collect_pool(
    source_rows: Iterable[dict],
    *,
    pool_size: int,
    start_row: int = 0,
    source_window_size: int | None = None,
    max_source_rows: int | None = None,
) -> list[dict]:
    """Collect quality source rows, enriched for downstream selection."""

    pool: list[dict] = []
    seen: set[str] = set()
    window_end = None if source_window_size is None else start_row + source_window_size
    for source_index, row in enumerate(source_rows):
        if max_source_rows is not None and source_index >= max_source_rows:
            break
        if source_index < start_row:
            continue
        if window_end is not None and source_index >= window_end:
            break
        if len(pool) >= pool_size:
            break
        uuid = str(row.get("uuid") or "")
        if not uuid or uuid in seen:
            continue
        if not is_quality_row(row):
            continue
        enriched = enrich_row(row)
        enriched["_selection"]["source_index"] = source_index
        pool.append(enriched)
        seen.add(uuid)
    return pool


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


def build_summary(
    *,
    seed: int,
    source: str,
    start_row: int,
    source_window_size: int | None,
    batch_size: int,
    pool_size: int,
    candidate_size: int,
    selected_size: int,
    pool: list[dict],
    candidates: list[dict],
    selected: list[dict],
    max_source_rows: int | None,
) -> dict:
    return {
        "source_dataset": DATASET_NAME,
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "source_method": source,
        "requested": {
            "pool_size": pool_size,
            "candidate_size": candidate_size,
            "selected_size": selected_size,
            "start_row": start_row,
            "source_window_size": source_window_size,
            "batch_size": batch_size,
            "max_source_rows": max_source_rows,
        },
        "selection_goal": "한국 서비스 전반 리뷰용 범용 persona raw panel",
        "criteria": [
            "필수 persona 텍스트와 핵심 메타데이터가 있는 row만 통과",
            "연령대 6군 평탄화 quota (각 16~17명)",
            "직업군 11군 marginal quota (사무·서비스·기능·전문직 균등 + 무직 캡)",
            "성별·지역·가족형태·학력·디지털 시그널은 rarity score로 균형",
            "접근성·가격·신뢰·개인정보·시간 절약·가족 돌봄·지역 생활·건강·복잡도·고객지원 관점 확보",
        ],
        "age_quotas": {
            "candidate": make_quotas(candidate_size, AGE_GROUP_WEIGHTS),
            "selected": make_quotas(selected_size, AGE_GROUP_WEIGHTS),
        },
        "occupation_quotas": {
            "candidate": make_quotas(candidate_size, OCCUPATION_GROUP_WEIGHTS),
            "selected": make_quotas(selected_size, OCCUPATION_GROUP_WEIGHTS),
        },
        "pool": summarize_rows(pool),
        "candidate": summarize_rows(candidates),
        "selected": summarize_rows(selected),
    }


def load_hf_rows(
    *,
    seed: int,
    shuffle_buffer_size: int = DEFAULT_SHUFFLE_BUFFER_SIZE,
    loader=None,
):
    """Load shuffled streaming rows from Hugging Face."""

    if loader is None:
        from datasets import load_dataset as loader

    dataset = loader(DATASET_NAME, split="train", streaming=True)
    if shuffle_buffer_size <= 0:
        return dataset
    return dataset.shuffle(seed=seed, buffer_size=shuffle_buffer_size)


def _dataset_rows_url(*, offset: int, length: int) -> str:
    query = urlencode(
        {
            "dataset": DATASET_NAME,
            "config": DATASET_CONFIG,
            "split": DATASET_SPLIT,
            "offset": offset,
            "length": length,
        }
    )
    return f"{DATASET_ROWS_ENDPOINT}?{query}"


def iter_dataset_server_rows(
    *,
    start_row: int,
    source_window_size: int,
    batch_size: int = DEFAULT_API_BATCH_SIZE,
    opener=urlopen,
    timeout: int = 60,
    sleeper=time.sleep,
    batch_delay_seconds: float = DEFAULT_BATCH_DELAY_SECONDS,
    retry_base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Iterable[dict]:
    """Yield rows from the Hugging Face Dataset Viewer /rows endpoint."""

    if source_window_size <= 0:
        return
    if batch_size <= 0 or batch_size > 100:
        raise ValueError("batch_size must be between 1 and 100 for the /rows API")

    fetched = 0
    while fetched < source_window_size:
        length = min(batch_size, source_window_size - fetched)
        offset = start_row + fetched
        url = _dataset_rows_url(offset=offset, length=length)
        payload = _open_json_with_retries(
            url,
            opener=opener,
            timeout=timeout,
            sleeper=sleeper,
            retry_base_delay_seconds=retry_base_delay_seconds,
            max_retries=max_retries,
        )

        rows = payload.get("rows") or []
        if not rows:
            break

        for item in rows:
            row = item.get("row")
            if row is not None:
                yield row

        fetched += len(rows)
        if len(rows) < length:
            break
        if fetched < source_window_size and batch_delay_seconds > 0:
            sleeper(batch_delay_seconds)


def _open_json_with_retries(
    url: str,
    *,
    opener,
    timeout: int,
    sleeper,
    retry_base_delay_seconds: float,
    max_retries: int,
) -> dict:
    attempts = 0
    while True:
        attempts += 1
        try:
            with opener(url, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            should_retry = exc.code in RETRYABLE_HTTP_STATUS_CODES
            if not should_retry or attempts > max_retries:
                raise
        except URLError:
            if attempts > max_retries:
                raise

        sleeper(retry_base_delay_seconds * attempts)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_outputs(
    *,
    output_dir: Path,
    pool: list[dict],
    candidates: list[dict],
    selected: list[dict],
    summary: dict,
) -> dict[str, Path]:
    """Write all generated JSON files after data was built in memory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        POOL_FILE_NAME: [strip_selection(row) for row in pool],
        CANDIDATE_FILE_NAME: [strip_selection(row) for row in candidates],
        SELECTED_FILE_NAME: [strip_selection(row) for row in selected],
        SUMMARY_FILE_NAME: summary,
    }

    temp_paths: dict[str, Path] = {}
    final_paths: dict[str, Path] = {}
    for name, payload in payloads.items():
        final_path = output_dir / name
        temp_path = final_path.with_suffix(final_path.suffix + ".tmp")
        write_json(temp_path, payload)
        temp_paths[name] = temp_path
        final_paths[name] = final_path

    for name, temp_path in temp_paths.items():
        temp_path.replace(final_paths[name])

    return final_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-size", type=int, default=10_000)
    parser.add_argument("--candidate-size", type=int, default=1_000)
    parser.add_argument("--selected-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--source", choices=["api", "datasets"], default="api")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_API_BATCH_SIZE)
    parser.add_argument("--batch-delay-seconds", type=float, default=DEFAULT_BATCH_DELAY_SECONDS)
    parser.add_argument("--retry-base-delay-seconds", type=float, default=DEFAULT_RETRY_BASE_DELAY_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--shuffle-buffer-size", type=int, default=DEFAULT_SHUFFLE_BUFFER_SIZE)
    parser.add_argument("--start-row", type=int, default=0)
    parser.add_argument("--source-window-size", type=int, default=None)
    parser.add_argument("--max-source-rows", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.source == "api":
        if args.source_window_size is None:
            raise ValueError("--source-window-size is required when --source api")
        source_rows = iter_dataset_server_rows(
            start_row=args.start_row,
            source_window_size=args.source_window_size,
            batch_size=args.batch_size,
            batch_delay_seconds=args.batch_delay_seconds,
            retry_base_delay_seconds=args.retry_base_delay_seconds,
            max_retries=args.max_retries,
        )
        selection_start_row = 0
        selection_window_size = None
    else:
        source_rows = load_hf_rows(seed=args.seed, shuffle_buffer_size=args.shuffle_buffer_size)
        selection_start_row = args.start_row
        selection_window_size = args.source_window_size

    pool, candidates, selected = build_selection_sets(
        source_rows,
        pool_size=args.pool_size,
        candidate_size=args.candidate_size,
        selected_size=args.selected_size,
        start_row=selection_start_row,
        source_window_size=selection_window_size,
        max_source_rows=args.max_source_rows,
    )
    summary = build_summary(
        seed=args.seed,
        source=args.source,
        start_row=args.start_row,
        source_window_size=args.source_window_size,
        batch_size=args.batch_size,
        pool_size=args.pool_size,
        candidate_size=args.candidate_size,
        selected_size=args.selected_size,
        pool=pool,
        candidates=candidates,
        selected=selected,
        max_source_rows=args.max_source_rows,
    )
    paths = write_outputs(
        output_dir=args.output_dir,
        pool=pool,
        candidates=candidates,
        selected=selected,
        summary=summary,
    )

    print(f"pool: {len(pool)} rows")
    print(f"candidate: {len(candidates)} rows")
    print(f"selected: {len(selected)} rows")
    for name in (POOL_FILE_NAME, CANDIDATE_FILE_NAME, SELECTED_FILE_NAME, SUMMARY_FILE_NAME):
        print(f"wrote {paths[name]}")


if __name__ == "__main__":
    main()
