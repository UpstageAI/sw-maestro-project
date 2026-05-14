import unittest
from unittest.mock import patch

from daily_news_agent.mail_sender import (
    EmailMessagePayload,
    MailDeliveryError,
    SMTPMailClient,
    build_briefing_email_payload,
    build_email_message,
)
from daily_news_agent.models import BriefingResult, NewsArticle


def make_payload() -> EmailMessagePayload:
    return EmailMessagePayload(
        subject="데일리 뉴스 브리핑",
        plain_text="오늘의 핵심 뉴스입니다.",
        html_text="<h1>오늘의 핵심 뉴스입니다.</h1>",
        sender="sender@example.com",
        recipients=["first@example.com", "second@example.com"],
    )


class MailSenderTests(unittest.TestCase):
    def test_build_email_message_sets_headers_and_alternatives(self) -> None:
        message = build_email_message(make_payload())

        self.assertEqual(message["Subject"], "데일리 뉴스 브리핑")
        self.assertEqual(message["From"], "sender@example.com")
        self.assertEqual(message["To"], "first@example.com, second@example.com")
        self.assertEqual(message.get_body(("plain",)).get_content().strip(), "오늘의 핵심 뉴스입니다.")
        self.assertEqual(message.get_body(("html",)).get_content().strip(), "<h1>오늘의 핵심 뉴스입니다.</h1>")

    def test_build_briefing_email_payload_includes_briefing_and_article_links(self) -> None:
        briefing_result = BriefingResult(
            interest="AI 산업 동향",
            keywords=["AI"],
            collected_count=3,
            stored_count=2,
            selected_articles=[
                NewsArticle(
                    title="AI 투자 확대",
                    summary="투자 소식 요약",
                    link="https://example.com/ai-investment",
                    source="Example",
                    published_at="2026-05-08",
                    keyword="AI",
                )
            ],
            briefing_markdown="## 오늘의 뉴스 요약\n- AI 투자 확대",
            errors=["RSS timeout"],
            skipped_existing_count=1,
        )

        payload = build_briefing_email_payload(
            briefing_result=briefing_result,
            sender="sender@example.com",
            recipient="recipient@example.com",
        )

        self.assertEqual(payload.subject, "Daily News Agent 브리핑 - AI 산업 동향")
        self.assertEqual(payload.sender, "sender@example.com")
        self.assertEqual(payload.recipients, ["recipient@example.com"])
        self.assertIn("## 오늘의 뉴스 요약", payload.plain_text)
        self.assertIn("https://example.com/ai-investment", payload.plain_text)
        self.assertIn("RSS timeout", payload.plain_text)

    @patch("daily_news_agent.mail_sender.smtplib.SMTP")
    def test_smtp_mail_client_uses_starttls_login_and_send(self, smtp_class) -> None:
        smtp_instance = smtp_class.return_value.__enter__.return_value
        client = SMTPMailClient(
            host="smtp.example.com",
            port=587,
            username="user",
            password="pass",
            use_tls=True,
            use_ssl=False,
            timeout_seconds=15,
        )

        client.send(make_payload())

        smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=15)
        smtp_instance.starttls.assert_called_once_with()
        smtp_instance.login.assert_called_once_with("user", "pass")
        smtp_instance.send_message.assert_called_once()

    @patch("daily_news_agent.mail_sender.smtplib.SMTP")
    def test_smtp_mail_client_wraps_delivery_failures(self, smtp_class) -> None:
        smtp_instance = smtp_class.return_value.__enter__.return_value
        smtp_instance.send_message.side_effect = OSError("network down")
        client = SMTPMailClient(host="smtp.example.com", port=587)

        with self.assertRaises(MailDeliveryError):
            client.send(make_payload())


if __name__ == "__main__":
    unittest.main()
