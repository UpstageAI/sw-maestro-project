"""LangGraph Memory Store wrapper — multi-tenant namespace + JSON dump persistence.

Namespace: (place_id, kind) where kind ∈ {"metadata", "tone_samples", "feedback"}.
Persistence: InMemoryStore + manual JSON dump on demand.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langgraph.store.memory import InMemoryStore

load_dotenv()

DUMP_PATH = Path(os.getenv("STORE_DUMP_PATH", "data/store_dump.json"))


# --- Singleton store ---------------------------------------------------------

_store: InMemoryStore | None = None


def get_store() -> InMemoryStore:
    """Get the process-wide store. Loads JSON dump on first access if it exists."""
    global _store
    if _store is None:
        _store = InMemoryStore()
        if DUMP_PATH.exists():
            _load_dump_into(_store)
    return _store


def _load_dump_into(store: InMemoryStore) -> None:
    """Restore from JSON dump."""
    data = json.loads(DUMP_PATH.read_text(encoding="utf-8"))
    for entry in data:
        ns = tuple(entry["namespace"])
        store.put(ns, key=entry["key"], value=entry["value"])


def save_dump() -> None:
    """Serialize all entries to JSON. Called at end of seed and after each write."""
    store = get_store()
    out: list[dict] = []
    # search across the entire store by querying each known top-level place_id
    # InMemoryStore lacks a "list all" — we walk via search with single-element
    # namespace prefix. For demo simplicity we iterate via list_namespaces.
    namespaces = store.list_namespaces()
    for ns in namespaces:
        items = store.search(ns)
        for item in items:
            out.append(
                {
                    "namespace": list(ns),
                    "key": item.key,
                    "value": item.value,
                }
            )
    DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    DUMP_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# --- Seed --------------------------------------------------------------------

def seed_from_json(places: list[dict]) -> None:
    """Seed places loaded from data/seed_places.json."""
    store = get_store()
    for p in places:
        place_id = p["place_id"]
        store.put((place_id, "metadata"), key="profile", value=p["metadata"])
        for sample in p.get("tone_samples", []):
            sid = f"sm_{uuid.uuid4().hex[:10]}"
            store.put((place_id, "tone_samples"), key=sid, value=sample)
        for fb in p.get("feedback", []):
            fid = f"fb_{uuid.uuid4().hex[:10]}"
            store.put((place_id, "feedback"), key=fid, value=fb)


# --- Read --------------------------------------------------------------------

def get_metadata(place_id: str) -> dict:
    items = get_store().search((place_id, "metadata"))
    return items[0].value if items else {}


def get_tone_samples(place_id: str, limit: int = 3) -> list[dict]:
    items = get_store().search((place_id, "tone_samples"), limit=limit)
    return [it.value for it in items]


def get_feedback_hints(place_id: str, limit: int = 5) -> list[str]:
    """톤 힌트 텍스트만 반환 — 최신 순.

    Wave 3+: 기본 limit 을 5 로 상향 (구 기본 1). 메타까지 필요하면
    list_feedback_with_meta 를 사용.
    """
    entries = list_feedback_with_meta(place_id, limit=limit)
    return [e["diff_hint"] for e in entries if e.get("diff_hint")]


def list_feedback_with_meta(place_id: str, limit: int = 20) -> list[dict]:
    """전체 힌트를 메타와 함께 반환. 최신 순 (created_at desc, fallback fid desc).

    Returns list of dict with keys:
        fid, diff_hint, source, merged_from, based_on_sample_ids, created_at, updated_at.
    """
    items = get_store().search((place_id, "feedback"))
    out: list[dict] = []
    for it in items:
        v = it.value or {}
        out.append(
            {
                "fid": it.key,
                "diff_hint": v.get("diff_hint", ""),
                "source": v.get("source", "auto_diff"),
                "merged_from": v.get("merged_from", []) or [],
                "based_on_sample_ids": v.get("based_on_sample_ids", []) or [],
                "created_at": v.get("created_at", ""),
                "updated_at": v.get("updated_at", v.get("created_at", "")),
                "dimension": v.get("dimension"),
            }
        )
    # 최신 순 정렬: created_at desc (빈 문자열은 가장 오래된 것으로 취급).
    # tie-breaker 로 fid 역순 사용.
    out.sort(key=lambda e: (e.get("created_at") or "", e.get("fid") or ""), reverse=True)
    return out[:limit]


def list_place_ids() -> list[str]:
    """metadata namespace를 가진 모든 place_id."""
    seen: set[str] = set()
    for ns in get_store().list_namespaces():
        if len(ns) == 2 and ns[1] == "metadata":
            seen.add(ns[0])
    return sorted(seen)


# --- Write -------------------------------------------------------------------

def append_tone_sample(place_id: str, sample: dict) -> str:
    """사장이 답글 [복사]/[수정 저장] 했을 때 호출."""
    sid = f"sm_{uuid.uuid4().hex[:10]}"
    get_store().put((place_id, "tone_samples"), key=sid, value=sample)
    save_dump()
    return sid


def append_feedback(
    place_id: str,
    diff_hint: str,
    source_sample_ids: list[str],
    *,
    source: str = "auto_diff",
    merged_from: list[str] | None = None,
    dimension: str | None = None,
) -> str:
    """톤 힌트 신규 저장. source / merged_from / dimension / created_at / updated_at 메타 포함.

    source:
      - auto_diff: 답글 수정 후 Solar diff 요약으로 자동 생성
      - manual: 사장이 사이드바 UI 에서 직접 입력
      - merged: dedup 과정에서 기존 힌트와 통합되며 신규 생성

    dimension: 사과표현 / 감사표현 / 어투/톤 / 길이 / 이모티콘 / 구체성 / 기타.
      legacy entry 호환을 위해 None 허용.
    """
    fid = f"fb_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    get_store().put(
        (place_id, "feedback"),
        key=fid,
        value={
            "diff_hint": diff_hint,
            "based_on_sample_ids": source_sample_ids,
            "source": source,
            "merged_from": merged_from or [],
            "created_at": now,
            "updated_at": now,
            "dimension": dimension,
        },
    )
    save_dump()
    return fid


def update_feedback(
    place_id: str,
    fid: str,
    new_hint: str,
    *,
    new_dimension: str | None = None,
) -> bool:
    """기존 fid 의 diff_hint 텍스트(+선택적으로 dimension) 갱신. 성공 시 True.

    new_dimension 이 None 이면 기존 dimension 보존, 값이 있으면 덮어씀.
    """
    store = get_store()
    item = store.get((place_id, "feedback"), key=fid)
    if item is None:
        return False
    value = dict(item.value or {})
    value["diff_hint"] = new_hint
    value["updated_at"] = datetime.now(timezone.utc).isoformat()
    # created_at 보존 — 없으면 빈 문자열 유지
    value.setdefault("created_at", value["updated_at"])
    value.setdefault("source", "auto_diff")
    value.setdefault("merged_from", [])
    value.setdefault("based_on_sample_ids", [])
    value.setdefault("dimension", None)
    if new_dimension is not None:
        value["dimension"] = new_dimension
    store.put((place_id, "feedback"), key=fid, value=value)
    save_dump()
    return True


def delete_feedback(place_id: str, fid: str) -> bool:
    """힌트 1건 삭제. 성공 시 True. 없으면 False (raise 하지 않음).

    InMemoryStore.delete(namespace, key) 가 native 로 존재 — 그대로 사용.
    """
    store = get_store()
    item = store.get((place_id, "feedback"), key=fid)
    if item is None:
        return False
    store.delete((place_id, "feedback"), key=fid)
    save_dump()
    return True


def upsert_metadata(place_id: str, metadata: dict) -> None:
    get_store().put((place_id, "metadata"), key="profile", value=metadata)
    save_dump()


# --- Utility -----------------------------------------------------------------

def reset() -> None:
    """Wipe in-memory store and dump file."""
    global _store
    _store = None
    if DUMP_PATH.exists():
        DUMP_PATH.unlink()


def _stringify(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
