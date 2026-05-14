import copy
import asyncio
import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


class DisabledLlm:
    configured = False

    async def chat_json(self, **kwargs):
        return None

    async def health(self):
        return {
            "configured": False,
            "base_url": "https://api.upstage.ai/v1",
            "model": "test-disabled",
            "daily_budget": 500,
            "calls_today": 0,
        }


class BackendContractTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from app.api.routes import get_now
        from app.main import create_app
        from app.services.cache import analyze_cache, health_cache, milestone_cache

        analyze_cache._items.clear()
        health_cache._items.clear()
        milestone_cache._items.clear()
        self.now = datetime(2026, 5, 6, 9, 0, tzinfo=timezone(timedelta(hours=9)))
        self._llm_patchers = [
            patch("app.api.routes.llm_client", DisabledLlm(), create=True),
            patch("app.agents.priority.llm_client", DisabledLlm(), create=True),
            patch("app.agents.schedule.llm_client", DisabledLlm(), create=True),
            patch("app.agents.risk.llm_client", DisabledLlm(), create=True),
        ]
        for patcher in self._llm_patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        app = create_app()
        app.dependency_overrides[get_now] = lambda: self.now
        self.client = TestClient(app)

    def _snapshot(self):
        starts_at = self.now.isoformat()
        return {
            "project": {
                "project_id": "proj_ABCDEF12",
                "name": "AI SWM 프로젝트",
                "goal": "AI 기반 프로젝트 일정 관리 MVP",
                "starts_at": "2026-05-06",
                "ends_at": "2026-06-30",
                "default_working_hours": {
                    "weekday": {"start": "09:00", "end": "18:00", "enabled": True},
                    "weekend": {"start": "10:00", "end": "16:00", "enabled": False},
                },
                "timezone": "Asia/Seoul",
            },
            "members": [
                {
                    "member_id": "mem_ALPHA1",
                    "name": "김개발",
                    "role": "Backend",
                    "weekly_capacity_hours": 40,
                    "available_hours": [],
                }
            ],
            "tasks": [
                {
                    "task_id": "task_ALPHA001",
                    "project_id": "proj_ABCDEF12",
                    "milestone_id": None,
                    "title": "FastAPI API Gateway 구현",
                    "description": "문서 계약에 맞는 API를 구현한다.",
                    "assignee_id": "mem_ALPHA1",
                    "deadline": (self.now + timedelta(days=2)).isoformat(),
                    "importance": "critical",
                    "estimated_hours": 2,
                    "status": "todo",
                    "progress_percent": 0,
                    "delay_reason": None,
                    "predecessor_ids": [],
                    "created_at": starts_at,
                    "updated_at": starts_at,
                }
            ],
            "milestones": [],
            "calendar_events": [],
        }

    def test_projects_endpoint_mints_project_id(self):
        payload = copy.deepcopy(self._snapshot()["project"])
        payload.pop("project_id")

        response = self.client.post("/v1/projects", json=payload)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertRegex(body["project_id"], r"^proj_[A-Za-z0-9]{8,}$")
        self.assertEqual(body["name"], payload["name"])

    def test_e2e_golden_fixtures_cover_all_five_scenarios(self):
        fixtures_dir = Path(__file__).parent / "fixtures" / "e2e"
        expected_files = [
            "scenario_1_happy_path.json",
            "scenario_2_unschedulable.json",
            "scenario_3_overload_unassigned.json",
            "scenario_4_circular_dependency.json",
            "scenario_5_stale_hash.json",
        ]

        for filename in expected_files:
            fixture = json.loads((fixtures_dir / filename).read_text(encoding="utf-8"))
            self.assertIn("snapshot", fixture)
            self.assertIn("expected", fixture)
            self.assertEqual(fixture["snapshot"]["project"]["project_id"], "proj_FIXTURE1")
            self.assertTrue(fixture["expected"])

    def test_e2e_golden_fixtures_match_backend_contracts(self):
        fixtures_dir = Path(__file__).parent / "fixtures" / "e2e"
        self.now = datetime(2026, 5, 11, 9, 0, tzinfo=timezone(timedelta(hours=9)))

        happy = json.loads((fixtures_dir / "scenario_1_happy_path.json").read_text(encoding="utf-8"))
        response = self.client.post("/v1/projects/proj_FIXTURE1/analyze", json={"snapshot": happy["snapshot"], "options": {}})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["priority"]["tasks_priority"]), happy["expected"]["priority_count"])
        self.assertEqual(len(body["schedule"]["slot_proposals"]), happy["expected"]["slot_proposal_count"])
        self.assertEqual(len(body["risk"]["checks"]), happy["expected"]["risk_check_count"])
        self.assertEqual(body["risk"]["blockers_failed"], happy["expected"]["blockers_failed"])

        unschedulable = json.loads((fixtures_dir / "scenario_2_unschedulable.json").read_text(encoding="utf-8"))
        response = self.client.post("/v1/projects/proj_FIXTURE1/analyze", json={"snapshot": unschedulable["snapshot"], "options": {}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["schedule"]["unschedulable"][0]["task_id"], unschedulable["expected"]["unschedulable_task_id"])
        self.assertIn(unschedulable["expected"]["unschedulable_reason"], response.json()["schedule"]["unschedulable"][0]["reasons"])

        overload = json.loads((fixtures_dir / "scenario_3_overload_unassigned.json").read_text(encoding="utf-8"))
        response = self.client.post("/v1/projects/proj_FIXTURE1/analyze", json={"snapshot": overload["snapshot"], "options": {}})
        self.assertEqual(response.status_code, 200)
        checks = {item["id"]: item["result"] for item in response.json()["risk"]["checks"]}
        self.assertEqual(checks["workload_concentration"], overload["expected"]["risk_checks"]["workload_concentration"])

        circular = json.loads((fixtures_dir / "scenario_4_circular_dependency.json").read_text(encoding="utf-8"))
        response = self.client.post("/v1/projects/proj_FIXTURE1/analyze", json={"snapshot": circular["snapshot"], "options": {}})
        self.assertEqual(response.status_code, circular["expected"]["status"])
        circular_body = response.json()
        circular_checks = {item["id"]: item["result"] for item in circular_body["risk"]["checks"]}
        self.assertEqual(circular_checks["dependency_correctness"], circular["expected"]["risk_checks"]["dependency_correctness"])
        self.assertEqual(circular_body["risk"]["blockers_failed"], circular["expected"]["blockers_failed"])
        circular_suggestion = next(
            item
            for item in circular_body["risk"]["suggestions"]
            if "dependency_correctness" in item["fixes_check_ids"]
        )
        self.assertEqual(circular_suggestion["action"], circular["expected"]["suggestion_action"])

        stale = json.loads((fixtures_dir / "scenario_5_stale_hash.json").read_text(encoding="utf-8"))
        response = self.client.post("/v1/projects/proj_FIXTURE1/analyze", json={"snapshot": stale["snapshot"], "options": {}})
        self.assertEqual(response.status_code, 200)
        stale_response = self.client.post(
            "/v1/projects/proj_FIXTURE1/schedule:approve",
            json={"snapshot_hash": "stale", "approvals": [{"task_id": "task_SMOKE001", "candidate_slot_index": 0}]},
        )
        self.assertEqual(stale_response.status_code, stale["expected"]["stale_status"])
        self.assertEqual(stale_response.json()["error"]["code"], stale["expected"]["stale_error_code"])

    def test_cors_allows_local_vite_ports(self):
        for origin in ["http://127.0.0.1:5173", "http://localhost:5173"]:
            with self.subTest(origin=origin):
                response = self.client.options(
                    "/v1/projects",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["access-control-allow-origin"], origin)

    def test_cors_rejects_unlisted_local_ports_by_default(self):
        response = self.client.options(
            "/v1/projects",
            headers={
                "Origin": "http://127.0.0.1:5174",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_cors_allows_frontend_origins_env_override(self):
        from fastapi.testclient import TestClient
        from app.main import create_app

        with patch.dict("os.environ", {"FRONTEND_ORIGINS": "http://127.0.0.1:6123, http://localhost:6123/"}):
            client = TestClient(create_app())
            response = client.options(
                "/v1/projects",
                headers={
                    "Origin": "http://localhost:6123",
                    "Access-Control-Request-Method": "POST",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:6123")

    def test_openapi_exposes_documented_api_contract_paths(self):
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for path in [
            "/v1/projects",
            "/v1/projects/{project_id}/milestones:suggest",
            "/v1/projects/{project_id}/milestones:approve",
            "/v1/projects/{project_id}/analyze",
            "/v1/projects/{project_id}/schedule:approve",
            "/v1/projects/{project_id}/risk:simulate",
            "/v1/health",
        ]:
            self.assertIn(path, paths)

    def test_rate_limit_returns_contract_error(self):
        from fastapi.testclient import TestClient
        from app.main import create_app

        with patch.dict("os.environ", {"RATE_LIMIT_PER_MIN": "2"}):
            limited_client = TestClient(create_app())
            self.assertEqual(limited_client.get("/v1/health").status_code, 200)
            self.assertEqual(limited_client.get("/v1/health").status_code, 200)
            response = limited_client.get("/v1/health")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "rate_limited")

    def test_default_rate_limit_matches_backend_spec(self):
        from fastapi.testclient import TestClient
        from app.main import create_app

        with patch.dict("os.environ", {}, clear=True):
            limited_client = TestClient(create_app())
            statuses = [limited_client.get("/v1/health").status_code for _ in range(31)]

        self.assertEqual(statuses[:30], [200] * 30)
        self.assertEqual(statuses[30], 429)

    def test_snapshot_hash_ignores_field_order_and_timestamp_microseconds(self):
        from app.schemas import ProjectSnapshot
        from app.services.hash import compute_snapshot_hash

        snapshot = self._snapshot()
        reordered = json.loads(json.dumps(snapshot, sort_keys=True))
        reordered["tasks"][0]["created_at"] = self.now.replace(microsecond=123456).isoformat()
        reordered["tasks"][0]["updated_at"] = self.now.replace(microsecond=654321).isoformat()

        self.assertEqual(
            compute_snapshot_hash(ProjectSnapshot(**snapshot)),
            compute_snapshot_hash(ProjectSnapshot(**reordered)),
        )

    def test_langsmith_env_toggle_does_not_break_analyze(self):
        from fastapi.testclient import TestClient
        from app.main import create_app

        for enabled in ("false", "true"):
            snapshot = self._snapshot()
            snapshot["project"]["project_id"] = f"proj_LANG{enabled.upper():0<4}"[:13]
            snapshot["tasks"][0]["project_id"] = snapshot["project"]["project_id"]
            with patch.dict(
                "os.environ",
                {
                    "LANGCHAIN_TRACING_V2": enabled,
                    "LANGCHAIN_API_KEY": "test-langsmith-key",
                    "LANGCHAIN_PROJECT": "ai-swm-55-test",
                },
            ):
                response = TestClient(create_app()).post(
                    f"/v1/projects/{snapshot['project']['project_id']}/analyze",
                    json={"snapshot": snapshot, "options": {}},
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["project_id"], snapshot["project"]["project_id"])

    def test_schedule_approve_and_risk_simulate_meet_backend_latency_targets(self):
        analyze = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": self._snapshot(), "options": {}},
        )
        self.assertEqual(analyze.status_code, 200)
        snapshot_hash = analyze.json()["snapshot_hash"]

        approve_start = time.perf_counter()
        approve = self.client.post(
            "/v1/projects/proj_ABCDEF12/schedule:approve",
            json={
                "snapshot_hash": snapshot_hash,
                "approvals": [{"task_id": "task_ALPHA001", "candidate_slot_index": 0}],
            },
        )
        approve_ms = (time.perf_counter() - approve_start) * 1000

        simulate_start = time.perf_counter()
        simulate = self.client.post(
            "/v1/projects/proj_ABCDEF12/risk:simulate",
            json={"snapshot": self._snapshot(), "applied_suggestion_ids": []},
        )
        simulate_ms = (time.perf_counter() - simulate_start) * 1000

        self.assertEqual(approve.status_code, 200)
        self.assertEqual(simulate.status_code, 200)
        self.assertLessEqual(approve_ms, 200)
        self.assertLessEqual(simulate_ms, 200)

    def test_api_handles_five_concurrent_analyze_requests(self):
        import httpx
        from app.main import create_app

        async def run_requests():
            transport = httpx.ASGITransport(app=create_app())
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                requests = []
                for index in range(5):
                    snapshot = copy.deepcopy(self._snapshot())
                    project_id = f"proj_CONCUR{index:02d}"
                    snapshot["project"]["project_id"] = project_id
                    snapshot["tasks"][0]["project_id"] = project_id
                    snapshot["tasks"][0]["task_id"] = f"task_CONC{index:04d}"
                    requests.append(
                        client.post(
                            f"/v1/projects/{project_id}/analyze",
                            json={"snapshot": snapshot, "options": {}},
                        )
                    )
                return await asyncio.gather(*requests)

        responses = asyncio.run(run_requests())

        self.assertEqual([response.status_code for response in responses], [200, 200, 200, 200, 200])
        self.assertEqual(
            {response.json()["project_id"] for response in responses},
            {f"proj_CONCUR{index:02d}" for index in range(5)},
        )

    def test_upstage_client_can_load_local_dotenv_file_without_overwriting_env(self):
        from app.services.llm_client import load_local_env

        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "UPSTAGE_API_KEY=from_file",
                        "UPSTAGE_MODEL='solar-test'",
                        "UPSTAGE_BASE_URL=https://example.test/v1",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"UPSTAGE_API_KEY": "already_set"}, clear=True):
                load_local_env(env_path)
                import os

                self.assertEqual(os.environ["UPSTAGE_API_KEY"], "already_set")
                self.assertEqual(os.environ["UPSTAGE_MODEL"], "solar-test")
                self.assertEqual(os.environ["UPSTAGE_BASE_URL"], "https://example.test/v1")

    def test_upstage_client_honors_daily_budget_without_network_call(self):
        import httpx
        from app.services.llm_client import UpstageClient

        def handler(_):
            raise AssertionError("budget-exhausted calls must not reach the network")

        client = UpstageClient(api_key="test-key", daily_budget=0, transport=httpx.MockTransport(handler))

        result = asyncio.run(client.chat_json(system="Return JSON", user="{}", temperature=0))

        self.assertIsNone(result)

    def test_upstage_client_retries_once_after_http_error(self):
        import httpx
        from app.services.llm_client import UpstageClient

        attempts = 0

        def handler(_):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(500, json={"error": "temporary"})
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "{\"ok\": true}"}}]},
            )

        client = UpstageClient(api_key="test-key", daily_budget=5, transport=httpx.MockTransport(handler))

        result = asyncio.run(client.chat_json(system="Return JSON", user="{}", temperature=0))

        self.assertEqual(result, {"ok": True})
        self.assertEqual(attempts, 2)

    def test_upstage_client_limits_concurrent_chat_requests(self):
        import httpx
        from app.services.llm_client import UpstageClient

        active = 0
        max_active = 0

        async def handler(_):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "{\"ok\": true}"}}]},
            )

        async def run_many():
            client = UpstageClient(
                api_key="test-key",
                daily_budget=10,
                max_concurrency=2,
                transport=httpx.MockTransport(handler),
            )
            return await asyncio.gather(
                *[client.chat_json(system="Return JSON", user="{}", temperature=0) for _ in range(5)]
            )

        results = asyncio.run(run_many())

        self.assertEqual(results, [{"ok": True}] * 5)
        self.assertLessEqual(max_active, 2)

    def test_upstage_client_sends_openai_compatible_chat_completion_request(self):
        import httpx
        from app.services.llm_client import UpstageClient

        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["authorization"] = request.headers["authorization"]
            seen["content_type"] = request.headers["content-type"]
            seen["body"] = json.loads(request.content.decode())
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "{\"ok\": true}"}}]},
            )

        client = UpstageClient(
            api_key="test-key",
            base_url="https://api.upstage.ai/v1",
            model="solar-pro3",
            daily_budget=5,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.chat_json(system="Return JSON", user="{\"hello\":\"world\"}", temperature=0.2, max_tokens=123))

        self.assertEqual(result, {"ok": True})
        self.assertEqual(seen["url"], "https://api.upstage.ai/v1/chat/completions")
        self.assertEqual(seen["authorization"], "Bearer test-key")
        self.assertEqual(seen["content_type"], "application/json")
        self.assertEqual(seen["body"]["model"], "solar-pro3")
        self.assertEqual(seen["body"]["temperature"], 0.2)
        self.assertEqual(seen["body"]["max_tokens"], 123)
        self.assertFalse(seen["body"]["stream"])
        self.assertEqual(seen["body"]["response_format"], {"type": "json_object"})
        self.assertEqual(seen["body"]["messages"][0], {"role": "system", "content": "Return JSON"})
        self.assertEqual(seen["body"]["messages"][1], {"role": "user", "content": "{\"hello\":\"world\"}"})

    def test_upstage_client_falls_back_when_json_mode_is_unsupported(self):
        import httpx
        from app.services.llm_client import UpstageClient

        bodies = []

        def handler(request):
            body = json.loads(request.content.decode())
            bodies.append(body)
            if len(bodies) == 1:
                self.assertEqual(body["response_format"], {"type": "json_object"})
                return httpx.Response(400, json={"error": {"message": "unsupported response_format"}})
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "{\"ok\": true}"}}]},
            )

        client = UpstageClient(api_key="test-key", daily_budget=5, transport=httpx.MockTransport(handler))

        result = asyncio.run(client.chat_json(system="Return JSON", user="{}"))

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(bodies), 2)
        self.assertNotIn("response_format", bodies[1])

    def test_upstage_client_records_raw_response_for_seven_day_retention(self):
        import httpx
        from app.services.llm_client import UpstageClient
        from app.services.metrics import llm_raw_response_summary, reset_llm_raw_responses

        reset_llm_raw_responses()

        def handler(_):
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "{\"ok\": true}"}}]},
            )

        client = UpstageClient(api_key="test-key", daily_budget=5, transport=httpx.MockTransport(handler))

        result = asyncio.run(client.chat_json(system="Return JSON", user="{}", purpose="risk_narrate"))

        self.assertEqual(result, {"ok": True})
        summary = llm_raw_response_summary()
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["retention_days"], 7)
        self.assertEqual(summary["by_purpose"]["risk_narrate"], 1)
        self.assertIsNotNone(summary["newest_recorded_at"])

    def test_health_exposes_llm_schema_pass_rate_metrics(self):
        from app.services.metrics import reset_llm_schema_metrics, record_llm_schema_result

        reset_llm_schema_metrics()
        record_llm_schema_result("risk_soft_checks", True)
        record_llm_schema_result("risk_soft_checks", False)

        response = self.client.get("/v1/health")

        self.assertEqual(response.status_code, 200)
        metrics = response.json()["llm_schema"]
        self.assertEqual(metrics["total"], 2)
        self.assertEqual(metrics["passed"], 1)
        self.assertEqual(metrics["pass_rate"], 0.5)

    def test_health_exposes_policy_violation_metrics(self):
        from app.services.metrics import policy_violation_summary, record_policy_violation, reset_policy_violation_metrics

        reset_policy_violation_metrics()
        record_policy_violation("forbidden_word")
        record_policy_violation("forbidden_word")
        record_policy_violation("hallucinated_task_id")

        response = self.client.get("/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["policy_violations"], policy_violation_summary())
        self.assertEqual(response.json()["policy_violations"]["total"], 3)
        self.assertEqual(response.json()["policy_violations"]["by_filter"]["forbidden_word"], 2)

    def test_health_exposes_llm_call_metrics(self):
        from app.services.metrics import llm_call_summary, record_llm_call, reset_llm_call_metrics

        reset_llm_call_metrics()
        record_llm_call("priority_narrate")
        record_llm_call("priority_narrate")
        record_llm_call("risk_soft_checks")

        response = self.client.get("/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["llm_calls"], llm_call_summary())
        self.assertEqual(response.json()["llm_calls"]["total"], 3)
        self.assertEqual(response.json()["llm_calls"]["by_purpose"]["priority_narrate"], 2)

    def test_health_caches_upstage_probe_but_keeps_dynamic_metrics_fresh(self):
        from app.services.cache import health_cache
        from app.services.metrics import record_llm_call, reset_llm_call_metrics

        class CountingHealthLlm:
            def __init__(self):
                self.calls = 0

            async def health(self):
                self.calls += 1
                return {
                    "configured": True,
                    "base_url": "https://api.upstage.ai/v1",
                    "model": "solar-pro3",
                    "daily_budget": 500,
                    "calls_today": self.calls,
                }

        fake_llm = CountingHealthLlm()
        reset_llm_call_metrics()
        health_cache._items.clear()
        with patch("app.api.routes.llm_client", fake_llm, create=True):
            first = self.client.get("/v1/health")
            record_llm_call("priority_narrate")
            second = self.client.get("/v1/health")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(fake_llm.calls, 1)
        self.assertEqual(first.json()["upstage_api"]["calls_today"], 1)
        self.assertEqual(second.json()["upstage_api"]["calls_today"], 1)
        self.assertEqual(second.json()["llm_calls"]["by_purpose"]["priority_narrate"], 1)

    def test_health_exposes_llm_raw_response_retention_metrics(self):
        from app.services.metrics import llm_raw_response_summary, record_llm_raw_response, reset_llm_raw_responses

        reset_llm_raw_responses()
        record_llm_raw_response("schedule_rerank", {"choices": [{"message": {"content": "{\"ok\": true}"}}]})

        response = self.client.get("/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["llm_raw_responses"], llm_raw_response_summary())
        self.assertEqual(response.json()["llm_raw_responses"]["total"], 1)
        self.assertEqual(response.json()["llm_raw_responses"]["retention_days"], 7)

    def test_health_exposes_llm_safety_metrics(self):
        from app.services.metrics import llm_safety_summary, record_llm_safety_result, reset_llm_safety_metrics

        reset_llm_safety_metrics()
        record_llm_safety_result("schedule_rerank", True)
        record_llm_safety_result("schedule_rerank", False, "rerank_violation:task_ALPHA001")
        record_llm_safety_result("risk_soft_checks", False, "hallucinated_task_id")

        response = self.client.get("/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["llm_safety"], llm_safety_summary())
        self.assertEqual(response.json()["llm_safety"]["total"], 3)
        self.assertEqual(response.json()["llm_safety"]["by_purpose"]["schedule_rerank"]["pass_rate"], 0.5)
        self.assertEqual(response.json()["llm_safety"]["by_purpose"]["risk_soft_checks"]["blocked_rate"], 1.0)

    def test_milestone_suggest_records_schema_failure_for_invalid_llm_payload(self):
        from app.services.cache import milestone_cache
        from app.services.metrics import llm_schema_summary, reset_llm_schema_metrics

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {"not_milestones": []}

        reset_llm_schema_metrics()
        milestone_cache._items.clear()
        with patch("app.api.routes.llm_client", FakeLlm(), create=True):
            response = self.client.post(
                "/v1/projects/proj_ABCDEF12/milestones:suggest",
                json={"snapshot": self._snapshot(), "max_milestones": 8},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["proposed_milestones"]), 5)
        self.assertEqual(llm_schema_summary()["by_purpose"]["milestone_suggest"]["failed"], 1)

    def test_milestone_suggest_setup_fallback_uses_duration_slots_and_goal(self):
        from app.services.cache import milestone_cache

        snapshot = copy.deepcopy(self._snapshot())
        snapshot["project"]["goal"] = "고객 상담 자동화 MVP"
        snapshot["project"]["starts_at"] = "2026-05-01"
        snapshot["project"]["ends_at"] = "2026-05-30"
        snapshot["tasks"] = []
        milestone_cache._items.clear()

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/milestones:suggest",
            json={"snapshot": snapshot, "max_milestones": 8},
        )

        self.assertEqual(response.status_code, 200)
        milestones = response.json()["proposed_milestones"]
        self.assertEqual(len(milestones), 4)
        self.assertEqual(milestones[-1]["due_date"], "2026-05-30")
        self.assertTrue(all(not item["name"].startswith("고객 상담 자동화 MVP") for item in milestones))
        self.assertEqual(len({item["name"] for item in milestones}), len(milestones))
        self.assertEqual(
            [item["name"] for item in milestones],
            ["요구사항 산출물 확정", "핵심 범위 설계 완료", "MVP 기능 산출물 완성", "검증 및 출시 준비"],
        )
        self.assertTrue(all("due_date" in item for item in milestones))

    def test_milestone_suggest_uses_backend_slots_and_ignores_llm_dates(self):
        from app.services.cache import milestone_cache

        class SlotLlm:
            configured = True

            def __init__(self):
                self.payload = None
                self.system = ""

            async def chat_json(self, **kwargs):
                self.payload = json.loads(kwargs["user"])
                self.system = kwargs["system"]
                return {
                    "milestones": [
                        {
                            "slot_index": 1,
                            "name": "요구사항 산출물 확정",
                            "due_date": "2099-01-01",
                            "ai_rationale": "초기 범위를 확정합니다.",
                        },
                        {
                            "slot_index": 2,
                            "name": "핵심 기능 산출물 완성",
                            "due_date": "2099-01-02",
                            "ai_rationale": "핵심 구현을 완료합니다.",
                        },
                    ]
                }

        fake_llm = SlotLlm()
        snapshot = copy.deepcopy(self._snapshot())
        snapshot["project"]["starts_at"] = "2026-05-01"
        snapshot["project"]["ends_at"] = "2026-05-14"
        snapshot["tasks"] = []
        milestone_cache._items.clear()

        with patch("app.api.routes.llm_client", fake_llm, create=True):
            response = self.client.post(
                "/v1/projects/proj_ABCDEF12/milestones:suggest",
                json={"snapshot": snapshot, "max_milestones": 8},
            )

        self.assertEqual(response.status_code, 200)
        milestones = response.json()["proposed_milestones"]
        self.assertEqual(len(milestones), 3)
        self.assertEqual(milestones[0]["name"], "요구사항 산출물 확정")
        self.assertNotEqual(milestones[0]["due_date"], "2099-01-01")
        self.assertEqual(milestones[-1]["due_date"], "2026-05-14")
        self.assertEqual(fake_llm.payload["mode"], "setup_mode")
        self.assertEqual(len(fake_llm.payload["slots"]), 3)
        self.assertIn("setup_mode", fake_llm.system)
        self.assertIn("execution_mode", fake_llm.system)
        self.assertIn("Good examples", fake_llm.system)
        self.assertIn("Bad examples", fake_llm.system)
        self.assertIn("Do not copy task titles verbatim", fake_llm.system)
        self.assertIn("Do not prefix every name with the project or product name", fake_llm.system)
        self.assertIn("Each rationale must explain why the deliverable belongs at that slot", fake_llm.system)

    def test_milestone_suggest_execution_mode_sends_task_summary_and_cache_tracks_tasks(self):
        from app.services.cache import milestone_cache

        class CountingLlm:
            configured = True

            def __init__(self):
                self.calls = 0
                self.payloads = []

            async def chat_json(self, **kwargs):
                self.calls += 1
                payload = json.loads(kwargs["user"])
                self.payloads.append(payload)
                return {
                    "milestones": [
                        {
                            "slot_index": slot["slot_index"],
                            "name": f"{slot['position']} 산출물 확정",
                            "ai_rationale": "제공된 task 맥락을 기준으로 산출물을 정리합니다.",
                        }
                        for slot in payload["slots"]
                    ]
                }

        fake_llm = CountingLlm()
        snapshot = copy.deepcopy(self._snapshot())
        second_task = copy.deepcopy(snapshot["tasks"][0])
        second_task["task_id"] = "task_BRAVO001"
        second_task["title"] = "React 대시보드 구현"
        second_task["description"] = "사용자 대시보드 화면을 구현한다."
        third_task = copy.deepcopy(snapshot["tasks"][0])
        third_task["task_id"] = "task_CHARLIE1"
        third_task["title"] = "배포 검증"
        third_task["description"] = "스테이징 배포 후 핵심 플로우를 검증한다."
        snapshot["tasks"] = [snapshot["tasks"][0], second_task, third_task]
        milestone_cache._items.clear()

        with patch("app.api.routes.llm_client", fake_llm, create=True):
            first = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json={"snapshot": snapshot, "max_milestones": 8})
            second = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json={"snapshot": snapshot, "max_milestones": 8})
            changed = copy.deepcopy(snapshot)
            changed["tasks"][1]["title"] = "React 대시보드 구현 변경"
            third = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json={"snapshot": changed, "max_milestones": 8})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(fake_llm.calls, 2)
        self.assertEqual(fake_llm.payloads[0]["mode"], "execution_mode")
        self.assertEqual(fake_llm.payloads[0]["task_summary"]["total"], 3)
        self.assertIn("React 대시보드 구현", fake_llm.payloads[0]["task_summary"]["titles"])

    def test_milestone_suggest_uses_24h_goal_cache_without_llm_recall(self):
        from app.services.cache import milestone_cache

        class CountingLlm:
            configured = True

            def __init__(self):
                self.calls = 0

            async def chat_json(self, **_):
                self.calls += 1
                return {
                    "milestones": [
                        {
                            "name": "계약 검증",
                            "due_date": "2026-05-20",
                            "ai_rationale": "API 계약부터 고정합니다.",
                        }
                    ]
                }

        fake_llm = CountingLlm()
        milestone_cache._items.clear()
        payload = {"snapshot": self._snapshot(), "max_milestones": 8}

        with patch("app.api.routes.llm_client", fake_llm, create=True):
            first = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json=payload)
            second = self.client.post("/v1/projects/proj_ABCDEF12/milestones:suggest", json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(fake_llm.calls, 1)
        self.assertEqual(first.json(), second.json())
        cache_entry = next(iter(milestone_cache._items.values()))
        self.assertGreater(cache_entry.expires_at - time.monotonic(), 86000)

    def test_analyze_returns_contract_and_cache_hit_on_second_call(self):
        request = {
            "snapshot": self._snapshot(),
            "options": {
                "request_decomposition_for": [],
                "schedule_horizon_days": 14,
                "include_unscheduled_in_response": True,
            },
        }

        first = self.client.post("/v1/projects/proj_ABCDEF12/analyze", json=request)
        second = self.client.post("/v1/projects/proj_ABCDEF12/analyze", json=request)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_body = first.json()
        second_body = second.json()
        self.assertEqual(first_body["snapshot_hash"], second_body["snapshot_hash"])
        self.assertFalse(first_body["meta"]["cache_hit"])
        self.assertTrue(second_body["meta"]["cache_hit"])
        self.assertEqual(first_body["priority"]["tasks_priority"][0]["task_id"], "task_ALPHA001")
        self.assertEqual(first_body["schedule"]["slot_proposals"][0]["selected_index"], 0)
        self.assertIn("checks", first_body["risk"])

    def test_analyze_accepts_task_without_optional_created_or_updated_timestamps(self):
        snapshot = self._snapshot()
        snapshot["tasks"][0].pop("created_at")
        snapshot["tasks"][0].pop("updated_at")

        response = self.client.post("/v1/projects/proj_ABCDEF12/analyze", json={"snapshot": snapshot, "options": {}})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["priority"]["tasks_priority"][0]["task_id"], "task_ALPHA001")

    def test_risk_action_schema_rejects_unknown_action_types(self):
        from pydantic import ValidationError

        from app.schemas import RiskResponse, RiskSuggestion, SoftCheck

        with self.assertRaises(ValidationError):
            RiskSuggestion(
                id="rs_BAD0000",
                fixes_check_ids=["workload_concentration"],
                action={"type": "delete_task", "target_task_id": "task_ALPHA001"},
                rationale_facts=["문서 계약 밖의 action type"],
                removes_blocker=True,
                user_facing_text="지원하지 않는 조치입니다.",
            )

        with self.assertRaises(ValidationError):
            SoftCheck(
                id="S1",
                trigger_label="implicit_dependency_suspected",
                confidence=0.8,
                involved_task_ids=["task_ALPHA001"],
                supporting_facts=["문서 계약 밖의 suggested_action type"],
                suggested_action={"type": "delete_task", "target_task_id": "task_ALPHA001"},
                user_facing_text="지원하지 않는 조치입니다.",
            )

        suggestions = [
            RiskSuggestion(
                id=f"rs_OVER{i:04d}",
                fixes_check_ids=["workload_concentration"],
                action={"type": "reassign", "target_task_id": "task_ALPHA001", "from": "mem_ALPHA1", "to": "mem_BRAVO1"},
                rationale_facts=["제안 수 제한 검증"],
                removes_blocker=True,
                user_facing_text="제안입니다.",
            )
            for i in range(6)
        ]
        with self.assertRaises(ValidationError):
            RiskResponse(
                project_id="proj_ABCDEF12",
                checks=[],
                soft_checks=[],
                task_risk_levels=[],
                member_workload=[],
                blockers_failed=[],
                suggestions=suggestions,
                summary="제안 수 제한 검증",
            )

    def test_task_decomposition_schema_rejects_invalid_subtask_contracts(self):
        from pydantic import ValidationError

        from app.schemas import TaskDecomposition

        with self.assertRaises(ValidationError):
            TaskDecomposition(
                source_task_id="task_ALPHA001",
                subtasks=[{"title": "하나뿐", "estimated_hours_range": [1, 2]}],
                decomposition_confidence=0.8,
            )

        with self.assertRaises(ValidationError):
            TaskDecomposition(
                source_task_id="task_ALPHA001",
                subtasks=[
                    {"title": "계약 정리", "estimated_hours_range": [0.5, 1]},
                    {"title": "구현"},
                ],
                decomposition_confidence=0.8,
            )

    def test_internal_calendar_event_source_defaults_to_ai_suggested(self):
        from app.schemas import CalendarEventSource, InternalCalendarEvent

        event = InternalCalendarEvent(
            event_id="evt_DEFAULT1",
            project_id="proj_ABCDEF12",
            task_id="task_ALPHA001",
            assignee_id="mem_ALPHA1",
            starts_at=self.now,
            ends_at=self.now + timedelta(hours=1),
            approved=True,
            approved_at=self.now,
        )

        self.assertEqual(event.source, CalendarEventSource.ai_suggested)

    def test_analyze_internal_failure_returns_agent_failed_contract_error(self):
        from fastapi.testclient import TestClient
        from app.main import create_app
        from app.services.metrics import agent_failure_summary, reset_agent_failure_metrics

        reset_agent_failure_metrics()
        client = TestClient(create_app(), raise_server_exceptions=False)
        request = {"snapshot": self._snapshot(), "options": {}}

        with patch("app.api.routes.analyze_snapshot", side_effect=RuntimeError("boom")):
            response = client.post("/v1/projects/proj_ABCDEF12/analyze", json=request)

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertEqual(body["error"]["code"], "agent_failed")
        self.assertIn("다시 시도", body["error"]["message"])
        self.assertEqual(agent_failure_summary()["total"], 1)
        self.assertEqual(agent_failure_summary()["by_agent"]["unknown"]["internal_error"], 1)
        self.assertEqual(client.get("/v1/health").json()["agent_failures"]["total"], 1)

    def test_analyze_rejects_more_than_five_decomposition_requests(self):
        request = {
            "snapshot": self._snapshot(),
            "options": {
                "request_decomposition_for": [
                    "task_ALPHA001",
                    "task_BRAVO001",
                    "task_CHARLIE1",
                    "task_DELTA001",
                    "task_ECHO0001",
                    "task_FOXTROT1",
                ]
            },
        }

        response = self.client.post("/v1/projects/proj_ABCDEF12/analyze", json=request)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_analyze_maps_missing_task_core_fields_to_task_info_insufficient(self):
        snapshot = self._snapshot()
        snapshot["tasks"][0].pop("title")
        snapshot["tasks"][0].pop("importance")
        snapshot["tasks"][0].pop("status")

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "task_info_insufficient")
        self.assertEqual(body["error"]["details"]["task_indices"], [0])
        self.assertEqual(body["error"]["details"]["fields"], ["importance", "status", "title"])

    def test_analyze_rejects_decomposition_request_when_estimate_is_missing(self):
        snapshot = self._snapshot()
        snapshot["tasks"][0]["estimated_hours"] = None

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={
                "snapshot": snapshot,
                "options": {"request_decomposition_for": ["task_ALPHA001"]},
            },
        )

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "task_info_insufficient")
        self.assertEqual(body["error"]["details"]["task_ids"], ["task_ALPHA001"])
        self.assertIn("estimated_hours", body["error"]["details"]["fields"])

    def test_analyze_meta_counts_all_configured_llm_calls(self):
        from app.orchestrator import analyze_snapshot
        from app.schemas import AnalyzeOptions, ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                system = kwargs["system"]
                if "deterministic priority scores" in system:
                    return {"rationales": []}
                if "rerank safe schedule candidates" in system:
                    return {
                        "rerankings": [
                            {
                                "task_id": "task_ALPHA001",
                                "ranked_indices": [0, 1, 2],
                                "selected_index": 0,
                                "rationale": "첫 번째 후보가 가장 빠른 안전 슬롯입니다.",
                            }
                        ]
                    }
                if "summarize deterministic project risk facts" in system:
                    return {"summary": "결정적 blocker는 없습니다."}
                return {"soft_checks": []}

        snapshot = ProjectSnapshot(**self._snapshot())
        with (
            patch("app.agents.priority.llm_client", FakeLlm(), create=True),
            patch("app.agents.schedule.llm_client", FakeLlm(), create=True),
            patch("app.agents.risk.llm_client", FakeLlm(), create=True),
        ):
            response = asyncio.run(
                analyze_snapshot(
                    project_id="proj_ABCDEF12",
                    snapshot=snapshot,
                    options=AnalyzeOptions(),
                    now=self.now,
                )
            )

        self.assertEqual(response.meta.llm_calls.priority_narrate, 1)
        self.assertEqual(response.meta.llm_calls.schedule_rerank, 1)
        self.assertEqual(response.meta.llm_calls.risk_soft_checks, 1)
        self.assertEqual(response.meta.llm_calls.risk_narrate, 0)
        self.assertEqual(response.meta.llm_calls.total, 3)

    def test_analyze_options_can_disable_llm_even_when_configured(self):
        class FailingLlm:
            configured = True

            async def chat_json(self, **kwargs):
                raise AssertionError("use_llm=false analyze must not call LLM")

        with (
            patch("app.agents.priority.llm_client", FailingLlm(), create=True),
            patch("app.agents.schedule.llm_client", FailingLlm(), create=True),
            patch("app.agents.risk.llm_client", FailingLlm(), create=True),
        ):
            response = self.client.post(
                "/v1/projects/proj_ABCDEF12/analyze",
                json={"snapshot": self._snapshot(), "options": {"use_llm": False}},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["meta"]["llm_calls"]["total"], 0)
        self.assertFalse(body["meta"]["llm_fallbacks"]["schedule_rerank_violation"])

    def test_analyze_can_use_openai_compatible_upstage_client_end_to_end(self):
        import httpx

        from app.orchestrator import analyze_snapshot
        from app.schemas import AnalyzeOptions, ProjectSnapshot
        from app.services.llm_client import UpstageClient
        from app.services.metrics import llm_raw_response_summary, reset_llm_raw_responses

        seen: list[dict] = []

        def handler(request):
            body = json.loads(request.content.decode())
            seen.append(body)
            system = body["messages"][0]["content"]
            if "deterministic priority scores" in system:
                content = {"rationales": [{"task_id": "task_ALPHA001", "text": "마감과 중요도가 높아 먼저 확인합니다."}]}
            elif "rerank safe schedule candidates" in system:
                content = {
                    "rerankings": [
                        {
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [0, 1, 2],
                            "selected_index": 0,
                            "rationale": "첫 번째 후보가 가장 빠른 안전 슬롯입니다.",
                        }
                    ]
                }
            elif "Find soft project risks" in system:
                content = {"soft_checks": []}
            elif "summarize deterministic project risk facts" in system:
                content = {"summary": "현재 결정적 blocker는 없습니다."}
            else:
                content = {}
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})

        client = UpstageClient(
            api_key="test-key",
            base_url="https://api.upstage.ai/v1",
            model="solar-pro3",
            daily_budget=10,
            transport=httpx.MockTransport(handler),
        )
        snapshot = ProjectSnapshot(**self._snapshot())
        reset_llm_raw_responses()

        with (
            patch("app.agents.priority.llm_client", client, create=True),
            patch("app.agents.schedule.llm_client", client, create=True),
            patch("app.agents.risk.llm_client", client, create=True),
        ):
            response = asyncio.run(
                analyze_snapshot(
                    project_id="proj_ABCDEF12",
                    snapshot=snapshot,
                    options=AnalyzeOptions(),
                    now=self.now,
                )
            )

        self.assertEqual(response.meta.llm_calls.total, 3)
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(body["model"] == "solar-pro3" for body in seen))
        self.assertTrue(all(body["stream"] is False for body in seen))
        self.assertEqual(client._calls_today, 3)
        self.assertEqual(llm_raw_response_summary()["total"], 3)
        self.assertEqual(response.priority.tasks_priority[0].rationale, "마감과 중요도가 높아 먼저 확인합니다.")
        self.assertEqual(response.schedule.slot_proposals[0].rerank_source, "llm_reranked")
        self.assertEqual(response.risk.summary, "현재 결정적 blocker는 없습니다. 실패한 보조 체크가 있으면 제안 카드를 검토하세요.")

    def test_e2e_analyze_falls_back_when_llm_rerank_violates_candidate_contract(self):
        from app.services.metrics import llm_safety_summary, reset_llm_safety_metrics

        class FakeScheduleLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [0, 99],
                            "selected_index": 99,
                            "rationale": "존재하지 않는 슬롯을 선택합니다.",
                        }
                    ]
                }

        reset_llm_safety_metrics()
        snapshot = self._snapshot()
        snapshot["project"]["name"] = "Invalid rerank E2E"

        with patch("app.agents.schedule.llm_client", FakeScheduleLlm(), create=True):
            response = self.client.post(
                "/v1/projects/proj_ABCDEF12/analyze",
                json={"snapshot": snapshot, "options": {}},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        proposal = body["schedule"]["slot_proposals"][0]
        self.assertEqual(proposal["task_id"], "task_ALPHA001")
        self.assertEqual(proposal["selected_index"], 0)
        self.assertEqual(proposal["rerank_source"], "deterministic")
        self.assertIn("rerank_violation:task_ALPHA001", body["schedule"]["warnings"])
        self.assertEqual(body["meta"]["llm_calls"]["schedule_rerank"], 2)
        self.assertTrue(body["meta"]["llm_fallbacks"]["schedule_rerank_violation"])
        self.assertFalse(body["meta"]["llm_fallbacks"]["risk_soft_checks_timeout"])
        self.assertEqual(llm_safety_summary()["by_purpose"]["schedule_rerank"]["blocked"], 2)

    def test_analyze_meta_reports_risk_soft_check_timeout_fallback(self):
        class TimeoutRiskLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": "현재 결정적 blocker는 없습니다."}
                raise TimeoutError("soft checks timed out")

        snapshot = self._snapshot()
        snapshot["project"]["name"] = "Soft check timeout meta"

        with patch("app.agents.risk.llm_client", TimeoutRiskLlm(), create=True):
            response = self.client.post(
                "/v1/projects/proj_ABCDEF12/analyze",
                json={"snapshot": snapshot, "options": {}},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["risk"]["soft_checks"], [])
        self.assertTrue(body["meta"]["llm_fallbacks"]["risk_soft_checks_timeout"])
        self.assertFalse(body["meta"]["llm_fallbacks"]["schedule_rerank_violation"])

    def test_analyze_meta_reports_narrator_fallback_template(self):
        class InvalidPriorityNarrator:
            configured = True

            async def chat_json(self, **kwargs):
                if "deterministic priority scores" in kwargs["system"]:
                    return {
                        "rationales": [
                            {"task_id": "task_ALPHA001", "text": "우선순위 999점입니다."}
                        ]
                    }
                return None

        snapshot = self._snapshot()
        snapshot["project"]["name"] = "Narrator fallback meta"

        with patch("app.agents.priority.llm_client", InvalidPriorityNarrator(), create=True):
            response = self.client.post(
                "/v1/projects/proj_ABCDEF12/analyze",
                json={"snapshot": snapshot, "options": {}},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["meta"]["llm_fallbacks"]["narrator_fallback_template"])
        self.assertTrue(body["meta"]["llm_fallbacks"]["priority_narrator_fallback"])
        self.assertFalse(body["meta"]["llm_fallbacks"]["risk_narrator_fallback"])
        self.assertIn("narrator_fallback_template", body["priority"]["warnings"])

    def test_priority_narrator_prompt_matches_verifier_contract(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        class RecordingLlm:
            configured = True

            def __init__(self):
                self.system = ""

            async def chat_json(self, **kwargs):
                self.system = kwargs["system"]
                return {
                    "rationales": [
                        {
                            "task_id": "task_ALPHA001",
                            "text": "마감과 중요도 근거로 먼저 확인합니다.",
                        }
                    ]
                }

        fake = RecordingLlm()
        snapshot = ProjectSnapshot(**self._snapshot())

        with patch("app.agents.priority.llm_client", fake, create=True):
            asyncio.run(run_priority(snapshot, self.now, []))

        self.assertIn("Return exactly one rationale per supplied task_id", fake.system)
        self.assertIn("Copy numeric tokens exactly", fake.system)
        self.assertIn("Do not round", fake.system)
        self.assertIn("Do not add ordinal or rank numbers", fake.system)

    def test_priority_narrator_accepts_supplied_rank_numbers(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        class RankNarrator:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rationales": [
                        {
                            "task_id": "task_ALPHA001",
                            "text": "현재 1위 task로 마감과 중요도 근거가 큽니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())

        with patch("app.agents.priority.llm_client", RankNarrator(), create=True):
            priority = asyncio.run(run_priority(snapshot, self.now, []))

        self.assertEqual(priority.tasks_priority[0].rationale, "현재 1위 task로 마감과 중요도 근거가 큽니다.")
        self.assertNotIn("narrator_fallback_template", priority.warnings)

    def test_priority_narrator_keeps_valid_items_when_one_llm_item_is_invalid(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        class PartialNarrator:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rationales": [
                        {
                            "task_id": "task_ALPHA001",
                            "text": "현재 1위 task로 마감과 중요도 근거가 큽니다.",
                        },
                        {
                            "task_id": "task_UNKNOWN1",
                            "text": "없는 task입니다.",
                        },
                    ]
                }

        snapshot = self._snapshot()
        second = copy.deepcopy(snapshot["tasks"][0])
        second["task_id"] = "task_BRAVO001"
        second["title"] = "두 번째 Task"
        second["importance"] = "medium"
        snapshot["tasks"].append(second)

        with patch("app.agents.priority.llm_client", PartialNarrator(), create=True):
            priority = asyncio.run(run_priority(ProjectSnapshot(**snapshot), self.now, []))

        self.assertEqual(priority.tasks_priority[0].rationale, "현재 1위 task로 마감과 중요도 근거가 큽니다.")
        self.assertNotIn("narrator_fallback_template", priority.warnings)

    def test_priority_evidence_distinguishes_assigned_workload_from_unassigned(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        snapshot["tasks"][0]["assignee_id"] = "mem_ALPHA1"
        priority = asyncio.run(run_priority(ProjectSnapshot(**snapshot), self.now, [], use_llm=False))

        evidence = priority.tasks_priority[0].evidence_facts
        self.assertTrue(any("담당자 배정됨" in fact for fact in evidence))
        self.assertFalse(any("담당자 미지정" in fact for fact in evidence))

    def test_priority_assigns_unassigned_active_tasks_by_role_then_load(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        snapshot["members"].append(
            {
                "member_id": "mem_FRONT1",
                "name": "최프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        ui_task = copy.deepcopy(snapshot["tasks"][0])
        ui_task["task_id"] = "task_FRONT001"
        ui_task["title"] = "React UI 화면 구현"
        ui_task["description"] = "대시보드 컴포넌트와 페이지를 구현한다."
        ui_task["assignee_id"] = None
        existing_task = copy.deepcopy(snapshot["tasks"][0])
        existing_task["task_id"] = "task_BACK0001"
        existing_task["title"] = "Backend API 유지"
        existing_task["assignee_id"] = "mem_ALPHA1"
        snapshot["tasks"] = [ui_task, existing_task]
        parsed = ProjectSnapshot(**snapshot)

        priority = asyncio.run(run_priority(parsed, self.now, [], use_llm=False))

        self.assertEqual(parsed.tasks[0].assignee_id, "mem_FRONT1")
        self.assertEqual(parsed.tasks[1].assignee_id, "mem_ALPHA1")
        self.assertEqual(len(priority.task_assignments), 1)
        assignment = priority.task_assignments[0]
        self.assertEqual(assignment.task_id, "task_FRONT001")
        self.assertEqual(assignment.assignee_id, "mem_FRONT1")
        self.assertTrue(any("role_hint=frontend" in fact for fact in assignment.rationale_facts))
        self.assertTrue(any("Frontend" in fact for fact in assignment.rationale_facts))

    def test_priority_assigns_ambiguous_unassigned_task_to_least_loaded_member(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        snapshot["members"].append(
            {
                "member_id": "mem_FRONT1",
                "name": "최프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        assigned = copy.deepcopy(snapshot["tasks"][0])
        assigned["task_id"] = "task_BUSY0001"
        assigned["title"] = "기존 백엔드 작업"
        assigned["assignee_id"] = "mem_ALPHA1"
        assigned["estimated_hours"] = 12
        ambiguous = copy.deepcopy(snapshot["tasks"][0])
        ambiguous["task_id"] = "task_DOCS0001"
        ambiguous["title"] = "문서 정리"
        ambiguous["description"] = "회의 후 정리할 내용을 작성한다."
        ambiguous["assignee_id"] = None
        snapshot["tasks"] = [assigned, ambiguous]
        parsed = ProjectSnapshot(**snapshot)

        priority = asyncio.run(run_priority(parsed, self.now, [], use_llm=False))

        self.assertEqual(parsed.tasks[1].assignee_id, "mem_FRONT1")
        self.assertEqual(priority.task_assignments[0].assignee_id, "mem_FRONT1")
        self.assertTrue(any("role_hint=none" in fact for fact in priority.task_assignments[0].rationale_facts))

    def test_schedule_rerank_prompt_matches_verifier_contract(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class RecordingLlm:
            configured = True

            def __init__(self):
                self.system = ""

            async def chat_json(self, **kwargs):
                self.system = kwargs["system"]
                return {
                    "rerankings": [
                        {
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [0, 1, 2],
                            "selected_index": 0,
                            "rationale": "첫 번째 후보가 가장 빠른 안전 슬롯입니다.",
                        }
                    ]
                }

        fake = RecordingLlm()
        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        with patch("app.agents.schedule.llm_client", fake, create=True):
            asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertIn("ranked_indices must contain every candidate index exactly once", fake.system)
        self.assertIn("Do not omit candidate indices", fake.system)
        self.assertIn("selected_index must be one of ranked_indices", fake.system)
        self.assertIn('"ranked_indices":[0,1,2]', fake.system)

    def test_schedule_rejects_missing_or_unknown_llm_rerank_task_ids(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_id": "task_TYPO0001",
                            "ranked_indices": [0, 1, 2],
                            "selected_index": 0,
                            "rationale": "존재하지 않는 task id입니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        with patch("app.agents.schedule.llm_client", FakeLlm(), create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertEqual(schedule.slot_proposals[0].rerank_source, "deterministic")
        self.assertIn("rerank_violation:task_ALPHA001", schedule.warnings)

    def test_schedule_rerank_uses_task_index_when_llm_typos_task_id(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_index": 0,
                            "task_id": "task_TYPO0001",
                            "ranked_indices": [1, 0, 2],
                            "selected_index": 1,
                            "rationale": "두 번째 후보가 가장 적합합니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        with patch("app.agents.schedule.llm_client", FakeLlm(), create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertEqual(schedule.warnings, [])
        self.assertEqual(schedule.slot_proposals[0].selected_index, 1)
        self.assertEqual(schedule.slot_proposals[0].rerank_source, "llm_reranked")

    def test_schedule_rerank_rejects_missing_ranked_indices_even_when_selected_index_is_valid(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_index": 0,
                            "selected_index": 1,
                            "rationale": "두 번째 후보가 가장 적합합니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        with patch("app.agents.schedule.llm_client", FakeLlm(), create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertIn("rerank_violation:task_ALPHA001", schedule.warnings)
        self.assertEqual(schedule.slot_proposals[0].selected_index, 0)
        self.assertEqual(schedule.slot_proposals[0].rerank_source, "deterministic")

    def test_risk_llm_prompts_match_verifier_contracts(self):
        from app.agents.priority import run_priority
        from app.agents.risk import RISK_NARRATOR_SUMMARY_MAX_CHARS, run_risk
        from app.schemas import ProjectSnapshot

        class RecordingLlm:
            configured = True

            def __init__(self):
                self.systems: list[str] = []

            async def chat_json(self, **kwargs):
                system = kwargs["system"]
                self.systems.append(system)
                if "summarize deterministic project risk facts" in system:
                    return {"summary": "현재 결정적 blocker는 없습니다."}
                return {"soft_checks": []}

        fake = RecordingLlm()
        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        with patch("app.agents.risk.llm_client", fake, create=True):
            asyncio.run(run_risk(snapshot, priority, None, self.now))

        soft_prompt = next(system for system in fake.systems if "Find soft project risks" in system)
        self.assertIn("Hard checks already handle deadline feasibility, explicit dependency correctness, and workload concentration", soft_prompt)
        self.assertIn("Do not report those as soft checks", soft_prompt)
        self.assertIn("Allowed trigger_label values", soft_prompt)
        self.assertIn("Rules by trigger_label", soft_prompt)
        self.assertIn("Return at most 3 soft_checks", soft_prompt)
        self.assertIn("If the evidence is weak or the issue belongs to hard checks", soft_prompt)
        self.assertIn("confidence must be between 0.5 and 1.0", soft_prompt)
        self.assertIn("involved_task_ids must use existing task IDs exactly", soft_prompt)
        self.assertIn("suggested_action.type must be one of", soft_prompt)
        self.assertFalse(any("summarize deterministic project risk facts" in system for system in fake.systems))

    def test_risk_narrator_prompt_matches_verifier_contract_when_hard_check_fails(self):
        from app.agents.priority import run_priority
        from app.agents.risk import RISK_NARRATOR_SUMMARY_MAX_CHARS, run_risk
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class RecordingLlm:
            configured = True

            def __init__(self):
                self.systems: list[str] = []

            async def chat_json(self, **kwargs):
                system = kwargs["system"]
                self.systems.append(system)
                if "summarize deterministic project risk facts" in system:
                    return {"summary": "마감일까지 완료 가능성 체크가 실패했습니다."}
                return {"soft_checks": []}

        fake = RecordingLlm()
        snapshot_payload = self._snapshot()
        snapshot_payload["tasks"][0]["deadline"] = (self.now - timedelta(days=1)).isoformat()
        snapshot = ProjectSnapshot(**snapshot_payload)
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, use_llm=False))

        with patch("app.agents.risk.llm_client", fake, create=True):
            asyncio.run(run_risk(snapshot, priority, schedule, self.now))

        narrator_prompt = next(system for system in fake.systems if "summarize deterministic project risk facts" in system)
        self.assertIn("Do not perform new risk analysis", narrator_prompt)
        self.assertIn("Prioritize failed_checks over task_risk_levels and member_workload", narrator_prompt)
        self.assertIn("If failed_checks is empty", narrator_prompt)
        self.assertIn("prefer check labels and PM actions over numbers", narrator_prompt)
        self.assertIn("Copy numeric tokens exactly", narrator_prompt)
        self.assertIn("Do not round", narrator_prompt)
        self.assertIn(f"Keep summary <={RISK_NARRATOR_SUMMARY_MAX_CHARS} chars", narrator_prompt)

    def test_analyze_emits_structured_agent_call_logs_without_task_body(self):
        from app.orchestrator import analyze_snapshot
        from app.schemas import AnalyzeOptions, ProjectSnapshot

        snapshot = ProjectSnapshot(**self._snapshot())
        observability_source = Path("BE/app/services/observability.py").read_text(encoding="utf-8")
        self.assertIn("structlog", observability_source)
        self.assertIn("JSONRenderer", observability_source)

        with self.assertLogs("app.observability", level="INFO") as logs:
            asyncio.run(
                analyze_snapshot(
                    project_id="proj_ABCDEF12",
                    snapshot=snapshot,
                    options=AnalyzeOptions(),
                    now=self.now,
                )
            )

        records = [json.loads(line.split("INFO:app.observability:", 1)[1]) for line in logs.output]
        agent_records = [record for record in records if record["event"] == "agent_call"]
        self.assertEqual([record["agent"] for record in agent_records], ["priority", "schedule", "risk", "super"])
        self.assertTrue(all(record["project_id"] == "proj_ABCDEF12" for record in agent_records))
        self.assertTrue(all(record["snapshot_hash"] for record in agent_records))
        self.assertTrue(all(isinstance(record["latency_ms"], int) for record in agent_records))
        self.assertNotIn("문서 계약에 맞는 API를 구현한다.", "\n".join(logs.output))

    def test_schedule_approve_rejects_stale_hash_and_accepts_cached_slot(self):
        stale = self.client.post(
            "/v1/projects/proj_ABCDEF12/schedule:approve",
            json={
                "snapshot_hash": "does-not-exist",
                "approvals": [{"task_id": "task_ALPHA001", "candidate_slot_index": 0}],
            },
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["error"]["code"], "snapshot_hash_stale")

        analyze = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": self._snapshot(), "options": {}},
        )
        snapshot_hash = analyze.json()["snapshot_hash"]

        approved = self.client.post(
            "/v1/projects/proj_ABCDEF12/schedule:approve",
            json={
                "snapshot_hash": snapshot_hash,
                "approvals": [{"task_id": "task_ALPHA001", "candidate_slot_index": 0}],
            },
        )

        self.assertEqual(approved.status_code, 200)
        body = approved.json()
        self.assertEqual(body["events_rejected"], [])
        self.assertEqual(body["events_created"][0]["task_id"], "task_ALPHA001")
        self.assertTrue(body["events_created"][0]["approved"])

    def test_milestone_approve_forces_approved_status(self):
        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/milestones:approve",
            json={
                "approved": [
                    {
                        "name": "MVP 백엔드 완성",
                        "due_date": "2026-05-20",
                        "ai_rationale": "프로젝트 종료 전 분석 API가 필요합니다.",
                    }
                ],
                "rejected_count": 0,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["milestones"][0]["status"], "approved")
        self.assertRegex(body["milestones"][0]["milestone_id"], r"^ms_[A-Za-z0-9]{6,}$")

    def test_e2e_normal_project_returns_all_three_agent_outputs_without_blockers(self):
        snapshot = self._snapshot()
        snapshot["members"].append(
            {
                "member_id": "mem_BRAVO1",
                "name": "김프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        base_task = snapshot["tasks"][0]
        tasks = []
        for index in range(5):
            task = copy.deepcopy(base_task)
            task["task_id"] = f"task_NORMAL{index}0"
            task["title"] = f"정상 시나리오 Task {index + 1}"
            task["assignee_id"] = "mem_ALPHA1" if index % 2 == 0 else "mem_BRAVO1"
            task["importance"] = "high" if index == 0 else "medium"
            task["estimated_hours"] = 1
            task["deadline"] = "2026-05-20T18:00:00+09:00"
            task["progress_percent"] = 40
            task["delay_reason"] = "현재 리스크 없음"
            tasks.append(task)
        snapshot["tasks"] = tasks

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["priority"]["tasks_priority"]), 5)
        self.assertEqual(len(body["schedule"]["slot_proposals"]), 5)
        self.assertEqual(len(body["risk"]["checks"]), 3)
        self.assertEqual(body["risk"]["blockers_failed"], [])

    def test_e2e_overload_and_unassigned_priority_fail_together(self):
        snapshot = self._snapshot()
        snapshot["members"][0]["weekly_capacity_hours"] = 8
        base_task = snapshot["tasks"][0]
        tasks = []
        for index in range(6):
            task = copy.deepcopy(base_task)
            task["task_id"] = f"task_LOAD{index}0000"
            task["title"] = f"과부하 시나리오 Task {index + 1}"
            task["assignee_id"] = None if index == 0 else "mem_ALPHA1"
            task["importance"] = "critical" if index == 0 else "high"
            task["estimated_hours"] = 4
            task["deadline"] = "2026-05-30T18:00:00+09:00"
            task["delay_reason"] = "부하 검증용 입력"
            tasks.append(task)
        snapshot["tasks"] = tasks

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        checks = {item["id"]: item["result"] for item in body["risk"]["checks"]}
        self.assertEqual(checks["workload_concentration"], "fail")
        self.assertTrue(any("workload_concentration" in item["fixes_check_ids"] for item in body["risk"]["suggestions"]))

    def test_risk_workload_concentration_suggestion_names_recommended_member(self):
        snapshot = self._snapshot()
        snapshot["members"].append(
            {
                "member_id": "mem_BRAVO1",
                "name": "김프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        snapshot["members"][0]["weekly_capacity_hours"] = 8
        snapshot["members"][1]["weekly_capacity_hours"] = 40 if len(snapshot["members"]) > 1 else 40
        second = copy.deepcopy(snapshot["tasks"][0])
        second["task_id"] = "task_BRAVO001"
        second["title"] = "기존 담당 작업"
        second["assignee_id"] = "mem_ALPHA1"
        second["importance"] = "high"
        second["estimated_hours"] = 4
        snapshot["tasks"][0]["estimated_hours"] = 8
        snapshot["tasks"].append(second)

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )

        self.assertEqual(response.status_code, 200)
        suggestion = next(
            item
            for item in response.json()["risk"]["suggestions"]
            if "workload_concentration" in item["fixes_check_ids"]
        )
        self.assertEqual(suggestion["action"]["type"], "reassign")
        self.assertEqual(suggestion["action"]["to"], "mem_BRAVO1")
        self.assertIn("김프론트", suggestion["user_facing_text"])
        self.assertTrue(any("김프론트" in fact for fact in suggestion["rationale_facts"]))

    def test_risk_a2_unschedulable_suggestion_tells_pm_exact_action(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        snapshot["tasks"][0]["title"] = "마감 전 배치 불가 Task"
        snapshot["tasks"][0]["estimated_hours"] = 80
        snapshot["tasks"][0]["deadline"] = (self.now + timedelta(days=1)).isoformat()
        parsed = ProjectSnapshot(**snapshot)
        priority = asyncio.run(run_priority(parsed, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(parsed, priority, self.now, horizon_days=14, use_llm=False))

        risk = asyncio.run(run_risk(parsed, priority, schedule, self.now, use_llm=False))

        suggestion = next(item for item in risk.suggestions if "deadline_feasibility" in item.fixes_check_ids)
        self.assertEqual(suggestion.action.type, "reschedule")
        self.assertEqual(suggestion.action.target_task_id, "task_ALPHA001")
        self.assertEqual(suggestion.action.from_, snapshot["tasks"][0]["deadline"])
        self.assertIsNotNone(suggestion.action.to)
        self.assertIn("마감 전 배치 불가 Task", suggestion.user_facing_text)
        self.assertIn("마감일을", suggestion.user_facing_text)
        self.assertIn(suggestion.action.to[:10], suggestion.user_facing_text)

    def test_risk_dependency_correctness_suggestion_reschedules_deadline_inversion(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        predecessor = copy.deepcopy(snapshot["tasks"][0])
        predecessor["task_id"] = "task_BLOCK001"
        predecessor["title"] = "선행 계약 확정"
        predecessor["status"] = "todo"
        predecessor["deadline"] = (self.now + timedelta(days=6)).isoformat()
        target = copy.deepcopy(snapshot["tasks"][0])
        target["task_id"] = "task_ALPHA001"
        target["title"] = "후행 개발 착수"
        target["predecessor_ids"] = ["task_BLOCK001"]
        target["deadline"] = (self.now + timedelta(days=5)).isoformat()
        snapshot["tasks"] = [predecessor, target]
        parsed = ProjectSnapshot(**snapshot)
        priority = asyncio.run(run_priority(parsed, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(parsed, priority, self.now, horizon_days=14, use_llm=False))

        risk = asyncio.run(run_risk(parsed, priority, schedule, self.now, use_llm=False))

        suggestion = next(item for item in risk.suggestions if "dependency_correctness" in item.fixes_check_ids)
        self.assertEqual(suggestion.action.type, "reschedule")
        self.assertEqual(suggestion.action.target_task_id, "task_ALPHA001")
        self.assertIn("후행 개발 착수", suggestion.user_facing_text)
        self.assertIn("선행 계약 확정", suggestion.user_facing_text)
        self.assertIn("마감", suggestion.user_facing_text)

    def test_risk_dependency_correctness_suggestion_reschedules_slot_inversion(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import CandidateSlot, ProjectSnapshot, ScheduleResponse, SlotProposal, SlotQuality

        snapshot = self._snapshot()
        predecessor = copy.deepcopy(snapshot["tasks"][0])
        predecessor["task_id"] = "task_BLOCK001"
        predecessor["title"] = "선행 계약 확정"
        predecessor["status"] = "done"
        predecessor["deadline"] = (self.now + timedelta(days=5)).isoformat()
        target = copy.deepcopy(snapshot["tasks"][0])
        target["task_id"] = "task_ALPHA001"
        target["title"] = "후행 개발 착수"
        target["predecessor_ids"] = ["task_BLOCK001"]
        target["deadline"] = (self.now + timedelta(days=5)).isoformat()
        snapshot["tasks"] = [predecessor, target]
        parsed = ProjectSnapshot(**snapshot)
        priority = asyncio.run(run_priority(parsed, self.now, [], use_llm=False))
        schedule = ScheduleResponse(
            project_id=parsed.project.project_id,
            slot_proposals=[
                SlotProposal(
                    task_id="task_BLOCK001",
                    candidate_slots=[
                        CandidateSlot(
                            starts_at=self.now + timedelta(hours=3),
                            ends_at=self.now + timedelta(hours=5),
                            quality=SlotQuality.acceptable,
                            fit_score=80,
                            conflicts=[],
                            rationale_facts=["테스트 선행 슬롯"],
                        )
                    ],
                    selected_index=0,
                ),
                SlotProposal(
                    task_id="task_ALPHA001",
                    candidate_slots=[
                        CandidateSlot(
                            starts_at=self.now + timedelta(hours=4),
                            ends_at=self.now + timedelta(hours=6),
                            quality=SlotQuality.acceptable,
                            fit_score=80,
                            conflicts=[],
                            rationale_facts=["테스트 후행 슬롯"],
                        )
                    ],
                    selected_index=0,
                ),
            ],
            unschedulable=[],
            warnings=[],
        )

        risk = asyncio.run(run_risk(parsed, priority, schedule, self.now, use_llm=False))

        check = next(item for item in risk.checks if item.id == "dependency_correctness")
        self.assertEqual(check.result, "fail")
        suggestion = next(item for item in risk.suggestions if "dependency_correctness" in item.fixes_check_ids)
        self.assertEqual(suggestion.action.type, "reschedule")
        self.assertEqual(suggestion.action.target_task_id, "task_ALPHA001")
        self.assertIn("후행 개발 착수", suggestion.user_facing_text)
        self.assertIn("선행 계약 확정", suggestion.user_facing_text)
        self.assertIn("먼저 끝나도록", suggestion.user_facing_text)

    def test_risk_workload_overload_suggestion_targets_reassignable_task_and_member(self):
        snapshot = self._snapshot()
        snapshot["members"][0]["weekly_capacity_hours"] = 8
        snapshot["members"].append(
            {
                "member_id": "mem_BRAVO1",
                "name": "김프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        base_task = snapshot["tasks"][0]
        tasks = []
        for index in range(4):
            task = copy.deepcopy(base_task)
            task["task_id"] = f"task_OVER{index}000"
            task["title"] = f"과부하 재배정 Task {index + 1}"
            task["assignee_id"] = "mem_ALPHA1"
            task["importance"] = "high"
            task["estimated_hours"] = 4
            task["deadline"] = "2026-05-30T18:00:00+09:00"
            task["delay_reason"] = "부하 검증용 입력"
            tasks.append(task)
        snapshot["tasks"] = tasks

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        suggestion = next(item for item in body["risk"]["suggestions"] if "workload_concentration" in item["fixes_check_ids"])
        self.assertEqual(suggestion["action"]["type"], "reassign")
        self.assertIn(suggestion["action"]["target_task_id"], {task["task_id"] for task in tasks})
        self.assertEqual(suggestion["action"]["from"], "mem_ALPHA1")
        self.assertEqual(suggestion["action"]["to"], "mem_BRAVO1")

    def test_analyze_reports_circular_dependency_as_risk_blocker(self):
        snapshot = self._snapshot()
        second = copy.deepcopy(snapshot["tasks"][0])
        second["task_id"] = "task_BRAVO001"
        second["title"] = "프론트 연결"
        snapshot["tasks"][0]["predecessor_ids"] = ["task_BRAVO001"]
        second["predecessor_ids"] = ["task_ALPHA001"]
        snapshot["tasks"].append(second)

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        dependency = next(item for item in body["risk"]["checks"] if item["id"] == "dependency_correctness")
        self.assertEqual(dependency["result"], "fail")
        self.assertIn("dependency_correctness", body["risk"]["blockers_failed"])
        self.assertTrue(any("순환 경로" in fact for fact in dependency["evidence_facts"]))
        suggestion = next(item for item in body["risk"]["suggestions"] if "dependency_correctness" in item["fixes_check_ids"])
        self.assertEqual(suggestion["action"]["type"], "remove_predecessor")
        self.assertEqual(suggestion["action"]["target_task_id"], "task_ALPHA001")
        self.assertEqual(suggestion["action"]["to"], "task_BRAVO001")

        simulated = self.client.post(
            "/v1/projects/proj_ABCDEF12/risk:simulate",
            json={"snapshot": snapshot, "applied_suggestion_ids": [suggestion["id"]]},
        )

        self.assertEqual(simulated.status_code, 200)
        self.assertIn("dependency_correctness", simulated.json()["score_action_coherence"]["changed_to_pass_ids"])

    def test_schedule_approve_rejects_out_of_range_and_override_conflict(self):
        snapshot = self._snapshot()
        snapshot["calendar_events"] = [
            {
                "event_id": "evt_BLOCK001",
                "project_id": "proj_ABCDEF12",
                "task_id": "task_ALPHA001",
                "assignee_id": "mem_ALPHA1",
                "starts_at": self.now.replace(hour=10).isoformat(),
                "ends_at": self.now.replace(hour=12).isoformat(),
                "approved": True,
                "approved_at": self.now.isoformat(),
                "source": "external_blocking",
            }
        ]

        analyze = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )
        self.assertEqual(analyze.status_code, 200)
        snapshot_hash = analyze.json()["snapshot_hash"]

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/schedule:approve",
            json={
                "snapshot_hash": snapshot_hash,
                "approvals": [
                    {"task_id": "task_ALPHA001", "candidate_slot_index": 99},
                    {
                        "task_id": "task_ALPHA001",
                        "candidate_slot_index": 0,
                        "override_starts_at": self.now.replace(hour=10).isoformat(),
                        "override_ends_at": self.now.replace(hour=11).isoformat(),
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        reasons = [item["reason"] for item in response.json()["events_rejected"]]
        self.assertIn("candidate_index_out_of_range", reasons)
        self.assertIn("override_conflicts", reasons)

    def test_schedule_approve_rejects_invalid_override_range(self):
        analyze = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": self._snapshot(), "options": {}},
        )
        self.assertEqual(analyze.status_code, 200)
        snapshot_hash = analyze.json()["snapshot_hash"]

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/schedule:approve",
            json={
                "snapshot_hash": snapshot_hash,
                "approvals": [
                    {
                        "task_id": "task_ALPHA001",
                        "candidate_slot_index": 0,
                        "override_starts_at": self.now.replace(hour=13).isoformat(),
                        "override_ends_at": self.now.replace(hour=12).isoformat(),
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["events_created"], [])
        self.assertEqual(response.json()["events_rejected"][0]["reason"], "invalid_override_range")

    def test_schedule_approve_rejects_override_conflict_with_same_request_event(self):
        snapshot = self._snapshot()
        second = copy.deepcopy(snapshot["tasks"][0])
        second["task_id"] = "task_BRAVO001"
        second["title"] = "동시 승인 충돌 Task"
        snapshot["tasks"].append(second)

        analyze = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )
        self.assertEqual(analyze.status_code, 200)
        snapshot_hash = analyze.json()["snapshot_hash"]

        response = self.client.post(
            "/v1/projects/proj_ABCDEF12/schedule:approve",
            json={
                "snapshot_hash": snapshot_hash,
                "approvals": [
                    {
                        "task_id": "task_ALPHA001",
                        "candidate_slot_index": 0,
                        "override_starts_at": self.now.replace(hour=13).isoformat(),
                        "override_ends_at": self.now.replace(hour=14).isoformat(),
                    },
                    {
                        "task_id": "task_BRAVO001",
                        "candidate_slot_index": 0,
                        "override_starts_at": self.now.replace(hour=13, minute=30).isoformat(),
                        "override_ends_at": self.now.replace(hour=14, minute=30).isoformat(),
                    },
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["events_created"]), 1)
        self.assertEqual(body["events_rejected"][0]["task_id"], "task_BRAVO001")
        self.assertEqual(body["events_rejected"][0]["reason"], "override_conflicts")

    def test_priority_is_deterministic_for_same_snapshot_and_now(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        snapshot = ProjectSnapshot(**self._snapshot())

        results = [
            asyncio.run(run_priority(snapshot, self.now, []))
            .model_dump(mode="json")["tasks_priority"]
            for _ in range(5)
        ]

        self.assertTrue(all(result == results[0] for result in results))

    def test_schedule_and_hard_risk_are_deterministic_for_same_snapshot_and_now(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        schedules = [
            asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14)).model_dump(mode="json")
            for _ in range(5)
        ]
        risks = [
            asyncio.run(run_risk(snapshot, priority, None, self.now, use_llm=False)).model_dump(mode="json")["checks"]
            for _ in range(5)
        ]

        self.assertTrue(all(item["slot_proposals"] == schedules[0]["slot_proposals"] for item in schedules))
        self.assertTrue(all(item == risks[0] for item in risks))

    def test_deterministic_agents_meet_100_task_performance_targets(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        snapshot["members"] = [
            {
                "member_id": f"mem_PERF{index:02d}",
                "name": f"성능 멤버 {index}",
                "role": "Engineer",
                "weekly_capacity_hours": 80,
                "available_hours": [],
            }
            for index in range(5)
        ]
        base_task = snapshot["tasks"][0]
        tasks = []
        for index in range(100):
            task = copy.deepcopy(base_task)
            task["task_id"] = f"task_PERF{index:04d}"
            task["title"] = f"성능 검증 Task {index:03d}"
            task["assignee_id"] = f"mem_PERF{index % 5:02d}"
            task["importance"] = "high" if index % 3 else "critical"
            task["estimated_hours"] = 1
            task["deadline"] = "2026-06-30T18:00:00+09:00"
            task["predecessor_ids"] = []
            tasks.append(task)
        snapshot["tasks"] = tasks
        parsed = ProjectSnapshot(**snapshot)

        priority_start = time.perf_counter()
        priority = asyncio.run(run_priority(parsed, self.now, [], use_llm=False))
        priority_ms = (time.perf_counter() - priority_start) * 1000

        schedule_start = time.perf_counter()
        schedule = asyncio.run(run_schedule(parsed, priority, self.now, horizon_days=30))
        schedule_ms = (time.perf_counter() - schedule_start) * 1000

        risk_start = time.perf_counter()
        risk = asyncio.run(run_risk(parsed, priority, schedule, self.now, use_llm=False))
        risk_ms = (time.perf_counter() - risk_start) * 1000

        self.assertEqual(len(priority.tasks_priority), 100)
        self.assertGreaterEqual(len(schedule.slot_proposals), 90)
        self.assertEqual(len(risk.checks), 3)
        self.assertLessEqual(priority_ms, 30)
        self.assertLessEqual(schedule_ms, 200)
        self.assertLessEqual(risk_ms, 30)

    def test_priority_skips_invalid_llm_decomposition_shape(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "Decompose" in kwargs["system"]:
                    return {
                        "subtasks": [
                            {"title": "너무 큰 작업 A", "estimated_hours_range": [10, 12]},
                            {"title": "너무 큰 작업 B", "estimated_hours_range": [10, 12]},
                        ],
                        "decomposition_confidence": 0.8,
                    }
                return {"rationales": []}

        snapshot = ProjectSnapshot(**self._snapshot())
        with patch("app.agents.priority.llm_client", FakeLlm(), create=True):
            priority = asyncio.run(run_priority(snapshot, self.now, ["task_ALPHA001"]))

        self.assertEqual(priority.agent_meta.decomposition_calls, 2)
        self.assertEqual(priority.agent_meta.schema_retries, 1)
        self.assertEqual(priority.task_decompositions, [])
        self.assertIn("decomposition_schema_violation:task_ALPHA001", priority.warnings)

    def test_priority_retries_once_after_invalid_llm_decomposition(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            def __init__(self):
                self.decompose_calls = 0

            async def chat_json(self, **kwargs):
                if "Decompose" not in kwargs["system"]:
                    return {"rationales": []}
                self.decompose_calls += 1
                if self.decompose_calls == 1:
                    return {"subtasks": [{"title": "하나뿐", "estimated_hours_range": [1, 1]}]}
                return {
                    "subtasks": [
                        {"title": "계약 정리", "description": "입출력 확인", "estimated_hours_range": [0.5, 1.0]},
                        {"title": "구현", "description": "라우터 작성", "estimated_hours_range": [0.5, 1.0]},
                    ],
                    "decomposition_confidence": 0.8,
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        fake = FakeLlm()
        with patch("app.agents.priority.llm_client", fake, create=True):
            priority = asyncio.run(run_priority(snapshot, self.now, ["task_ALPHA001"]))

        self.assertEqual(priority.agent_meta.decomposition_calls, 2)
        self.assertEqual(priority.agent_meta.schema_retries, 1)
        self.assertEqual(len(priority.task_decompositions), 1)

    def test_priority_retries_once_after_forbidden_llm_narrator_text(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot
        from app.services.metrics import policy_violation_summary, reset_policy_violation_metrics

        class FakeLlm:
            configured = True

            def __init__(self):
                self.narrator_calls = 0

            async def chat_json(self, **kwargs):
                if "deterministic priority scores" not in kwargs["system"]:
                    return None
                self.narrator_calls += 1
                if self.narrator_calls == 1:
                    return {
                        "rationales": [
                            {"task_id": "task_ALPHA001", "text": "담당자가 게으른 상태라 위험합니다."}
                        ]
                    }
                return {
                    "rationales": [
                        {
                            "task_id": "task_ALPHA001",
                            "text": "마감과 중요도 fact만 근거로 먼저 확인합니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        fake = FakeLlm()
        reset_policy_violation_metrics()
        with patch("app.agents.priority.llm_client", fake, create=True):
            priority = asyncio.run(run_priority(snapshot, self.now, []))

        self.assertEqual(fake.narrator_calls, 2)
        self.assertEqual(priority.agent_meta.narrator_calls, 2)
        self.assertEqual(priority.agent_meta.schema_retries, 1)
        self.assertNotIn("게으", priority.tasks_priority[0].rationale)
        self.assertIn("마감과 중요도 fact", priority.tasks_priority[0].rationale)
        self.assertEqual(policy_violation_summary()["by_filter"]["forbidden_word"], 1)

    def test_priority_rejects_llm_narrator_numbers_not_present_in_facts(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "deterministic priority scores" not in kwargs["system"]:
                    return None
                return {
                    "rationales": [
                        {
                            "task_id": "task_ALPHA001",
                            "text": "우선순위 999점입니다. 마감까지 77일 남았습니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        with patch("app.agents.priority.llm_client", FakeLlm(), create=True):
            priority = asyncio.run(run_priority(snapshot, self.now, []))

        self.assertNotIn("999", priority.tasks_priority[0].rationale)
        self.assertNotIn("77", priority.tasks_priority[0].rationale)
        self.assertEqual(priority.agent_meta.narrator_calls, 2)
        self.assertEqual(priority.agent_meta.schema_retries, 1)

    def test_priority_keeps_valid_llm_decomposition(self):
        from app.agents.priority import run_priority
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "Decompose" in kwargs["system"]:
                    return {
                        "subtasks": [
                            {"title": "API 계약 정리", "description": "입출력 확인", "estimated_hours_range": [0.5, 1.0]},
                            {
                                "title": "라우터 구현",
                                "description": "FastAPI 라우터 작성",
                                "estimated_hours_range": [0.5, 1.0],
                                "suggested_predecessors_within_decomposition": [0],
                            },
                        ],
                        "decomposition_confidence": 0.82,
                    }
                return {"rationales": []}

        snapshot = ProjectSnapshot(**self._snapshot())
        with patch("app.agents.priority.llm_client", FakeLlm(), create=True):
            priority = asyncio.run(run_priority(snapshot, self.now, ["task_ALPHA001"]))

        self.assertEqual(priority.agent_meta.decomposition_calls, 1)
        self.assertEqual(len(priority.task_decompositions), 1)
        self.assertEqual(priority.task_decompositions[0].subtasks[1].suggested_predecessors_within_decomposition, [0])

    def test_soft_checks_keep_existing_task_ids_only(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot

        payload = self._snapshot()
        payload["tasks"][0]["title"] = "API"
        payload["tasks"][0]["description"] = ""
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertGreaterEqual(len(risk.soft_checks), 1)
        valid_task_ids = {task["task_id"] for task in payload["tasks"]}
        for check in risk.soft_checks:
            self.assertTrue(set(check.involved_task_ids).issubset(valid_task_ids))
            self.assertGreaterEqual(check.confidence, 0.5)

    def test_risk_simulate_applies_reassign_suggestion_and_reports_changed_checks(self):
        snapshot = self._snapshot()
        snapshot["members"].append(
            {
                "member_id": "mem_BRAVO1",
                "name": "김프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        snapshot["members"][0]["weekly_capacity_hours"] = 8
        snapshot["members"][1]["weekly_capacity_hours"] = 8 if len(snapshot["members"]) > 1 else 8
        snapshot["tasks"][0]["estimated_hours"] = 1.5
        extra_tasks = []
        for index in range(5):
            task = copy.deepcopy(snapshot["tasks"][0])
            task["task_id"] = f"task_LOADSIM{index}"
            task["title"] = f"부하 시뮬레이션 Task {index + 1}"
            task["estimated_hours"] = 1.5
            extra_tasks.append(task)
        snapshot["tasks"].extend(extra_tasks)

        before = self.client.post(
            "/v1/projects/proj_ABCDEF12/analyze",
            json={"snapshot": snapshot, "options": {}},
        )
        self.assertEqual(before.status_code, 200)
        suggestion = next(
            item
            for item in before.json()["risk"]["suggestions"]
            if "workload_concentration" in item["fixes_check_ids"]
        )

        simulated = self.client.post(
            "/v1/projects/proj_ABCDEF12/risk:simulate",
            json={"snapshot": snapshot, "applied_suggestion_ids": [suggestion["id"]]},
        )

        self.assertEqual(simulated.status_code, 200)
        body = simulated.json()
        before_workload = next(item for item in body["before"]["checks"] if item["id"] == "workload_concentration")
        after_workload = next(item for item in body["after"]["checks"] if item["id"] == "workload_concentration")
        self.assertEqual(before_workload["result"], "fail")
        self.assertEqual(after_workload["result"], "pass")
        self.assertIn("workload_concentration", body["changed_check_ids"])
        self.assertGreaterEqual(body["score_action_coherence"]["priority_delta"], 5)
        self.assertTrue(body["score_action_coherence"]["passes_threshold"])
        self.assertEqual(
            body["score_action_coherence"]["priority_delta_by_task"]["task_ALPHA001"],
            body["score_action_coherence"]["priority_delta"],
        )

    def test_risk_simulate_does_not_call_llm_even_when_configured(self):
        snapshot = self._snapshot()
        snapshot["members"].append(
            {
                "member_id": "mem_BRAVO1",
                "name": "김프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        snapshot["tasks"][0]["assignee_id"] = None

        class FailingLlm:
            configured = True

            async def chat_json(self, **_):
                raise AssertionError("risk:simulate must not call LLM")

        with (
            patch("app.agents.priority.llm_client", FailingLlm(), create=True),
            patch("app.agents.risk.llm_client", FailingLlm(), create=True),
        ):
            simulated = self.client.post(
                "/v1/projects/proj_ABCDEF12/risk:simulate",
                json={"snapshot": snapshot, "applied_suggestion_ids": []},
            )

        self.assertEqual(simulated.status_code, 200)
        self.assertIn("before", simulated.json())
        self.assertIn("after", simulated.json())

    def test_schedule_accepts_valid_llm_rerank_without_changing_candidate_slots(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [1, 0, 2],
                            "selected_index": 1,
                            "rationale": "두 번째 후보가 오후 검토 시간과 더 잘 맞습니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))

        with patch("app.agents.schedule.llm_client", FakeLlm(), create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        proposal = schedule.slot_proposals[0]
        self.assertGreaterEqual(len(proposal.candidate_slots), 2)
        self.assertEqual(proposal.selected_index, 1)
        self.assertEqual(proposal.rerank_source, "llm_reranked")
        self.assertEqual(len(proposal.candidate_slots), 3)

    def test_schedule_priority_order_does_not_break_dependencies(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        payload = self._snapshot()
        predecessor = payload["tasks"][0]
        child = {**predecessor}
        predecessor["task_id"] = "task_SETUP001"
        predecessor["title"] = "Setup API contract"
        predecessor["importance"] = "medium"
        predecessor["estimated_hours"] = 2
        predecessor["predecessor_ids"] = []
        child["task_id"] = "task_CHILD001"
        child["title"] = "Launch critical integration"
        child["importance"] = "critical"
        child["estimated_hours"] = 2
        child["predecessor_ids"] = ["task_SETUP001"]
        payload["tasks"] = [child, predecessor]

        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        slot_by_task = {
            proposal.task_id: proposal.candidate_slots[proposal.selected_index]
            for proposal in schedule.slot_proposals
        }
        self.assertEqual(schedule.unschedulable, [])
        self.assertLessEqual(slot_by_task["task_SETUP001"].ends_at, slot_by_task["task_CHILD001"].starts_at)

    def test_schedule_places_child_after_unfinished_predecessor_in_same_run(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        payload = self._snapshot()
        first = payload["tasks"][0]
        second = {**first}
        first["task_id"] = "task_FIRST001"
        first["title"] = "Write API draft"
        first["status"] = "todo"
        first["estimated_hours"] = 2
        first["predecessor_ids"] = []
        second["task_id"] = "task_SECOND01"
        second["title"] = "Review API draft"
        second["status"] = "todo"
        second["estimated_hours"] = 2
        second["predecessor_ids"] = ["task_FIRST001"]
        payload["tasks"] = [second, first]

        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        slot_by_task = {
            proposal.task_id: proposal.candidate_slots[proposal.selected_index]
            for proposal in schedule.slot_proposals
        }
        self.assertEqual(schedule.unschedulable, [])
        self.assertLessEqual(slot_by_task["task_FIRST001"].ends_at, slot_by_task["task_SECOND01"].starts_at)

    def test_schedule_spreads_tasks_across_one_hour_buckets(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        payload = self._snapshot()
        base_member = payload["members"][0]
        base_task = payload["tasks"][0]
        payload["members"] = [
            {
                **base_member,
                "member_id": f"mem_SPREAD{i:02d}",
                "name": f"Member {i}",
                "role": "Engineer",
            }
            for i in range(4)
        ]
        payload["tasks"] = []
        for index in range(4):
            task = {**base_task}
            task["task_id"] = f"task_SPREAD{index:02d}"
            task["title"] = f"Spread task {index}"
            task["assignee_id"] = f"mem_SPREAD{index:02d}"
            task["estimated_hours"] = 1
            task["importance"] = "high"
            task["predecessor_ids"] = []
            task["deadline"] = (self.now + timedelta(days=3)).isoformat()
            payload["tasks"].append(task)

        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14, use_llm=False))

        buckets: dict[str, int] = {}
        for proposal in schedule.slot_proposals:
            slot = proposal.candidate_slots[proposal.selected_index]
            bucket = slot.starts_at.replace(minute=0, second=0, microsecond=0).isoformat()
            buckets[bucket] = buckets.get(bucket, 0) + 1
        self.assertLessEqual(max(buckets.values()), 2)

    def test_schedule_rejects_incomplete_llm_ranked_indices(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_index": 0,
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [1],
                            "selected_index": 1,
                            "rationale": "후보 일부만 반환합니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        with patch("app.agents.schedule.llm_client", FakeLlm(), create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertEqual(schedule.slot_proposals[0].selected_index, 0)
        self.assertEqual(schedule.slot_proposals[0].rerank_source, "deterministic")
        self.assertIn("rerank_violation:task_ALPHA001", schedule.warnings)

    def test_schedule_repair_uses_alternate_candidate_for_density_violation(self):
        from app.agents.schedule import repair_schedule, validate_selected_schedule
        from app.schemas import CandidateSlot, ProjectSnapshot, SlotProposal, SlotQuality

        payload = self._snapshot()
        base_member = payload["members"][0]
        base_task = payload["tasks"][0]
        payload["members"] = [
            {**base_member, "member_id": f"mem_REPAIR{i:02d}", "name": f"Repair {i}"}
            for i in range(3)
        ]
        payload["tasks"] = []
        for index in range(3):
            task = {**base_task}
            task["task_id"] = f"task_REPAIR{index:02d}"
            task["assignee_id"] = f"mem_REPAIR{index:02d}"
            task["estimated_hours"] = 1
            task["deadline"] = (self.now + timedelta(days=2)).isoformat()
            payload["tasks"].append(task)
        snapshot = ProjectSnapshot(**payload)

        def slot(hour: int) -> CandidateSlot:
            starts_at = self.now.replace(hour=hour, minute=0)
            return CandidateSlot(
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=1),
                quality=SlotQuality.preferred,
                fit_score=90,
                conflicts=[],
                rationale_facts=[f"{hour}:00 후보"],
            )

        proposals = [
            SlotProposal(
                task_id=f"task_REPAIR{index:02d}",
                candidate_slots=[slot(9), slot(10 + index)],
                selected_index=0,
            )
            for index in range(3)
        ]
        self.assertTrue(any(item.startswith("density_violation:") for item in validate_selected_schedule(snapshot=snapshot, proposals=proposals)))

        repaired, warnings = repair_schedule(snapshot=snapshot, proposals=proposals)

        self.assertEqual(warnings, [])
        self.assertEqual(validate_selected_schedule(snapshot=snapshot, proposals=repaired), [])
        self.assertTrue(any(proposal.selected_index == 1 for proposal in repaired))

    def test_schedule_applies_priority_assignments_before_packing(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        payload = self._snapshot()
        payload["members"].append(
            {
                "member_id": "mem_FRONT1",
                "name": "최프론트",
                "role": "Frontend",
                "weekly_capacity_hours": 40,
                "available_hours": [],
            }
        )
        payload["tasks"][0]["title"] = "React UI 화면 구현"
        payload["tasks"][0]["description"] = "대시보드 컴포넌트와 페이지를 구현한다."
        payload["tasks"][0]["assignee_id"] = None
        original_snapshot = ProjectSnapshot(**copy.deepcopy(payload))
        priority_snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(priority_snapshot, self.now, [], use_llm=False))

        schedule = asyncio.run(run_schedule(original_snapshot, priority, self.now, horizon_days=14, use_llm=False))

        self.assertEqual(schedule.unschedulable, [])
        self.assertEqual(len(schedule.slot_proposals), 1)

    def test_schedule_moves_hard_validation_failures_to_unschedulable(self):
        from app.agents.schedule import finalize_valid_schedule
        from app.schemas import CandidateSlot, ProjectSnapshot, SlotProposal, SlotQuality

        payload = self._snapshot()
        task = payload["tasks"][0]
        task["task_id"] = "task_INVALID1"
        task["deadline"] = self.now.replace(hour=10).isoformat()
        snapshot = ProjectSnapshot(**payload)
        starts_at = self.now.replace(hour=17)
        invalid_slot = CandidateSlot(
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            quality=SlotQuality.preferred,
            fit_score=90,
            conflicts=[],
            rationale_facts=["마감 이후 후보"],
        )
        proposals = [SlotProposal(task_id="task_INVALID1", candidate_slots=[invalid_slot], selected_index=0)]

        valid, unschedulable, warnings = finalize_valid_schedule(
            snapshot=snapshot,
            proposals=proposals,
            unschedulable=[],
            warnings=[],
        )

        self.assertEqual(valid, [])
        self.assertEqual(unschedulable[0].task_id, "task_INVALID1")
        self.assertIn("no_capacity_before_deadline", unschedulable[0].reasons)
        self.assertTrue(any(item.startswith("deadline_exceeded:task_INVALID1") for item in warnings))

    def test_schedule_rerank_prompt_includes_task_context_and_priority(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class RecordingLlm:
            configured = True

            def __init__(self):
                self.user_payload = {}

            async def chat_json(self, **kwargs):
                self.user_payload = json.loads(kwargs["user"])
                return {
                    "rerankings": [
                        {
                            "task_index": 0,
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [0, 1, 2],
                            "selected_index": 0,
                            "rationale": "첫 번째 후보가 작업 맥락과 맞습니다.",
                        }
                    ]
                }

        payload = self._snapshot()
        payload["tasks"][0]["title"] = "API 설계 리뷰"
        payload["tasks"][0]["description"] = "PM 승인 전 API 계약을 검토한다."
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        fake = RecordingLlm()

        with patch("app.agents.schedule.llm_client", fake, create=True):
            asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        task_payload = fake.user_payload["tasks"][0]
        self.assertEqual(task_payload["title"], "API 설계 리뷰")
        self.assertEqual(task_payload["description"], "PM 승인 전 API 계약을 검토한다.")
        self.assertEqual(task_payload["priority_score"], priority.tasks_priority[0].score)
        self.assertEqual(task_payload["priority_rank"], priority.tasks_priority[0].rank)

    def test_schedule_skips_llm_rerank_when_each_task_has_one_candidate(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class FailingLlm:
            configured = True

            async def chat_json(self, **_):
                raise AssertionError("single-candidate schedules should skip LLM rerank")

        snapshot = self._snapshot()
        snapshot["tasks"][0]["estimated_hours"] = 9
        snapshot["tasks"][0]["deadline"] = self.now.replace(hour=23).isoformat()
        parsed = ProjectSnapshot(**snapshot)
        priority = asyncio.run(run_priority(parsed, self.now, [], use_llm=False))

        with patch("app.agents.schedule.llm_client", FailingLlm(), create=True):
            schedule = asyncio.run(run_schedule(parsed, priority, self.now, horizon_days=1))

        self.assertEqual(len(schedule.slot_proposals), 1)
        self.assertEqual(len(schedule.slot_proposals[0].candidate_slots), 1)
        self.assertEqual(schedule.slot_proposals[0].rerank_source, "deterministic")
        self.assertEqual(getattr(schedule, "_agent_meta")["rerank_calls"], 0)

    def test_schedule_rejects_invalid_llm_rerank_and_keeps_deterministic_selection(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot
        from app.services.metrics import llm_safety_summary, reset_llm_safety_metrics

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [0, 99],
                            "selected_index": 99,
                            "rationale": "존재하지 않는 슬롯을 선택합니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        reset_llm_safety_metrics()

        with patch("app.agents.schedule.llm_client", FakeLlm()):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        proposal = schedule.slot_proposals[0]
        self.assertEqual(proposal.selected_index, 0)
        self.assertEqual(proposal.rerank_source, "deterministic")
        self.assertIn("rerank_violation:task_ALPHA001", schedule.warnings)
        self.assertEqual(llm_safety_summary()["by_purpose"]["schedule_rerank"]["blocked"], 2)

    def test_schedule_retries_once_after_invalid_llm_rerank(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            def __init__(self):
                self.rerank_calls = 0

            async def chat_json(self, **_):
                self.rerank_calls += 1
                if self.rerank_calls == 1:
                    return {
                        "rerankings": [
                            {
                                "task_id": "task_ALPHA001",
                                "ranked_indices": [0, 99],
                                "selected_index": 99,
                                "rationale": "존재하지 않는 슬롯입니다.",
                            }
                        ]
                    }
                return {
                    "rerankings": [
                        {
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [1, 0, 2],
                            "selected_index": 1,
                            "rationale": "두 번째 후보가 오후 검토 시간과 더 잘 맞습니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        fake = FakeLlm()

        with patch("app.agents.schedule.llm_client", fake, create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertEqual(fake.rerank_calls, 2)
        self.assertEqual(getattr(schedule, "_agent_meta")["rerank_calls"], 2)
        self.assertEqual(schedule.slot_proposals[0].selected_index, 1)
        self.assertEqual(schedule.slot_proposals[0].rerank_source, "llm_reranked")

    def test_schedule_falls_back_when_llm_rerank_times_out(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        class TimeoutLlm:
            configured = True

            async def chat_json(self, **_):
                raise TimeoutError("rerank timed out")

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))

        with patch("app.agents.schedule.llm_client", TimeoutLlm(), create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertEqual(schedule.slot_proposals[0].selected_index, 0)
        self.assertEqual(schedule.slot_proposals[0].rerank_source, "deterministic")
        self.assertIn("schedule_rerank_timeout", schedule.warnings)
        self.assertEqual(getattr(schedule, "_agent_meta")["rerank_calls"], 2)

    def test_schedule_rejects_forbidden_llm_rerank_rationale(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot
        from app.services.metrics import policy_violation_summary, reset_policy_violation_metrics

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "rerankings": [
                        {
                            "task_id": "task_ALPHA001",
                            "ranked_indices": [1, 0, 2],
                            "selected_index": 1,
                            "rationale": "담당자 성격 때문에 이 시간이 낫습니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        reset_policy_violation_metrics()

        with patch("app.agents.schedule.llm_client", FakeLlm(), create=True):
            schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))

        self.assertEqual(schedule.slot_proposals[0].selected_index, 0)
        self.assertEqual(schedule.slot_proposals[0].rerank_source, "deterministic")
        self.assertIn("rerank_violation:task_ALPHA001", schedule.warnings)
        self.assertEqual(policy_violation_summary()["by_filter"]["forbidden_word"], 2)

    def test_schedule_reports_no_capacity_before_deadline_for_occupied_one_day_task(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        snapshot["tasks"][0]["estimated_hours"] = 8
        snapshot["tasks"][0]["deadline"] = self.now.replace(hour=18).isoformat()
        snapshot["calendar_events"] = [
            {
                "event_id": "evt_BUSY0001",
                "project_id": "proj_ABCDEF12",
                "task_id": "task_ALPHA001",
                "assignee_id": "mem_ALPHA1",
                "starts_at": self.now.replace(hour=13).isoformat(),
                "ends_at": self.now.replace(hour=17).isoformat(),
                "approved": True,
                "approved_at": self.now.isoformat(),
                "source": "external_blocking",
            }
        ]

        model = ProjectSnapshot(**snapshot)
        priority = asyncio.run(run_priority(model, self.now, []))
        schedule = asyncio.run(run_schedule(model, priority, self.now, horizon_days=1))

        self.assertEqual(schedule.unschedulable[0].task_id, "task_ALPHA001")
        self.assertIn("no_capacity_before_deadline", schedule.unschedulable[0].reasons)
        self.assertEqual(schedule.slot_proposals, [])

    def test_schedule_uses_later_member_window_when_first_window_is_too_short(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        snapshot = self._snapshot()
        snapshot["members"][0]["available_hours"] = [
            {"day_of_week": self.now.weekday(), "start": "09:00", "end": "10:00"},
            {"day_of_week": self.now.weekday(), "start": "14:00", "end": "18:00"},
        ]
        snapshot["tasks"][0]["estimated_hours"] = 2
        snapshot["tasks"][0]["deadline"] = self.now.replace(hour=18).isoformat()
        model = ProjectSnapshot(**snapshot)
        priority = asyncio.run(run_priority(model, self.now, []))

        schedule = asyncio.run(run_schedule(model, priority, self.now, horizon_days=1))

        self.assertEqual(schedule.unschedulable, [])
        slot = schedule.slot_proposals[0].candidate_slots[0]
        self.assertEqual(slot.starts_at.hour, 14)
        self.assertEqual(slot.ends_at.hour, 16)

    def test_schedule_falls_back_to_project_weekend_window_when_member_has_no_weekend_hours(self):
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import ProjectSnapshot

        saturday = datetime(2026, 5, 9, 9, 0, tzinfo=timezone(timedelta(hours=9)))
        snapshot = self._snapshot()
        snapshot["project"]["default_working_hours"]["weekend"] = {
            "start": "11:00",
            "end": "15:00",
            "enabled": True,
        }
        snapshot["members"][0]["available_hours"] = [
            {"day_of_week": day, "start": "09:00", "end": "18:00"}
            for day in range(5)
        ]
        snapshot["tasks"][0]["estimated_hours"] = 2
        snapshot["tasks"][0]["deadline"] = saturday.replace(hour=18).isoformat()
        model = ProjectSnapshot(**snapshot)
        priority = asyncio.run(run_priority(model, saturday, []))

        schedule = asyncio.run(run_schedule(model, priority, saturday, horizon_days=1))

        self.assertEqual(schedule.unschedulable, [])
        slot = schedule.slot_proposals[0].candidate_slots[0]
        self.assertEqual(slot.starts_at.weekday(), 5)
        self.assertEqual(slot.starts_at.hour, 11)
        self.assertEqual(slot.ends_at.hour, 13)

    def test_orchestrator_exports_langgraph_super_graph(self):
        from app.orchestrator import SUPER_GRAPH

        self.assertTrue(hasattr(SUPER_GRAPH, "ainvoke"))

    def test_agent_modules_export_compiled_langgraph_subgraphs(self):
        from app.agents import priority_subgraph, risk_subgraph, schedule_subgraph
        from app.schemas import ProjectSnapshot

        self.assertTrue(hasattr(priority_subgraph, "ainvoke"))
        self.assertTrue(hasattr(schedule_subgraph, "ainvoke"))
        self.assertTrue(hasattr(risk_subgraph, "ainvoke"))

        snapshot = ProjectSnapshot(**self._snapshot())
        priority_state = asyncio.run(
            priority_subgraph.ainvoke(
                {
                    "snapshot": snapshot,
                    "now": self.now,
                    "request_decomposition_for": [],
                    "use_llm": False,
                }
            )
        )
        schedule_state = asyncio.run(
            schedule_subgraph.ainvoke(
                {
                    "snapshot": snapshot,
                    "priority": priority_state["priority"],
                    "now": self.now,
                    "horizon_days": 14,
                }
            )
        )
        risk_state = asyncio.run(
            risk_subgraph.ainvoke(
                {
                    "snapshot": snapshot,
                    "priority": priority_state["priority"],
                    "schedule": schedule_state["schedule"],
                    "now": self.now,
                    "use_llm": False,
                }
            )
        )

        self.assertGreater(len(priority_state["priority"].tasks_priority), 0)
        self.assertGreater(len(schedule_state["schedule"].slot_proposals), 0)
        self.assertEqual(len(risk_state["risk"].checks), 3)

    def test_orchestrator_agent_nodes_invoke_compiled_subgraphs(self):
        from types import SimpleNamespace

        from app import orchestrator
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import AnalyzeOptions, ProjectSnapshot

        class FakePrioritySubgraph:
            async def ainvoke(self, state):
                return {"priority": SimpleNamespace(agent_meta=SimpleNamespace(schema_retries=7))}

        class FakeScheduleSubgraph:
            async def ainvoke(self, state):
                return {"schedule": SimpleNamespace()}

        class FakeRiskSubgraph:
            async def ainvoke(self, state):
                return {"risk": SimpleNamespace()}

        snapshot = ProjectSnapshot(**self._snapshot())
        real_priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        real_schedule = asyncio.run(run_schedule(snapshot, real_priority, self.now, horizon_days=14))
        base_state = {
            "project_id": "proj_ABCDEF12",
            "snapshot": snapshot,
            "options": AnalyzeOptions(schedule_horizon_days=14),
            "now": self.now,
            "snapshot_hash": "hash_test",
            "agent_latencies_ms": {},
        }
        original_priority = orchestrator.priority_subgraph
        original_schedule = orchestrator.schedule_subgraph
        original_risk = orchestrator.risk_subgraph
        try:
            orchestrator.priority_subgraph = FakePrioritySubgraph()
            priority_state = asyncio.run(orchestrator._priority_node(base_state))
            self.assertEqual(priority_state["priority"].agent_meta.schema_retries, 7)

            orchestrator.schedule_subgraph = FakeScheduleSubgraph()
            schedule_state = asyncio.run(orchestrator._schedule_node({**base_state, "priority": real_priority}))
            self.assertIsInstance(schedule_state["schedule"], SimpleNamespace)

            orchestrator.risk_subgraph = FakeRiskSubgraph()
            risk_state = asyncio.run(
                orchestrator._risk_node({**base_state, "priority": real_priority, "schedule": real_schedule})
            )
            self.assertIsInstance(risk_state["risk"], SimpleNamespace)
        finally:
            orchestrator.priority_subgraph = original_priority
            orchestrator.schedule_subgraph = original_schedule
            orchestrator.risk_subgraph = original_risk

    def test_orchestrator_overlaps_schedule_with_risk_soft_lane(self):
        from app import orchestrator
        from app.agents.priority import run_priority
        from app.agents.schedule import run_schedule
        from app.schemas import AnalyzeOptions, ProjectSnapshot

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, [], use_llm=False))
        real_schedule = asyncio.run(run_schedule(snapshot, priority, self.now, horizon_days=14))
        schedule_running = False
        soft_started_while_schedule_running = False

        class SlowScheduleSubgraph:
            async def ainvoke(self, _):
                nonlocal schedule_running
                schedule_running = True
                await asyncio.sleep(0.03)
                schedule_running = False
                return {"schedule": real_schedule}

        class SoftLaneLlm:
            configured = True

            async def chat_json(self, **kwargs):
                nonlocal soft_started_while_schedule_running
                if "Find soft project risks" in kwargs["system"]:
                    soft_started_while_schedule_running = schedule_running
                    await asyncio.sleep(0.01)
                    return {"soft_checks": []}
                return {"summary": "현재 결정적 blocker는 없습니다."}

        original_schedule = orchestrator.schedule_subgraph
        try:
            orchestrator.schedule_subgraph = SlowScheduleSubgraph()
            with patch("app.agents.risk.llm_client", SoftLaneLlm(), create=True):
                asyncio.run(
                    orchestrator.analyze_snapshot(
                        project_id="proj_ABCDEF12",
                        snapshot=snapshot,
                        options=AnalyzeOptions(),
                        now=self.now,
                    )
                )
        finally:
            orchestrator.schedule_subgraph = original_schedule

        self.assertTrue(soft_started_while_schedule_running)

    def test_risk_includes_valid_llm_soft_checks_when_configured(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **_):
                return {
                    "soft_checks": [
                        {
                            "id": "S1",
                            "trigger_label": "implicit_dependency_suspected",
                            "confidence": 0.81,
                            "involved_task_ids": ["task_ALPHA001"],
                            "supporting_facts": ["task_ALPHA001.title='FastAPI API Gateway 구현'"],
                            "suggested_action": None,
                            "user_facing_text": "API 작업에 암묵적 선행 관계 확인이 필요합니다.",
                        }
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))

        with patch("app.agents.risk.llm_client", FakeLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertTrue(any(check.id == "S1" for check in risk.soft_checks))

    def test_risk_filters_invalid_llm_soft_checks(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot
        from app.services.metrics import (
            llm_safety_summary,
            policy_violation_summary,
            reset_llm_safety_metrics,
            reset_policy_violation_metrics,
        )

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": "현재 결정적 blocker는 없습니다."}
                return {
                    "soft_checks": [
                        {
                            "id": "S1",
                            "trigger_label": "implicit_dependency_suspected",
                            "confidence": 0.3,
                            "involved_task_ids": ["task_ALPHA001"],
                            "supporting_facts": ["confidence가 낮은 항목"],
                            "suggested_action": None,
                            "user_facing_text": "낮은 confidence 항목입니다.",
                        },
                        {
                            "id": "S1",
                            "trigger_label": "implicit_dependency_suspected",
                            "confidence": 0.81,
                            "involved_task_ids": ["task_DOESNOTEXIST"],
                            "supporting_facts": ["존재하지 않는 task_id"],
                            "suggested_action": None,
                            "user_facing_text": "환각 task_id 항목입니다.",
                        },
                        {
                            "id": "S4",
                            "trigger_label": "task_definition_too_vague",
                            "confidence": 0.76,
                            "involved_task_ids": ["task_ALPHA001"],
                            "supporting_facts": ["금지어 포함 항목"],
                            "suggested_action": None,
                            "user_facing_text": "담당자 성격 때문에 위험합니다.",
                        },
                        {
                            "id": "S3",
                            "trigger_label": "unsupported_soft_risk_label",
                            "confidence": 0.82,
                            "involved_task_ids": ["task_ALPHA001"],
                            "supporting_facts": ["문서 계약에 없는 trigger_label"],
                            "suggested_action": None,
                            "user_facing_text": "문서 계약에 없는 라벨입니다.",
                        },
                        {
                            "id": "S5",
                            "trigger_label": "duplicate_task_suspected",
                            "confidence": 0.79,
                            "involved_task_ids": ["task_ALPHA001"],
                            "supporting_facts": ["task_ALPHA001.title='FastAPI API Gateway 구현'"],
                            "suggested_action": None,
                            "user_facing_text": "Task 중복 가능성을 PM이 확인해야 합니다.",
                        },
                    ]
                }

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        reset_llm_safety_metrics()
        reset_policy_violation_metrics()

        with patch("app.agents.risk.llm_client", FakeLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertEqual([check.id for check in risk.soft_checks], ["S5"])
        self.assertNotIn("성격", risk.soft_checks[0].user_facing_text)
        self.assertEqual(risk.blockers_failed, [])
        self.assertEqual(policy_violation_summary()["by_filter"]["forbidden_word"], 1)
        safety = llm_safety_summary()["by_purpose"]["risk_soft_checks"]
        self.assertEqual(safety["passed"], 1)
        self.assertEqual(safety["blocked_by_reason"]["low_confidence"], 1)
        self.assertEqual(safety["blocked_by_reason"]["hallucinated_task_id"], 1)
        self.assertEqual(safety["blocked_by_reason"]["forbidden_word"], 1)
        self.assertEqual(safety["blocked_by_reason"]["schema_invalid"], 1)

    def test_risk_records_schema_failure_for_invalid_soft_check_payload(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot
        from app.services.metrics import llm_schema_summary, reset_llm_schema_metrics

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": "현재 결정적 blocker는 없습니다."}
                return {"not_soft_checks": []}

        reset_llm_schema_metrics()
        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))

        with patch("app.agents.risk.llm_client", FakeLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertEqual(risk.soft_checks, [])
        self.assertEqual(llm_schema_summary()["by_purpose"]["risk_soft_checks"]["failed"], 1)

    def test_risk_soft_checks_timeout_returns_empty_soft_lane(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot
        from app.services.metrics import llm_safety_summary, reset_llm_safety_metrics

        class TimeoutLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": "현재 결정적 blocker는 없습니다."}
                raise TimeoutError("soft checks timed out")

        reset_llm_safety_metrics()
        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))

        with patch("app.agents.risk.llm_client", TimeoutLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertEqual(risk.soft_checks, [])
        self.assertEqual(risk.summary, "현재 결정적 blocker는 없습니다. 실패한 보조 체크가 있으면 제안 카드를 검토하세요.")
        self.assertEqual(llm_safety_summary()["by_purpose"]["risk_soft_checks"]["blocked_by_reason"]["timeout"], 1)

    def test_risk_uses_valid_llm_narrator_summary_when_configured(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": "마감일까지 완료 가능성 체크가 실패했고 일정 조정이 필요합니다."}
                return {"soft_checks": []}

        payload = self._snapshot()
        payload["tasks"][0]["deadline"] = (self.now - timedelta(days=1)).isoformat()
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, []))

        with patch("app.agents.risk.llm_client", FakeLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertEqual(risk.summary, "마감일까지 완료 가능성 체크가 실패했고 일정 조정이 필요합니다.")

    def test_risk_retries_once_after_forbidden_llm_narrator_summary(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot
        from app.services.metrics import policy_violation_summary, reset_policy_violation_metrics

        class FakeLlm:
            configured = True

            def __init__(self):
                self.narrator_calls = 0

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" not in kwargs["system"]:
                    return {"soft_checks": []}
                self.narrator_calls += 1
                if self.narrator_calls == 1:
                    return {"summary": "담당자 성격 때문에 위험합니다."}
                return {"summary": "마감일까지 완료 가능성 체크가 실패했고 일정 조정이 필요합니다."}

        payload = self._snapshot()
        payload["tasks"][0]["deadline"] = (self.now - timedelta(days=1)).isoformat()
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        fake = FakeLlm()
        reset_policy_violation_metrics()

        with patch("app.agents.risk.llm_client", fake, create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertEqual(fake.narrator_calls, 2)
        self.assertEqual(getattr(risk, "_agent_meta")["narrator_calls"], 2)
        self.assertNotIn("성격", risk.summary)
        self.assertIn("마감일까지 완료 가능성 체크", risk.summary)
        self.assertEqual(policy_violation_summary()["by_filter"]["forbidden_word"], 1)

    def test_risk_rejects_llm_narrator_numbers_not_present_in_facts(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": "담당자 부하 체크가 실패했고 utilization 999%입니다."}
                return {"soft_checks": []}

        payload = self._snapshot()
        payload["tasks"][0]["deadline"] = (self.now - timedelta(days=1)).isoformat()
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, []))

        with patch("app.agents.risk.llm_client", FakeLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertNotIn("999", risk.summary)
        self.assertIn("마감일까지 완료 가능성 체크", risk.summary)
        self.assertEqual(getattr(risk, "_agent_meta")["narrator_calls"], 2)

    def test_risk_rejects_llm_narrator_summary_over_contract_limit(self):
        from app.agents.priority import run_priority
        from app.agents.risk import RISK_NARRATOR_SUMMARY_MAX_CHARS, run_risk
        from app.schemas import ProjectSnapshot

        oversized_summary = "가" * (RISK_NARRATOR_SUMMARY_MAX_CHARS + 1)

        class FakeLlm:
            configured = True

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    return {"summary": oversized_summary}
                return {"soft_checks": []}

        payload = self._snapshot()
        payload["tasks"][0]["deadline"] = (self.now - timedelta(days=1)).isoformat()
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, []))

        with patch("app.agents.risk.llm_client", FakeLlm(), create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertNotEqual(risk.summary, oversized_summary)
        self.assertIn("마감일까지 완료 가능성 체크", risk.summary)
        self.assertEqual(getattr(risk, "_agent_meta")["narrator_calls"], 2)

    def test_risk_skips_llm_narrator_when_checks_pass(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot

        invented_summary = "담당자 부하 체크가 실패했고 담당자 지정 보완이 필요합니다."

        class FakeLlm:
            configured = True
            narrator_calls = 0

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    self.narrator_calls += 1
                    return {"summary": invented_summary}
                return {"soft_checks": []}

        snapshot = ProjectSnapshot(**self._snapshot())
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        fake = FakeLlm()

        with patch("app.agents.risk.llm_client", fake, create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertNotEqual(risk.summary, invented_summary)
        self.assertIn("현재 결정적 blocker", risk.summary)
        self.assertEqual(fake.narrator_calls, 0)
        self.assertEqual(getattr(risk, "_agent_meta")["narrator_calls"], 0)

    def test_risk_rejects_empty_or_non_string_llm_narrator_summary(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot

        invalid_payloads = [
            {"summary": ""},
            {"summary": "   "},
            {"summary": 123},
            {},
        ]

        for invalid_payload in invalid_payloads:
            with self.subTest(invalid_payload=invalid_payload):
                class FakeLlm:
                    configured = True

                    async def chat_json(self, **kwargs):
                        if "summarize deterministic project risk facts" in kwargs["system"]:
                            return invalid_payload
                        return {"soft_checks": []}

                payload = self._snapshot()
                payload["tasks"][0]["deadline"] = (self.now - timedelta(days=1)).isoformat()
                snapshot = ProjectSnapshot(**payload)
                priority = asyncio.run(run_priority(snapshot, self.now, []))

                with patch("app.agents.risk.llm_client", FakeLlm(), create=True):
                    risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

                self.assertIn("마감일까지 완료 가능성 체크", risk.summary)
                self.assertEqual(getattr(risk, "_agent_meta")["narrator_calls"], 2)

    def test_risk_rejects_forbidden_llm_narrator_summary(self):
        from app.agents.priority import run_priority
        from app.agents.risk import run_risk
        from app.schemas import ProjectSnapshot

        class FakeLlm:
            configured = True
            narrator_calls = 0

            async def chat_json(self, **kwargs):
                if "summarize deterministic project risk facts" in kwargs["system"]:
                    self.narrator_calls += 1
                    return {"summary": "담당자 성격 때문에 위험합니다."}
                return {"soft_checks": []}

        payload = self._snapshot()
        payload["tasks"][0]["deadline"] = (self.now - timedelta(days=1)).isoformat()
        snapshot = ProjectSnapshot(**payload)
        priority = asyncio.run(run_priority(snapshot, self.now, []))
        fake = FakeLlm()

        with patch("app.agents.risk.llm_client", fake, create=True):
            risk = asyncio.run(run_risk(snapshot, priority, None, self.now))

        self.assertNotIn("성격", risk.summary)
        self.assertIn("마감일까지 완료 가능성 체크", risk.summary)
        self.assertEqual(fake.narrator_calls, 2)
        self.assertEqual(getattr(risk, "_agent_meta")["narrator_calls"], 2)


if __name__ == "__main__":
    unittest.main()
