from __future__ import annotations

from pathlib import Path

from autocoin_ai.cli import main
from autocoin_ai.graph import draw_completion_graph_mermaid, draw_order_graph_mermaid


def test_order_graph_mermaid_contains_expected_nodes():
    mermaid = draw_order_graph_mermaid()

    assert "graph TD;" in mermaid
    assert "policy(policy)" in mermaid
    assert "risk(risk)" in mermaid
    assert "evaluator(evaluator)" in mermaid


def test_completion_graph_mermaid_contains_expected_nodes():
    mermaid = draw_completion_graph_mermaid()

    assert "graph TD;" in mermaid
    assert "execution(execution)" in mermaid


def test_visualize_command_writes_mermaid_file(monkeypatch, tmp_path: Path, capsys):
    output_path = tmp_path / "order-graph.mmd"
    monkeypatch.setattr(
        "sys.argv",
        ["autocoin-ai", "visualize", "order", "--output", str(output_path)],
    )

    main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert output_path.exists() is True
    assert "policy(policy)" in output_path.read_text(encoding="utf-8")
