from __future__ import annotations

import argparse
import json
import sys

import httpx


def _check(resp: httpx.Response, *, expected_status: int, label: str) -> None:
    if resp.status_code != expected_status:
        raise AssertionError(
            f"{label} failed: expected {expected_status}, got {resp.status_code}, body={resp.text}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify demo/mock stock mode endpoints.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--symbol", default="005930")
    parser.add_argument("--expect-mode", default="mock")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        health = httpx.get(f"{base_url}/health", timeout=10.0)
        _check(health, expected_status=200, label="/health")
        health_json = health.json()
        print(
            json.dumps(
                {
                    "health": {
                        "ok": health_json.get("ok"),
                        "data_mode": health_json.get("data_mode"),
                        "kis_auth_ready": health_json.get("kis_auth_ready"),
                        "llm_ready": health_json.get("llm_ready"),
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if health_json.get("data_mode") != args.expect_mode:
            raise AssertionError(
                f"expected data_mode={args.expect_mode}, got {health_json.get('data_mode')}"
            )

        stocks = httpx.get(f"{base_url}/api/stocks", timeout=10.0)
        _check(stocks, expected_status=200, label="/api/stocks")
        stocks_json = stocks.json()
        print(
            json.dumps(
                {
                    "stocks_count": len(stocks_json.get("stocks", [])),
                    "first_symbols": [s.get("symbol") for s in stocks_json.get("stocks", [])[:5]],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not stocks_json.get("stocks"):
            raise AssertionError("stock list is empty")

        stock = httpx.get(f"{base_url}/api/stocks/{args.symbol}", timeout=10.0)
        _check(stock, expected_status=200, label=f"/api/stocks/{args.symbol}")
        stock_json = stock.json()
        stock_payload = stock_json.get("stock", {})
        print(
            json.dumps(
                {
                    "stock": {
                        "symbol": stock_payload.get("symbol"),
                        "name": stock_payload.get("name"),
                        "price": stock_payload.get("price"),
                        "data_mode": stock_payload.get("data_mode"),
                        "data_source": stock_payload.get("data_source"),
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        missing = httpx.get(f"{base_url}/api/stocks/999999", timeout=10.0)
        _check(missing, expected_status=404, label="/api/stocks/999999")
        print("404 check passed")
        return 0
    except Exception as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
