"""pii_mask node — 정규식으로 전화·이메일·계좌 마스킹 + P0-3 비한국어 필터."""

from __future__ import annotations

import re

from src.graph.trace import measure

PHONE_RE = re.compile(r"01[016789][\-. ]?\d{3,4}[\-. ]?\d{4}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ACCOUNT_RE = re.compile(r"\b\d{2,4}-\d{2,6}-\d{2,8}\b")

# P0-3: Solar Pro 2는 한국어 최적화. 영어/스팸 리뷰는 분류 품질 저하 + token 낭비.
# 알파벳 문자가 MIN_ALPHABETIC_CHARS 이상이고, 그 중 한글 음절 비율이 KO_RATIO_THRESHOLD
# 미만일 때 lang_skip 으로 노드 우회.
KO_RATIO_THRESHOLD = 0.3
MIN_ALPHABETIC_CHARS = 5

_HANGUL_RE = re.compile(r"[가-힣]")
_ALPHABETIC_RE = re.compile(r"[A-Za-z가-힣]")


def mask_pii(text: str) -> tuple[str, list[str]]:
    masks: list[str] = []
    if PHONE_RE.search(text):
        masks.append("전화번호")
        text = PHONE_RE.sub("[전화번호]", text)
    if EMAIL_RE.search(text):
        masks.append("이메일")
        text = EMAIL_RE.sub("[이메일]", text)
    if ACCOUNT_RE.search(text):
        masks.append("계좌")
        text = ACCOUNT_RE.sub("[계좌]", text)
    return text, masks


def _korean_ratio(text: str) -> tuple[float, int]:
    """(한글 음절 비율, 전체 알파벳 문자 수). 알파벳이 0이면 비율 0.0."""
    ko = len(_HANGUL_RE.findall(text))
    total = len(_ALPHABETIC_RE.findall(text))
    if total == 0:
        return 0.0, 0
    return ko / total, total


def pii_mask_node(state: dict) -> dict:
    with measure("pii_mask", "transform") as log:
        masked, masks = mask_pii(state["raw_text"])
        ratio, alpha_count = _korean_ratio(masked)

        # 비한국어 판정: 알파벳 충분 + 한글 비율 낮음 → graph skip
        lang_skip = (
            alpha_count >= MIN_ALPHABETIC_CHARS and ratio < KO_RATIO_THRESHOLD
        )
        lang_skip_reason = (
            f"non-Korean (ko_ratio={ratio:.2f})" if lang_skip else ""
        )

        summary_parts: list[str] = []
        summary_parts.append(
            f"마스킹 {len(masks)}건: {', '.join(masks)}" if masks else "마스킹 없음"
        )
        if lang_skip:
            summary_parts.append(
                f"비한국어 — graph skip (한국어 비율 {ratio:.2f})"
            )
        log["summary"] = " · ".join(summary_parts)
        log["details"] = {
            "masks_applied": masks,
            "input_length": len(state["raw_text"]),
            "output_length": len(masked),
            "ko_ratio": round(ratio, 3),
            "alphabetic_chars": alpha_count,
            "lang_skip": lang_skip,
        }
    return {
        "masked_text": masked,
        "lang_skip": lang_skip,
        "lang_skip_reason": lang_skip_reason,
        "node_log": [log],
    }
