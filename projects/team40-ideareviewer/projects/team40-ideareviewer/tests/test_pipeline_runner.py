import os
import unittest
from unittest.mock import patch

from services.pipeline_runner import (
    NODE_LABELS,
    compose_review_input,
    get_langsmith_status,
    make_pipeline_event,
    stream_pipeline,
)


class PipelineRunnerTests(unittest.TestCase):
    def test_compose_review_input_includes_form_fields(self) -> None:
        raw_input = compose_review_input(
            service_name="시니어 케어",
            stage="아이디어",
            focus_areas=["사용성", "신뢰"],
            description="병원 예약과 복약 알림을 돕는 서비스입니다.",
        )

        self.assertIn("서비스 이름: 시니어 케어", raw_input)
        self.assertIn("현재 단계: 아이디어", raw_input)
        self.assertIn("중점 검토 항목: 사용성, 신뢰", raw_input)
        self.assertIn("기획 설명:", raw_input)
        self.assertIn("병원 예약", raw_input)

    def test_make_pipeline_event_uses_user_facing_label_and_non_null_keys(self) -> None:
        event = make_pipeline_event(
            "f0_parse",
            {"brief": object(), "ignored": None},
        )

        self.assertEqual(event.node_name, "f0_parse")
        self.assertEqual(event.label, NODE_LABELS["f0_parse"])
        self.assertEqual(event.update_keys, ["brief"])

    def test_stream_pipeline_uses_injected_streamer_without_importing_graph(self) -> None:
        calls = []

        def fake_streamer(payload, *, stream_mode):
            calls.append((payload, stream_mode))
            yield {"f0_parse": {"brief": "parsed"}}
            yield {"supervisor_finalize": {"final_review_text": "done"}}

        events = list(stream_pipeline("raw idea", graph_streamer=fake_streamer))

        self.assertEqual(calls, [({"raw_input": "raw idea"}, "updates")])
        self.assertEqual([event.node_name for event in events], ["f0_parse", "supervisor_finalize"])
        self.assertEqual(events[-1].update["final_review_text"], "done")

    def test_stream_pipeline_rejects_empty_input(self) -> None:
        with self.assertRaises(ValueError):
            list(stream_pipeline("   ", graph_streamer=lambda *_args, **_kwargs: []))

    def test_get_langsmith_status_reads_environment(self) -> None:
        clean_env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("LANGSMITH_")
        }
        clean_env.update(
            {
                "LANGSMITH_TRACING": "true",
                "LANGSMITH_PROJECT": "demo-project",
                "LANGSMITH_ENDPOINT": "https://example.test",
                "LANGSMITH_API_KEY": "test-key",
            }
        )

        with patch.dict(os.environ, clean_env, clear=True):
            status = get_langsmith_status()

        self.assertTrue(status.tracing_enabled)
        self.assertEqual(status.project, "demo-project")
        self.assertEqual(status.endpoint, "https://example.test")
        self.assertTrue(status.has_api_key)


if __name__ == "__main__":
    unittest.main()
