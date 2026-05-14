import os
from pathlib import Path
from typing import Iterable


class MissingEnvironmentError(RuntimeError):
    pass


def load_environment(
    *,
    root_dir: Path | None = None,
    ai_dir: Path | None = None,
) -> None:
    root, ai = _resolve_env_dirs(root_dir=root_dir, ai_dir=ai_dir)
    for path in (root / ".env", ai / ".env"):
        _load_env_file(path)


def require_environment(
    keys: Iterable[str],
    *,
    root_dir: Path | None = None,
    ai_dir: Path | None = None,
) -> dict[str, str]:
    load_environment(root_dir=root_dir, ai_dir=ai_dir)
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        raise MissingEnvironmentError("AI 설정을 읽지 못해 재수집을 완료하지 못했어요.")
    return {key: os.environ[key] for key in keys}


def require_refresh_environment() -> None:
    require_environment(("DATABASE_URL", "UPSTAGE_API_KEY"))


def _resolve_env_dirs(
    *,
    root_dir: Path | None,
    ai_dir: Path | None,
) -> tuple[Path, Path]:
    if root_dir is not None and ai_dir is not None:
        return root_dir, ai_dir

    package_file = Path(__file__).resolve()
    inferred_ai_dir = package_file.parents[2]
    inferred_root_dir = inferred_ai_dir.parent
    return root_dir or inferred_root_dir, ai_dir or inferred_ai_dir


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        if key not in os.environ:
            os.environ[key] = value


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[7:].lstrip()
    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    if not key:
        return None

    return key, _parse_env_value(value.strip())


def _parse_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]

    marker = value.find(" #")
    if marker >= 0:
        value = value[:marker].rstrip()
    return value
