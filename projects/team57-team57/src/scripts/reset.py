"""Reset script — DB·Memory Store dump 삭제. 그 다음 `make seed` 실행.

Cross-platform (Windows + macOS/Linux) 동작.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    targets = [
        Path(os.getenv("DB_PATH", "data/review_ops.db")),
        Path(os.getenv("STORE_DUMP_PATH", "data/store_dump.json")),
    ]
    for p in targets:
        if p.exists():
            p.unlink()
            print(f"  removed {p}")
        else:
            print(f"  (skip) {p} 없음")
    print("\n다음: make seed")


if __name__ == "__main__":
    main()
