"""prompt template 로드 + system/user 메시지 조립.

system.md / user_template.md / tone_guide.md / vision_system.md를 패키지 내
텍스트 자원으로 로드. species 정규화 후 tone_guide의 §0 공통 + §1/§2/§3 중 한
섹션을 diary system 메시지에 inject. user 메시지는 모드(generate / regenerate
± feedback)에 따라 3 모드 블록 조립. vision system은 별도 분석가용으로 짧게.
"""
from importlib.resources import files
from typing import Literal

from .state import DiaryState

_PROMPT_PKG = "ai_gateway.prompts.diary_v1"

# 모듈 import 시 1회만 read (캐싱).
_SYSTEM_TMPL = files(_PROMPT_PKG).joinpath("system.md").read_text(encoding="utf-8")
_USER_TMPL = files(_PROMPT_PKG).joinpath("user_template.md").read_text(encoding="utf-8")
_TONE_GUIDE = files(_PROMPT_PKG).joinpath("tone_guide.md").read_text(encoding="utf-8")
_VISION_SYSTEM_TMPL = files(_PROMPT_PKG).joinpath("vision_system.md").read_text(encoding="utf-8")


SpeciesNorm = Literal["cat", "dog", "other"]


def normalize_species(species_text: str) -> SpeciesNorm:
    """자유 입력 species → cat/dog/other. ADR-0013 §종 이모지 매핑과 키워드 정합."""
    s = species_text.lower().strip()
    cat_kw = ("고양이", "냥이", "냥", "cat", "kitty", "kitten")
    dog_kw = ("강아지", "멍멍이", "멍멍", "댕댕이", "dog", "puppy")
    if any(k in s for k in cat_kw):
        return "cat"
    if any(k in s for k in dog_kw):
        return "dog"
    return "other"


def _split_tone_sections(text: str) -> dict[str, str]:
    """tone_guide.md를 §0/§1/§2/§3 섹션으로 split.

    헤더 패턴: '## §0', '## §1', '## §2', '## §3'.
    각 섹션은 헤더 라인 포함한 통째로 inject (헤더가 가이드 문맥에 도움).
    """
    out: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("## §0"):
            if current is not None:
                out[current] = "\n".join(buf).rstrip()
            current = "common"
            buf = [line]
        elif stripped.startswith("## §1"):
            if current is not None:
                out[current] = "\n".join(buf).rstrip()
            current = "cat"
            buf = [line]
        elif stripped.startswith("## §2"):
            if current is not None:
                out[current] = "\n".join(buf).rstrip()
            current = "dog"
            buf = [line]
        elif stripped.startswith("## §3"):
            if current is not None:
                out[current] = "\n".join(buf).rstrip()
            current = "other"
            buf = [line]
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).rstrip()
    return out


_TONE_SECTIONS = _split_tone_sections(_TONE_GUIDE)


def _split_user_modes(text: str) -> dict[str, str]:
    """user_template.md를 모드 A/B/C 섹션으로 split.

    헤더 패턴: '## 모드 A', '## 모드 B', '## 모드 C'.
    각 섹션은 헤더 다음 빈 줄부터 다음 헤더 직전까지의 본문만.
    """
    out: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## 모드 A"):
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current = "A"
            buf = []
            continue
        if line.startswith("## 모드 B"):
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current = "B"
            buf = []
            continue
        if line.startswith("## 모드 C"):
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current = "C"
            buf = []
            continue
        if current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).strip()
    return out


_USER_MODES = _split_user_modes(_USER_TMPL)


def _format_recent_diaries(recent: list[str]) -> str:
    if not recent:
        return "(없음)"
    return "\n".join(f"{i + 1}. {d}" for i, d in enumerate(recent))


def build_system_message(state: DiaryState) -> str:
    species_norm = normalize_species(state["species"])
    return (
        _SYSTEM_TMPL
        .replace("{{ tone_common }}", _TONE_SECTIONS["common"])
        .replace("{{ tone_species }}", _TONE_SECTIONS[species_norm])
        .replace("{{ species_raw }}", state["species"])
        .replace("{{ gender }}", state["gender"])
        .replace("{{ honorific }}", state["honorific"])
    )


def build_vision_system_message(state: DiaryState) -> str:
    """vision agent용 system. species/gender만 fill — 호칭·톤·키워드 책임 X."""
    return (
        _VISION_SYSTEM_TMPL
        .replace("{{ species_raw }}", state["species"])
        .replace("{{ gender }}", state["gender"])
    )


def build_user_message(state: DiaryState) -> str:
    """모드 A/B/C 중 1개 선택 후 placeholder fill."""
    if state["seq"] == 1:
        mode = "A"
    elif state.get("regen_feedback"):
        mode = "B"
    else:
        mode = "C"

    template = _USER_MODES[mode]
    filled = (
        template
        .replace("{{ vision_description }}", state.get("vision_description") or "")
        .replace("{{ keywords }}", state["keywords"])
        .replace("{{ recent_diaries_block }}", _format_recent_diaries(state["recent_diaries"]))
    )

    if mode in ("B", "C"):
        previous = state.get("previous_diary_text") or ""
        filled = filled.replace("{{ previous_diary_text }}", previous)
    if mode == "B":
        feedback = state.get("regen_feedback") or ""
        filled = filled.replace("{{ regen_feedback }}", feedback)

    return filled
