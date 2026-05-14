"""Mock LLM provider — 오프라인 데모/CI fallback.

`UPSTAGE_API_KEY` 가 없거나 `REVIEW_OPS_LLM=mock` 일 때 `upstage.py` 가 이 모듈로
모든 LLM 호출을 라우팅한다. 결정론적(키워드 매칭) 더미 응답으로 LangGraph 그래프
전체가 네트워크 없이 통과하도록 보장하는 안전망.

설계 원칙:
- `random` 사용 금지 — 같은 입력이면 항상 같은 출력
- 모든 텍스트 응답은 `[MOCK]` 으로 시작 → trace/UI 에서 즉시 식별 가능
- meta dict 키는 `upstage._extract_meta` 와 1:1 호환 (input_tokens=0 등)
"""

from __future__ import annotations

import os
import re

DEFAULT_MODEL = os.getenv("UPSTAGE_DEFAULT_MODEL", "solar-pro2")
PREVIEW_MAX = 200


# --- 키워드 사전 (classifier 결정론 기반) ----------------------------------------

_NEG_KEYWORDS = (
    "대기", "줄", "비싸", "위생", "불편", "별로", "차갑", "누락", "짜", "식어",
    "지저분",
)
_POS_KEYWORDS = ("맛있", "좋", "친절", "깔끔", "최고", "훌륭")
_RISK_KEYWORDS = ("욕설", "씨발", "병신", "고소", "소송")

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "대기시간": ("대기", "줄", "기다"),
    "가격": ("비싸", "가성비", "가격"),
    "위생": ("위생", "지저분", "더럽"),
    "서비스": ("차갑", "친절", "응대", "불친절"),
    "맛": ("맛있", "맛", "짜", "식어", "달", "싱겁"),
}


# --- helpers ------------------------------------------------------------------


def _truncate(s: str, n: int = PREVIEW_MAX) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "…"


def _build_meta(*, system: str, prompt: str, response_text: str, model: str) -> dict:
    """upstage._extract_meta 와 동일한 키 — duration=1ms 표기."""
    return {
        "model": model,
        "duration_ms": 1,
        "duration_api_ms": 1,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_create_tokens": 0,
        "system_preview": _truncate(system),
        "prompt_preview": _truncate(prompt),
        "response_preview": _truncate(response_text),
    }


# --- classifier 결정론 ---------------------------------------------------------


def _detect_categories(text: str) -> list[dict]:
    """카테고리별 키워드 히트 수 → 상위 2개 반환."""
    hits: list[tuple[str, int]] = []
    for cat, kws in _CATEGORY_KEYWORDS.items():
        count = sum(kw in text for kw in kws)
        if count > 0:
            hits.append((cat, count))
    hits.sort(key=lambda x: x[1], reverse=True)
    top = hits[:2]
    if not top:
        return []
    confidences = [0.8, 0.7]
    return [
        {"category": cat, "confidence": confidences[i]}
        for i, (cat, _) in enumerate(top)
    ]


def _mock_classify(text: str) -> dict:
    """키워드 매칭으로 sentiment/categories/confidence/risk_flag 결정."""
    has_neg = any(kw in text for kw in _NEG_KEYWORDS)
    has_pos = any(kw in text for kw in _POS_KEYWORDS)
    has_risk = any(kw in text for kw in _RISK_KEYWORDS)

    if has_pos and has_neg:
        # 데모 포인트: 양쪽 키워드 공존 시 저신뢰도 → apology_lowconf 분기 유도
        sentiment = "negative"
        confidence = 0.55
    elif has_neg:
        sentiment = "negative"
        confidence = 0.85
    elif has_pos:
        sentiment = "positive"
        confidence = 0.90
    else:
        sentiment = "neutral"
        confidence = 0.60

    categories = _detect_categories(text)

    return {
        "sentiment": sentiment,
        "categories": categories,
        "confidence": confidence,
        "risk_flag": has_risk,
        "risk_reason": "안전 위험 표현 감지 (mock)" if has_risk else None,
    }


# --- pattern.llm_summarize 결정론 ---------------------------------------------


def _mock_summarize_pattern(prompt: str) -> str:
    """pattern.llm_summarize 가 받는 (이전 메시지 누적 + tool 결과) 응답.

    실제로는 _MockChatLLM 에서 처리하지만, complete_text_with_meta 경로에서도
    드물게 호출될 수 있어 안전한 fallback 제공.
    """
    return (
        "[MOCK] 1. 대기시간 (3회)\n"
        "2. 가격 (2회)\n"
        "3. 위생 (1회)"
    )


