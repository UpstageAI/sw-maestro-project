import sys
import unittest
from unittest.mock import MagicMock, patch

from daily_news_agent.models import BriefingResult, CollectionResult, NewsArticle


def _make_article(keyword="AI"):
    return NewsArticle(
        title="AI 뉴스",
        summary="요약",
        link="https://example.com/ai",
        source="Example",
        published_at="2026-05-09",
        keyword=keyword,
    )


def _make_collection_result():
    return CollectionResult(
        interest="AI 산업",
        keywords=["AI"],
        collected_articles=[_make_article()],
        collected_count=1,
        stored_count=1,
        skipped_existing_count=0,
        errors=[],
    )


def _make_briefing_result():
    return BriefingResult(
        interest="AI 산업",
        keywords=["AI"],
        collected_count=1,
        stored_count=1,
        skipped_existing_count=0,
        selected_articles=[_make_article()],
        briefing_markdown="## 브리핑",
        errors=[],
    )


def _run_main(args: list[str]) -> int:
    from run_daily import main

    with patch("sys.argv", ["run_daily.py"] + args):
        return main()


class RunDailyExitCodeTests(unittest.TestCase):
    @patch("run_daily._create_workflow")
    def test_exits_zero_on_success(self, mock_create_workflow):
        mock_workflow = MagicMock()
        mock_workflow.collect_and_store.return_value = _make_collection_result()
        mock_workflow.generate_briefing.return_value = _make_briefing_result()
        mock_create_workflow.return_value = mock_workflow

        result = _run_main(["--interest", "AI 산업", "--keywords", "AI", "--no-mail"])

        self.assertEqual(result, 0)

    @patch("run_daily._create_workflow")
    def test_exits_one_on_workflow_error(self, mock_create_workflow):
        mock_create_workflow.side_effect = RuntimeError("연결 실패")

        result = _run_main(["--interest", "AI 산업", "--keywords", "AI", "--no-mail"])

        self.assertEqual(result, 1)

    @patch("run_daily._create_workflow")
    def test_skips_mail_when_no_mail_flag(self, mock_create_workflow):
        mock_workflow = MagicMock()
        mock_workflow.collect_and_store.return_value = _make_collection_result()
        mock_workflow.generate_briefing.return_value = _make_briefing_result()
        mock_create_workflow.return_value = mock_workflow

        with patch("run_daily.SMTPMailClient") as mock_smtp:
            result = _run_main(
                ["--interest", "AI 산업", "--keywords", "AI", "--no-mail", "--recipient", "test@example.com"]
            )

        self.assertEqual(result, 0)
        mock_smtp.assert_not_called()

    @patch("run_daily._create_workflow")
    def test_sends_mail_when_recipient_given(self, mock_create_workflow):
        mock_workflow = MagicMock()
        mock_workflow.collect_and_store.return_value = _make_collection_result()
        mock_workflow.generate_briefing.return_value = _make_briefing_result()
        mock_create_workflow.return_value = mock_workflow

        mock_settings = MagicMock()
        mock_settings.per_keyword_limit = 3
        mock_settings.top_k = 5
        mock_settings.email_to_default = ""
        mock_settings.email_from = "sender@gmail.com"
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "sender@gmail.com"
        mock_settings.smtp_password = "password"
        mock_settings.smtp_use_tls = True
        mock_settings.smtp_use_ssl = False
        mock_settings.request_timeout_seconds = 10

        with patch("run_daily.Settings.from_env", return_value=mock_settings), \
             patch("run_daily.SMTPMailClient") as mock_smtp_cls:
            mock_smtp_cls.return_value.send = MagicMock()
            result = _run_main(
                ["--interest", "AI 산업", "--keywords", "AI", "--recipient", "recv@example.com"]
            )

        self.assertEqual(result, 0)
        mock_smtp_cls.return_value.send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
