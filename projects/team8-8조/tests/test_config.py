import unittest
from unittest.mock import patch

from daily_news_agent.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_limit_api_work_for_local_demo(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings.from_env(load_env=False)

        self.assertEqual(settings.per_keyword_limit, 3)
        self.assertEqual(settings.top_k, 5)
        self.assertEqual(settings.upstage_base_url, "https://api.upstage.ai/v1")
        self.assertEqual(settings.upstage_chat_model, "solar-pro3")
        self.assertEqual(settings.email_mode, "demo")
        self.assertEqual(settings.email_outbox_path, "data/outbox")
        self.assertEqual(settings.smtp_port, 587)
        self.assertTrue(settings.smtp_use_tls)
        self.assertFalse(settings.smtp_use_ssl)

    def test_validate_mail_settings_allows_demo_mode_without_smtp_values(self):
        with patch.dict("os.environ", {"EMAIL_MODE": "demo"}, clear=True):
            settings = Settings.from_env(load_env=False)

        settings.validate_mail_settings()

    def test_validate_mail_settings_requires_required_smtp_fields(self):
        with patch.dict("os.environ", {"EMAIL_MODE": "smtp"}, clear=True):
            settings = Settings.from_env(load_env=False)

        with self.assertRaisesRegex(ValueError, "EMAIL_FROM"):
            settings.validate_mail_settings()

    def test_validate_mail_settings_accepts_gmail_tls_defaults(self):
        with patch.dict(
            "os.environ",
            {
                "EMAIL_MODE": "smtp",
                "EMAIL_FROM": "sender@gmail.com",
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": "587",
                "SMTP_USERNAME": "sender@gmail.com",
                "SMTP_PASSWORD": "app-password",
                "SMTP_USE_TLS": "true",
                "SMTP_USE_SSL": "false",
            },
            clear=True,
        ):
            settings = Settings.from_env(load_env=False)

        settings.validate_mail_settings()

    def test_validate_mail_settings_rejects_invalid_gmail_tls_port(self):
        with patch.dict(
            "os.environ",
            {
                "EMAIL_MODE": "smtp",
                "EMAIL_FROM": "sender@gmail.com",
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": "465",
                "SMTP_USERNAME": "sender@gmail.com",
                "SMTP_PASSWORD": "app-password",
                "SMTP_USE_TLS": "true",
                "SMTP_USE_SSL": "false",
            },
            clear=True,
        ):
            settings = Settings.from_env(load_env=False)

        with self.assertRaisesRegex(ValueError, "587"):
            settings.validate_mail_settings()

    def test_naver_credentials_default_to_empty_strings(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings.from_env(load_env=False)

        self.assertEqual(settings.naver_client_id, "")
        self.assertEqual(settings.naver_client_secret, "")

    def test_naver_credentials_loaded_from_environment(self):
        with patch.dict(
            "os.environ",
            {"NAVER_CLIENT_ID": " id-123 ", "NAVER_CLIENT_SECRET": " secret-xyz "},
            clear=True,
        ):
            settings = Settings.from_env(load_env=False)

        self.assertEqual(settings.naver_client_id, "id-123")
        self.assertEqual(settings.naver_client_secret, "secret-xyz")

    def test_validate_mail_settings_rejects_tls_and_ssl_enabled_together(self):
        with patch.dict(
            "os.environ",
            {
                "EMAIL_MODE": "smtp",
                "EMAIL_FROM": "sender@gmail.com",
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": "465",
                "SMTP_USERNAME": "sender@gmail.com",
                "SMTP_PASSWORD": "app-password",
                "SMTP_USE_TLS": "true",
                "SMTP_USE_SSL": "true",
            },
            clear=True,
        ):
            settings = Settings.from_env(load_env=False)

        with self.assertRaisesRegex(ValueError, "동시에 true"):
            settings.validate_mail_settings()


if __name__ == "__main__":
    unittest.main()
