"""API 응답시간 성능 테스트 — SLA 기준값 검증."""
import time
import statistics
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.main import app
from src.services.session_manager import manager

client = TestClient(app)

# ──────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────

def measure_response_time(fn, iterations: int = 20) -> dict:
    """함수를 N회 실행하고 응답시간 통계를 반환."""
    times = []
    # 첫 번째 호출은 워밍업 (Python 캐싱 등)
    fn()
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # ms 단위

    return {
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "avg_ms": round(statistics.mean(times), 2),
        "median_ms": round(statistics.median(times), 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2),
        "iterations": iterations,
    }


# ──────────────────────────────────────────────
# SLA 기준값 (플랜 § 7.1)
# ──────────────────────────────────────────────

SLA = {
    "health": 50,        # p95 < 50ms
    "create_session": 200,  # p95 < 200ms
    "poll_session": 100,    # p95 < 100ms
    "abort_session": 100,   # p95 < 100ms
}


class TestHealthEndpointPerformance:
    def test_health_p95_under_50ms(self):
        stats = measure_response_time(lambda: client.get("/health"), iterations=30)
        print(f"\n  /health: avg={stats['avg_ms']}ms p95={stats['p95_ms']}ms")
        assert stats["p95_ms"] < SLA["health"], (
            f"SLA 위반: p95={stats['p95_ms']}ms > {SLA['health']}ms"
        )

    def test_health_always_returns_200(self):
        for _ in range(10):
            assert client.get("/health").status_code == 200


class TestCreateSessionPerformance:
    def test_create_session_p95_under_200ms(self):
        with patch("src.services.orchestrator.start_session"):
            stats = measure_response_time(
                lambda: client.post("/api/session", json={"repo_url": "https://github.com/a/b"}),
                iterations=20,
            )
        print(f"\n  POST /api/session: avg={stats['avg_ms']}ms p95={stats['p95_ms']}ms")
        assert stats["p95_ms"] < SLA["create_session"], (
            f"SLA 위반: p95={stats['p95_ms']}ms > {SLA['create_session']}ms"
        )


class TestPollSessionPerformance:
    def test_poll_session_p95_under_100ms(self):
        with patch("src.services.orchestrator.start_session"):
            sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]

        stats = measure_response_time(
            lambda: client.get(f"/api/session/{sid}"),
            iterations=50,
        )
        print(f"\n  GET /api/session/{{sid}}: avg={stats['avg_ms']}ms p95={stats['p95_ms']}ms")
        assert stats["p95_ms"] < SLA["poll_session"], (
            f"SLA 위반: p95={stats['p95_ms']}ms > {SLA['poll_session']}ms"
        )

    def test_poll_nonexistent_session_p95_under_100ms(self):
        stats = measure_response_time(
            lambda: client.get("/api/session/nonexistent999"),
            iterations=20,
        )
        print(f"\n  GET /api/session/nonexistent: avg={stats['avg_ms']}ms p95={stats['p95_ms']}ms")
        assert stats["p95_ms"] < SLA["poll_session"], (
            f"SLA 위반: p95={stats['p95_ms']}ms > {SLA['poll_session']}ms"
        )


class TestAbortSessionPerformance:
    def test_abort_session_p95_under_100ms(self):
        sids = []
        with patch("src.services.orchestrator.start_session"):
            for _ in range(20):
                sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
                sids.append(sid)

        times = []
        for sid in sids:
            start = time.perf_counter()
            client.post(f"/api/session/{sid}/abort")
            times.append((time.perf_counter() - start) * 1000)

        p95 = sorted(times)[int(len(times) * 0.95)]
        print(f"\n  POST /api/session/{{sid}}/abort: avg={statistics.mean(times):.2f}ms p95={p95:.2f}ms")
        assert p95 < SLA["abort_session"], f"SLA 위반: p95={p95:.2f}ms > {SLA['abort_session']}ms"


class TestConcurrentPolling:
    def test_10_concurrent_sessions_stable(self):
        """동시 10개 세션 폴링 — 응답시간 저하 없는지 확인."""
        import threading

        sids = []
        with patch("src.services.orchestrator.start_session"):
            for _ in range(10):
                sid = client.post("/api/session", json={"repo_url": "https://github.com/a/b"}).json()["session_id"]
                sids.append(sid)

        errors = []
        times_all = []

        def poll_session(sid):
            local_times = []
            for _ in range(5):
                start = time.perf_counter()
                res = client.get(f"/api/session/{sid}")
                local_times.append((time.perf_counter() - start) * 1000)
                if res.status_code != 200:
                    errors.append(f"sid={sid} 상태코드={res.status_code}")
            times_all.extend(local_times)

        threads = [threading.Thread(target=poll_session, args=(sid,)) for sid in sids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"에러 발생: {errors}"
        p95 = sorted(times_all)[int(len(times_all) * 0.95)]
        print(f"\n  동시 10세션 폴링: avg={statistics.mean(times_all):.2f}ms p95={p95:.2f}ms")
        # 동시 부하에서도 200ms 이내
        assert p95 < 200, f"동시 부하 SLA 위반: p95={p95:.2f}ms > 200ms"


class TestCostTrackerPerformance:
    def test_cost_tracker_record_is_fast(self):
        """CostTracker.record()가 빠른지 확인 — 동기 LLM 직렬화에 병목 없어야 함."""
        from src.tools.cost_tracker import CostTracker
        ct = CostTracker()

        start = time.perf_counter()
        for _ in range(10_000):
            ct.record("solar-pro3:low", 100, 50)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\n  CostTracker.record() x10000: {elapsed_ms:.1f}ms")
        assert elapsed_ms < 500, f"CostTracker 병목: {elapsed_ms:.1f}ms > 500ms"