# --- drafter / generic 텍스트 응답 --------------------------------------------


def _detect_drafter_kind(system: str) -> str:
    """drafter system prompt 에서 어느 종류인지 추정."""
    s = system or ""
    if "긍정" in s and "감사 답글" in s:
        return "thanks"
    if "보수적인" in s or "단정적 사과는 회피" in s:
        return "apology_lowconf"
    if "사과 답글" in s and "3단 구조" in s:
        return "apology"
    if "중립" in s:
        return "neutral"
    return "generic"


_DRAFTER_TEMPLATES = {
    "thanks": (
        "[MOCK 답글] 소중한 칭찬 감사드립니다. 만족스러우셨다니 정말 기쁘고, "
        "앞으로도 같은 정성으로 준비하겠습니다. 다음에도 편하게 들러주세요. "
        "(mock thanks 답글 — 실제 LLM 응답 아님)"
    ),
    "apology": (
        "[MOCK 답글] 불편을 드려 진심으로 죄송합니다. 말씀해주신 부분을 매장에서 "
        "다시 점검하고 개선하겠습니다. 다음 방문 때는 더 나은 경험을 드리도록 "
        "노력하겠습니다. (mock apology 답글 — 실제 LLM 응답 아님)"
    ),
    "apology_lowconf": (
        "[MOCK 답글] 의견 남겨주셔서 감사합니다. 혹시 어떤 부분이 불편하셨는지 "
        "조금만 더 알려주시면 정확히 살펴 개선하겠습니다. "
        "(mock apology_lowconf 답글 — 실제 LLM 응답 아님)"
    ),
    "neutral": (
        "[MOCK 답글] 방문해주시고 의견 남겨주셔서 감사합니다. 다음 방문 때는 더 "
        "나은 경험을 드릴 수 있도록 준비하겠습니다. "
        "(mock neutral 답글 — 실제 LLM 응답 아님)"
    ),
}


def _mock_text(system: str, prompt: str) -> str:
    """drafter / pattern.summarize / diff hint 등 모든 plain text 호출의 응답."""
    # pattern aggregator 의 summarize 호출은 system 에 "aggregator" 등 단서가 있을 수 있음
    s = (system or "").lower()
    if "aggregator" in s or "query_review_stats" in s:
        return _mock_summarize_pattern(prompt)

    kind = _detect_drafter_kind(system)
    if kind in _DRAFTER_TEMPLATES:
        # system prefix 첫 30자를 append 해 시스템 prompt 식별성 확보 (테스트용)
        sys_preview = (system or "")[:30].replace("\n", " ")
        return f"{_DRAFTER_TEMPLATES[kind]} (system prefix: {sys_preview})"

    # generic fallback — diff hint 등
    return (
        "[MOCK] 사장님 톤을 반영한 mock 텍스트 응답입니다. "
        "실제 LLM 응답이 아니므로 운영 환경에서는 UPSTAGE_API_KEY 를 설정해주세요. "
        "(generic mock text)"
    )


# --- public API: complete_text_with_meta / complete_json_with_meta ------------


def complete_text_with_meta(
    prompt: str, *, system: str, model: str | None = None
) -> tuple[str, dict]:
    use_model = model or DEFAULT_MODEL
    text = _mock_text(system, prompt)
    meta = _build_meta(system=system, prompt=prompt, response_text=text, model=use_model)
    return text, meta


_LINE_WITH_DIM_RE = re.compile(r"^\[([^\]]+)\]\s+([^:]+):\s+(.+)$")
_PREFER_OVER_RE = re.compile(r"(.+?)\s*보다\s+(.+?)\s+선호")
_PREFER_RE = re.compile(r"(.+?)\s*(?:선호|채택)\s*$")
_NEW_HINT_WITH_DIM_RE = re.compile(r"^새 힌트\s*\(([^)]+)\)\s*:\s*(.+)$")


