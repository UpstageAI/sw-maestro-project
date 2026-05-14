from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.services.llm_client import UpstageClient, load_local_env


async def main() -> int:
    parser = argparse.ArgumentParser(description="Check Upstage/OpenAI-compatible LLM readiness.")
    parser.add_argument("--require-key", action="store_true", help="Fail when UPSTAGE_API_KEY is not configured.")
    parser.add_argument("--live", action="store_true", help="Make a real Upstage chat/completions probe.")
    args = parser.parse_args()

    load_local_env()
    client = UpstageClient()
    health = await client.health()
    result = {
        "ok": True,
        "configured": health["configured"],
        "base_url": health["base_url"],
        "model": health["model"],
        "daily_budget": health["daily_budget"],
        "calls_today": health["calls_today"],
        "live_probe": None,
    }

    if args.require_key and not client.configured:
        result["ok"] = False
        result["error"] = "UPSTAGE_API_KEY is not configured."
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2

    if args.live:
        if not client.configured:
            result["ok"] = False
            result["error"] = "Use --live only after setting UPSTAGE_API_KEY."
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 2
        probe = await client.chat_json(
            system='Return only JSON: {"ok": true}.',
            user='{"probe":"upstage_readiness_probe"}',
            purpose="upstage_readiness_probe",
            temperature=0,
            max_tokens=32,
        )
        result["live_probe"] = probe
        if not isinstance(probe, dict) or probe.get("ok") is not True:
            result["ok"] = False
            result["error"] = "Live Upstage probe did not return the expected JSON object."
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 1

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
