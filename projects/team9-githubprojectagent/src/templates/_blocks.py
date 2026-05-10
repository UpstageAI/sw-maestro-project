"""마크다운 → Notion blocks 변환. 라인 기반 단순 컨버터."""
import re


# 인라인 마크다운: **bold**, *italic*, `code`. Notion rich_text annotations로 분할.
_INLINE_RE = re.compile(r"(\*\*([^*\n]+)\*\*|\*([^*\n]+)\*|`([^`\n]+)`)")


def _rt(text: str) -> list[dict]:
    """인라인 마크다운을 Notion rich_text 배열로. **bold**/*italic*/`code` 처리."""
    parts: list[dict] = []
    last = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > last:
            parts.append({"type": "text", "text": {"content": text[last:m.start()]}})
        if m.group(2):  # **bold**
            parts.append({
                "type": "text",
                "text": {"content": m.group(2)},
                "annotations": {"bold": True},
            })
        elif m.group(3):  # *italic*
            parts.append({
                "type": "text",
                "text": {"content": m.group(3)},
                "annotations": {"italic": True},
            })
        elif m.group(4):  # `code`
            parts.append({
                "type": "text",
                "text": {"content": m.group(4)},
                "annotations": {"code": True},
            })
        last = m.end()
    if last < len(text):
        parts.append({"type": "text", "text": {"content": text[last:]}})
    # 빈 콘텐츠 제거 — Notion API 거부 가능
    parts = [p for p in parts if p["text"]["content"]]
    return parts or [{"type": "text", "text": {"content": text or ""}}]


def para(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt(text)}}


def heading(level: int, text: str) -> dict:
    key = f"heading_{min(max(level, 1), 3)}"
    return {"object": "block", "type": key, key: {"rich_text": _rt(text)}}


def bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _rt(text)}}


def code(text: str, lang: str = "plain text") -> dict:
    # Notion 허용 언어 목록은 제한적. 'mermaid' 허용됨 (2024+).
    return {"object": "block", "type": "code",
            "code": {"rich_text": _rt(text), "language": lang}}


def divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def quote(text: str) -> dict:
    return {"object": "block", "type": "quote",
            "quote": {"rich_text": _rt(text)}}


def callout(emoji: str, text: str) -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": _rt(text),
            "icon": {"type": "emoji", "emoji": emoji},
        },
    }


def toggle(text: str, children: list[dict]) -> dict:
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {"rich_text": _rt(text), "children": children},
    }


def table_row(cells: list[str]) -> dict:
    return {
        "object": "block",
        "type": "table_row",
        "table_row": {"cells": [_rt(c) for c in cells]},
    }


def table(rows: list[list[str]], has_header: bool = True) -> dict:
    width = max((len(r) for r in rows), default=1)
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": has_header,
            "has_row_header": False,
            "children": [table_row(r + [""] * (width - len(r))) for r in rows],
        },
    }


HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)")


def md_to_blocks(md: str) -> list[dict]:
    """heading / bullet / code / paragraph / hr 만 지원하는 단순 컨버터."""
    blocks: list[dict] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip() or "plain text"
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            blocks.append(code("\n".join(buf), lang))
            i = j + 1
            continue
        m = HEADING_RE.match(line)
        if m:
            blocks.append(heading(len(m.group(1)), m.group(2).strip()))
            i += 1
            continue
        m = BULLET_RE.match(line)
        if m:
            blocks.append(bullet(m.group(1).strip()))
            i += 1
            continue
        if re.match(r"^---+\s*$", line):
            blocks.append(divider())
            i += 1
            continue
        if line.strip():
            blocks.append(para(line.strip()))
        i += 1
    return blocks
