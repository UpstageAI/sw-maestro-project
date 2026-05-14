import re


def chunk_text(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = _planning_paragraphs(text)
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        current = ""
        for sentence in re.split(r"(?<=[.!?。！？])\s+|\n+", paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if current and len(current) + len(sentence) + 1 > max_chars:
                chunks.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            chunks.append(current)
    return chunks


def filter_reusable_chunks(chunks: list[str]) -> list[str]:
    return [chunk for chunk in chunks if len(chunk.strip()) >= 12]


def _planning_paragraphs(text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if block.strip()]
    paragraphs: list[str] = []
    heading_context: list[str] = []

    for block in blocks:
        heading = _markdown_heading(block)
        if heading:
            heading_context = [*heading_context, heading][-2:]
            continue

        paragraph = block
        if heading_context:
            paragraph = "\n".join([*heading_context, paragraph])
        paragraphs.append(paragraph)

    return paragraphs


def _markdown_heading(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) != 1:
        return ""
    match = re.match(r"^#{1,6}\s+(.+)$", lines[0])
    return match.group(1).strip() if match else ""
