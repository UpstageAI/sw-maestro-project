from pathlib import Path
from urllib.parse import urlparse


SUPPORTED_SOURCE_TYPES = {
    "manual",
    "upload",
    "txt",
    "md",
    "pdf",
    "csv",
    "notion",
    "github",
    "slack",
    "linear",
    "mcp",
    "web",
}

SOURCE_EXTENSIONS = {
    "manual": "md",
    "md": "md",
    "txt": "txt",
    "upload": "txt",
    "pdf": "pdf",
    "csv": "csv",
    "notion": "md",
    "github": "md",
    "slack": "md",
    "linear": "md",
    "mcp": "md",
    "web": "md",
}


def normalize_source_type(source_type: str | None, default: str = "manual") -> str:
    normalized = (source_type or default).strip().lower()
    return normalized if normalized in SUPPORTED_SOURCE_TYPES else normalized or default


def filename_from_source(title: str | None, source_type: str, source_url: str | None) -> str:
    extension = SOURCE_EXTENSIONS.get(source_type, "md")
    if title and title.strip():
        return _ensure_extension(title.strip(), extension)

    parsed = urlparse(source_url or "")
    candidate = Path(parsed.path).name
    if candidate:
        return _ensure_extension(candidate, extension)

    return f"{source_type}-source.{extension}"


def _ensure_extension(value: str, extension: str) -> str:
    clean = value.strip() or f"source.{extension}"
    if Path(clean).suffix:
        return clean
    return f"{clean}.{extension}"
