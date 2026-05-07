"""Command-line harness for standalone manual QA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.llm import load_llm_settings


def load_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def print_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


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
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    if args.command == "settings":
        print_json(load_llm_settings().__dict__)
        return
    app = AutocoinAgentApp()
    state = app.start(load_json(args.payload))
    if args.command == "complete":
        state = app.complete(state["run_id"], load_json(args.completion))
    print_json(state)


if __name__ == "__main__":
    main()
