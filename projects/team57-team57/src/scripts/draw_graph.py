"""Render graph topology to PNG/Mermaid for the demo deck.

Usage: `make graph-diagram`
Outputs:
  docs/spec/diagrams/main_graph.mmd
  docs/spec/diagrams/batch_graph.mmd
"""

from __future__ import annotations

from pathlib import Path

from src.graph.build import graph
from src.graph.build_batch import batch_graph

OUT_DIR = Path("docs/spec/diagrams")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    main_mmd = graph.get_graph().draw_mermaid()
    (OUT_DIR / "main_graph.mmd").write_text(main_mmd, encoding="utf-8")
    print(f"Wrote: {OUT_DIR / 'main_graph.mmd'}")

    batch_mmd = batch_graph.get_graph().draw_mermaid()
    (OUT_DIR / "batch_graph.mmd").write_text(batch_mmd, encoding="utf-8")
    print(f"Wrote: {OUT_DIR / 'batch_graph.mmd'}")

    print(
        "\nMermaid 코드를 GitHub README나 https://mermaid.live 에서 PNG로 export 할 수 있습니다."
    )


if __name__ == "__main__":
    main()
