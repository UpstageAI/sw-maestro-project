"""Command-line harness for standalone manual QA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.graph import draw_completion_graph_mermaid, draw_order_graph_mermaid
from autocoin_ai.llm import load_llm_settings
from autocoin_ai.verification import build_verification_report


def load_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def print_summary(report: Mapping[str, Any]) -> None:
    print("autocoin-ai verification report")
    print("passed: %s" % report["passed"])
    print("scenarios: %s/%s" % (report["passed_count"], report["scenario_count"]))
    for scenario in report["scenarios"]:
        observed = scenario.get("observed", {})
        expected = scenario.get("expected", {})
        print(
            "- {name}: passed={passed}, observed={observed_status}, expected={expected_status}".format(
                name=scenario["name"],
                passed=scenario["passed"],
                observed_status=observed.get("lifecycle_status", "boundary-ok"),
                expected_status=expected.get("lifecycle_status", "boundary-ok"),
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="autocoin-ai standalone LangGraph runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("payload")
    complete_parser = subparsers.add_parser("complete")
    complete_parser.add_argument("payload")
    complete_parser.add_argument("completion")
    settings_parser = subparsers.add_parser("settings")
    settings_parser.set_defaults(settings=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--summary", action="store_true")
    verify_parser.add_argument("--output")
    visualize_parser = subparsers.add_parser("visualize")
    visualize_parser.add_argument("graph", choices=("order", "completion"))
    visualize_parser.add_argument("--output")
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    if args.command == "settings":
        print_json(load_llm_settings().__dict__)
        return
    if args.command == "verify":
        report = build_verification_report()
        if args.output:
            Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        if args.summary:
            print_summary(report)
        else:
            print_json(report)
        return
    if args.command == "visualize":
        mermaid = draw_order_graph_mermaid() if args.graph == "order" else draw_completion_graph_mermaid()
        if args.output:
            Path(args.output).write_text(mermaid, encoding="utf-8")
        else:
            print(mermaid)
        return
    app = AutocoinAgentApp()
    state = app.start(load_json(args.payload))
    if args.command == "complete":
        state = app.complete(state["run_id"], load_json(args.completion))
    print_json(state)


if __name__ == "__main__":
    main()
