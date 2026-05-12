"""Document parsing + chunking for RAG ingestion.

Produces a uniform list of chunk dicts:
    {text: str, file_name: str, heading: str, page: int | None}

Chunking targets:
  - 200~1500 chars per chunk
  - Markdown is split by header (#/##/###) using LangChain's MarkdownHeaderTextSplitter
    so the heading metadata is preserved as the section that owns the chunk.
  - PDF is split by page first, then any page over ~1500 chars is split into
    overlapping windows so we don't lose context at boundaries.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

log = logging.getLogger(__name__)

_MIN_CHARS = 200
_MAX_CHARS = 1500
_OVERLAP = 150


# ---------- generic helpers ----------

_HTML_TAG_RE = re.compile(r"<[^<>]+>")
_INLINE_WS_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_HTML_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&nbsp;": " ",
}


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities so embeddings see clean prose.

    Tech-interview repos heavily use <details>/<summary> for collapsible Q&A
    blocks. Without stripping, those tags pollute every chunk's text — bad
    for embedding similarity AND for the citation card the user sees.
    """
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    for entity, char in _HTML_ENTITIES.items():
        text = text.replace(entity, char)
    text = _INLINE_WS_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()

def _split_long_text(text: str, max_chars: int = _MAX_CHARS, overlap: int = _OVERLAP) -> list[str]:
    """Window a long string into max_chars-size chunks with overlap.
    Used for very long PDF pages or markdown sections that fall under one heading.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    chunks: list[str] = []
    step = max_chars - overlap
    i = 0
    while i < len(text):
        piece = text[i : i + max_chars].strip()
        if piece:
            chunks.append(piece)
        i += step
    return chunks


def _accumulate_short(pieces: list[str], min_chars: int = _MIN_CHARS) -> list[str]:
    """Merge sequential pieces shorter than min_chars into the next/prev so we don't
    flood Chroma with tiny <50 char headings."""
    out: list[str] = []
    buffer = ""
    for p in pieces:
        if len(buffer) + len(p) + 2 <= _MAX_CHARS:
            buffer = (buffer + "\n\n" + p).strip() if buffer else p
        else:
            if buffer:
                out.append(buffer)
            buffer = p
        if len(buffer) >= min_chars:
            out.append(buffer)
            buffer = ""
    if buffer:
        # Append leftover even if shorter than min_chars — better than dropping.
        if out and len(buffer) < min_chars:
            out[-1] = (out[-1] + "\n\n" + buffer).strip()
        else:
            out.append(buffer)
    return out


# ---------- markdown ----------

def parse_md(content: str, file_name: str) -> list[dict]:
    """Split markdown by # / ## / ### headings.

    Falls back to plain windowing when langchain-text-splitters isn't available
    or when there are no headings.
    """
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter
    except Exception as e:  # pragma: no cover
        log.warning("MarkdownHeaderTextSplitter unavailable (%s); falling back", e)
        return _md_fallback(content, file_name)

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    try:
        docs = splitter.split_text(content)
    except Exception as e:
        log.warning("md split failed for %s (%s); falling back", file_name, e)
        return _md_fallback(content, file_name)

    chunks: list[dict] = []
    for d in docs:
        meta = getattr(d, "metadata", {}) or {}
        page_content = _strip_html(getattr(d, "page_content", "") or "")
        heading = _strip_html(
            meta.get("h3") or meta.get("h2") or meta.get("h1") or ""
        )
        if not page_content:
            continue
        for piece in _split_long_text(page_content):
            chunks.append({
                "text": piece,
                "file_name": file_name,
                "heading": heading,
                "page": None,
            })

    if not chunks:
        return _md_fallback(content, file_name)
    return chunks


def _md_fallback(content: str, file_name: str) -> list[dict]:
    pieces = _split_long_text(_strip_html(content))
    return [
        {"text": p, "file_name": file_name, "heading": "", "page": None}
        for p in pieces
    ]


# ---------- pdf ----------

def parse_pdf(file_bytes: bytes, file_name: str) -> list[dict]:
    """Extract text page-by-page, then window any over-long pages."""
    try:
        import pypdf
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"pypdf not available: {e}") from e

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        raise RuntimeError(f"PDF 파싱 실패: {e}") from e

    chunks: list[dict] = []
    for page_idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            log.warning("page %d extract failed in %s: %s", page_idx, file_name, e)
            continue
        text = text.strip()
        if not text:
            continue
        for piece in _split_long_text(text):
            chunks.append({
                "text": piece,
                "file_name": file_name,
                "heading": f"p.{page_idx + 1}",
                "page": page_idx + 1,
            })

    if not chunks:
        raise RuntimeError("PDF에서 추출된 텍스트가 없습니다 (OCR이 필요한 파일일 수 있음).")
    return chunks


# ---------- shared dispatch ----------

def parse_bytes(file_bytes: bytes, file_name: str, kind: str) -> list[dict[str, Any]]:
    """Dispatch helper used by the materials endpoint."""
    if kind == "md":
        return parse_md(file_bytes.decode("utf-8", errors="replace"), file_name)
    if kind == "pdf":
        return parse_pdf(file_bytes, file_name)
    raise ValueError(f"Unsupported kind: {kind}")
