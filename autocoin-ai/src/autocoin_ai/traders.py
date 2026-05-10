"""Trader knowledge loader — parses knowledge/{trader_id}/principles.md."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"


@dataclass(frozen=True)
class Principle:
    chunk_id: str
    title: str
    content: str
    keywords: tuple[str, ...]
    preferred_action: str
    avoid_when: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class TraderMeta:
    trader_id: str
    display_name: str
    style: str
    default_persona: str
    primary_sources: tuple[str, ...]
    principles: tuple[Principle, ...]


def _backtick_value(line: str) -> str:
    after = line.split(": ", 1)[1].strip() if ": " in line else line.strip()
    return after.strip("`")


def _parse_list_values(line: str) -> tuple[str, ...]:
    after = line.split(": ", 1)[1].strip() if ": " in line else ""
    parts = [p.strip().strip("`") for p in re.split(r",\s*", after)]
    return tuple(p for p in parts if p)


def _parse_principle(title: str, body_lines: list[str]) -> Principle | None:
    chunk_id = ""
    keywords: tuple[str, ...] = ()
    preferred_action = ""
    avoid_when = ""
    source_refs: tuple[str, ...] = ()
    content_parts: list[str] = []
    in_meta = False

    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("- chunk_id:"):
            in_meta = True
            chunk_id = _backtick_value(stripped)
        elif stripped.startswith("- keywords:"):
            in_meta = True
            keywords = _parse_list_values(stripped)
        elif stripped.startswith("- preferred_action:"):
            in_meta = True
            preferred_action = stripped.split(": ", 1)[1].strip()
        elif stripped.startswith("- avoid_when:"):
            in_meta = True
            avoid_when = stripped.split(": ", 1)[1].strip()
        elif stripped.startswith("- source_refs:"):
            in_meta = True
            source_refs = _parse_list_values(stripped)
        elif not in_meta and stripped:
            content_parts.append(stripped)

    if not chunk_id:
        return None
    return Principle(
        chunk_id=chunk_id,
        title=title,
        content=" ".join(content_parts),
        keywords=keywords,
        preferred_action=preferred_action,
        avoid_when=avoid_when,
        source_refs=source_refs,
    )


def load_trader(trader_id: str) -> TraderMeta:
    path = KNOWLEDGE_DIR / trader_id / "principles.md"
    if not path.exists():
        raise ValueError("unknown trader_id: %s" % trader_id)

    text = path.read_text(encoding="utf-8")
    sections = re.split(r"\n## ", "\n" + text)

    meta_kwargs: dict[str, str] = {}
    primary_sources: list[str] = []
    principles: list[Principle] = []

    for section in sections[1:]:
        lines = section.split("\n")
        title = lines[0].strip()
        body = lines[1:]

        if title == "Metadata":
            in_sources = False
            for line in body:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("- primary_sources:"):
                    in_sources = True
                    continue
                if in_sources:
                    if stripped.startswith("- http"):
                        primary_sources.append(stripped[2:].strip())
                    elif not stripped.startswith("-"):
                        in_sources = False
                    continue
                if stripped.startswith("- trader_id:"):
                    meta_kwargs["trader_id"] = _backtick_value(stripped)
                elif stripped.startswith("- display_name:"):
                    meta_kwargs["display_name"] = _backtick_value(stripped)
                elif stripped.startswith("- style:"):
                    meta_kwargs["style"] = stripped.split(": ", 1)[1].strip()
                elif stripped.startswith("- default_persona:"):
                    meta_kwargs["default_persona"] = _backtick_value(stripped)
        else:
            p = _parse_principle(title, body)
            if p is not None:
                principles.append(p)

    return TraderMeta(
        trader_id=meta_kwargs.get("trader_id", trader_id),
        display_name=meta_kwargs.get("display_name", trader_id),
        style=meta_kwargs.get("style", ""),
        default_persona=meta_kwargs.get("default_persona", "MODERATE"),
        primary_sources=tuple(primary_sources),
        principles=tuple(principles),
    )