def _parse_hint_dedup_prompt(
    prompt: str,
) -> tuple[list[tuple[str, str, str]], str, str]:
    """hint_dedup prompt 에서 (existing=[(fid, dimension, hint), ...], new_dimension, new_hint) 추출.

    프롬프트 형식 (Wave 5):
        기존 힌트들:
        [fb_xxx] 사과표현: 내용1
        [fb_yyy] 어투/톤: 내용2

        새 힌트 (사과표현): ...

    Legacy 포맷 (`[fb_xxx] 내용1` — dimension 없음) 도 호환.
    """
    existing: list[tuple[str, str, str]] = []
    new_hint = ""
    new_dim = "기타"
    for line in (prompt or "").splitlines():
        line = line.strip()
        if not line:
            continue
        # 새 힌트 (dimension) : 패턴
        m_new = _NEW_HINT_WITH_DIM_RE.match(line)
        if m_new:
            new_dim = m_new.group(1).strip()
            new_hint = m_new.group(2).strip()
            continue
        # legacy '새 힌트: ...' (dimension 없음)
        if line.startswith("새 힌트:"):
            new_hint = line[len("새 힌트:"):].strip()
            continue
        # 기존 힌트: dimension 포함 우선
        m = _LINE_WITH_DIM_RE.match(line)
        if m:
            fid = m.group(1).strip()
            dim = m.group(2).strip()
            hint = m.group(3).strip()
            existing.append((fid, dim, hint))
            continue
        # legacy `[fid] hint` (dimension 없음)
        if line.startswith("[") and "]" in line:
            try:
                fid_close = line.index("]")
                fid = line[1:fid_close]
                hint = line[fid_close + 1:].strip()
                existing.append((fid, "기타", hint))
            except ValueError:
                continue
    return existing, new_dim, new_hint


def _extract_preferred(hint: str) -> str | None:
    """힌트에서 사장이 '선호'하는 표현을 추출.

    'X 보다 Y 선호' → Y
    'Y 선호' / 'Y 채택' → Y
    매칭 안 되면 None.
    """
    m = _PREFER_OVER_RE.search(hint or "")
    if m:
        return m.group(2).strip()
    m = _PREFER_RE.search(hint or "")
    if m:
        return m.group(1).strip()
    return None


def _word_set(s: str) -> set[str]:
    """공백 분리 + 길이 1 토큰 제외."""
    return {w for w in (s or "").split() if len(w) > 1}


def _char_bigrams(s: str) -> set[str]:
    """공백 제거 후 길이 2 character bigram. 짧은 한국어 문장 유사도용."""
    s = (s or "").replace(" ", "")
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _mock_hint_dedup(prompt: str) -> dict:
    """결정론적 dedup 의사결정.

    Wave 5 우선순위:
    0. 같은 dimension 내 'X 선호' 패턴 비교 (preferred phrasing)
       - 같은 선호 → skip
       - 다른 선호 → merge (기존 fid 대상)
    1. 정중↔친근 모순 → merge
    2. substring / Jaccard / bigram 중복 → skip
    3. else → append
    """
    existing, new_dim, new_hint = _parse_hint_dedup_prompt(prompt)
    new_words = _word_set(new_hint)
    new_lc = new_hint.replace(" ", "")

    # 0) 같은 dimension + preferred phrasing 비교 (사과표현/감사표현 등 contradictions)
    if new_dim and new_dim != "기타":
        new_pref = _extract_preferred(new_hint)
        for fid, dim, hint in existing:
            if dim != new_dim:
                continue
            old_pref = _extract_preferred(hint)
            if new_pref and old_pref:
                if old_pref == new_pref:
                    return {
                        "action": "skip",
                        "target_fid": fid,
                        "merged_text": None,
                        "reason": "동일 선호",
                    }
                # 서로 다른 선호 → 같은 dimension 내 모순
                return {
                    "action": "merge",
                    "target_fid": fid,
                    "merged_text": new_hint,
                    "reason": "선호 변경",
                }

    # 1) 모순 감지: 정중↔친근 (legacy fallback — test_dedup_merge_on_contradiction 보존)
    for fid, _dim, hint in existing:
        h = hint or ""
        if ("정중" in new_hint and "친근" in h) or ("친근" in new_hint and "정중" in h):
            return {
                "action": "merge",
                "target_fid": fid,
                "merged_text": new_hint,
                "reason": "모순",
            }

    # 2) 중복 감지: substring / word-Jaccard / char-bigram-Jaccard
    new_bg = _char_bigrams(new_hint)
    for _fid, _dim, hint in existing:
        h_lc = (hint or "").replace(" ", "")
        if not h_lc:
            continue
        if new_lc and (new_lc in h_lc or h_lc in new_lc):
            return {
                "action": "skip",
                "target_fid": None,
                "merged_text": None,
                "reason": "중복",
            }
        if _jaccard(new_words, _word_set(hint)) > 0.8:
            return {
                "action": "skip",
                "target_fid": None,
                "merged_text": None,
                "reason": "중복",
            }
        # 짧은 한국어 — char bigram Jaccard >= 0.5 면 사실상 동일 의미
        if _jaccard(new_bg, _char_bigrams(hint)) >= 0.5:
            return {
                "action": "skip",
                "target_fid": None,
                "merged_text": None,
                "reason": "중복",
            }

    # 3) 독립
    return {
        "action": "append",
        "target_fid": None,
        "merged_text": None,
        "reason": "독립",
    }


def _mock_diff_hint(prompt: str, schema: dict, model: str) -> tuple[dict, dict]:
    """AI 초안 vs 사장 최종본 토큰 diff 로 dimension/before/after/hint 추출.

    프롬프트 형식:
        AI 초안:
        ...

        사장 최종:
        ...
    """
    # AI 초안 / 사장 최종 텍스트 추출
    ai_text = ""
    owner_text = ""
    if prompt:
        # split with markers — markers 사이 본문 추출
        # 'AI 초안:' 이후 ~ '사장 최종:' 전까지 = AI, '사장 최종:' 이후 = owner
        ai_marker = prompt.find("AI 초안:")
        owner_marker = prompt.find("사장 최종:")
        if ai_marker >= 0 and owner_marker > ai_marker:
            ai_text = prompt[ai_marker + len("AI 초안:"):owner_marker].strip()
            owner_text = prompt[owner_marker + len("사장 최종:"):].strip()
        else:
            # marker 못 찾으면 전체를 양쪽에 — 결과는 빈 diff 가 되어 generic 힌트로 fallback
            ai_text = prompt
            owner_text = prompt

    def _toks(s: str) -> list[str]:
        return re.findall(r"[가-힣A-Za-z]+", s or "")

    ai_toks = _toks(ai_text)
    ow_toks = _toks(owner_text)
    ai_set = set(ai_toks)
    ow_set = set(ow_toks)
    before_candidates = [t for t in ai_toks if t not in ow_set]
    after_candidates = [t for t in ow_toks if t not in ai_set]
    before = max(before_candidates, key=len) if before_candidates else ""
    after = max(after_candidates, key=len) if after_candidates else ""

    # dimension heuristic
    joined = (before + " " + after).lower()
    if any(k in joined for k in ("미안", "죄송", "사과")):
        dim = "사과표현"
    elif any(k in joined for k in ("감사", "고마")):
        dim = "감사표현"
    elif any(k in joined for k in ("이모", "^_^", "ㅎㅎ", "ㅠㅠ")):
        dim = "이모티콘"
    elif before or after:
        dim = "어투/톤"
    else:
        dim = "기타"

    # hint
    if before and after:
        hint = f"{before} 보다 {after} 선호"
    elif after:
        hint = f"{after} 선호"
    else:
        hint = "[MOCK] 표현 다듬음"

    result = {
        "dimension": dim,
        "before": before,
        "after": after,
        "hint": hint,
    }

    import json as _json
    response_preview = _json.dumps(result, ensure_ascii=False)
    meta = _build_meta(
        system="(diff_hint mock)",
        prompt=prompt,
        response_text=response_preview,
        model=model,
    )
    return result, meta


def complete_json_with_meta(
    prompt: str,
    *,
    system: str,
    schema: dict,
    model: str | None = None,
) -> tuple[dict, dict]:
    """schema 의 키워드로 classifier / checklist / hint_dedup 셋을 구분."""
    use_model = model or DEFAULT_MODEL
    props = (schema or {}).get("properties", {}) if isinstance(schema, dict) else {}

    # diff_hint 구조화 스키마 (dimension + before + hint) — 가장 먼저 분기
    if "dimension" in props and "hint" in props and "before" in props:
        return _mock_diff_hint(prompt, schema, use_model)

    if "sentiment" in props and "categories" in props and "risk_flag" in props:
        # classifier
        result = _mock_classify(prompt)
    elif "action" in props and "merged_text" in props:
        # hint_dedup — 톤 힌트 dedup 결정
        result = _mock_hint_dedup(prompt)
    elif "items" in props:
        # checklist_generator — TOP 3 부정 카테고리 보고 점검 To-Do
        result = {
            "items": [
                "[MOCK] 피크타임 인력 1명 추가 검토",
                "[MOCK] 매장 청결 점검 체크리스트 일일 수행",
                "[MOCK] 가격 안내 메뉴판 가시성 점검",
            ]
        }
    else:
        # 알 수 없는 schema — 빈 dict
        result = {}

    import json as _json
    response_preview = _json.dumps(result, ensure_ascii=False)
    meta = _build_meta(
        system=system, prompt=prompt, response_text=response_preview, model=use_model
    )
    return result, meta
