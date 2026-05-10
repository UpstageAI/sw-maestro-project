"""Secret Scanner 단위 테스트 — 수정된 패턴(@ 등 특수문자) 포함."""
import pytest
from src.tools.secret_scanner import redact_secrets


class TestRedactAPIKey:
    def test_api_key_pattern_redacted(self):
        text = 'api_key = "abcdefghijklmnopqrstuvwxyz12345"'
        assert "abcdefghijklmnopqrstuvwxyz12345" not in redact_secrets(text)
        assert "REDACTED" in redact_secrets(text)

    def test_secret_pattern_redacted(self):
        text = 'secret: "mysupersecretvalue123456789012"'
        assert "mysupersecretvalue123456789012" not in redact_secrets(text)

    def test_token_pattern_redacted(self):
        text = 'token = "abcdefghijklmnopqrstuvwxyz1234"'
        assert "abcdefghijklmnopqrstuvwxyz1234" not in redact_secrets(text)

    def test_password_with_at_sign_redacted(self):
        # Issue 1 수정 후: @ 포함 패스워드도 감지
        text = 'password = "MyP@ssword_SuperSecret1234"'
        assert "MyP@ssword_SuperSecret1234" not in redact_secrets(text)

    def test_password_alphanum_redacted(self):
        text = 'password = "MyPassword_SuperSecretLong1234"'
        assert "MyPassword_SuperSecretLong1234" not in redact_secrets(text)


class TestRedactBearerToken:
    def test_bearer_token_redacted(self):
        # Issue 1 수정 후: Bearer 형식 토큰 감지
        text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz1234"
        result = redact_secrets(text)
        assert "abcdefghijklmnopqrstuvwxyz1234" not in result
        assert "REDACTED" in result

    def test_bearer_token_case_insensitive(self):
        text = "authorization: bearer AbCdEfGhIjKlMnOpQrStUvWxYz12345"
        result = redact_secrets(text)
        assert "AbCdEfGhIjKlMnOpQrStUvWxYz12345" not in result


class TestRedactKnownKeyFormats:
    def test_sk_prefix_key_redacted(self):
        text = "key = sk-" + "A" * 32
        assert "sk-" + "A" * 32 not in redact_secrets(text)

    def test_github_pat_redacted(self):
        text = "github_token = ghp_" + "B" * 30
        assert "ghp_" + "B" * 30 not in redact_secrets(text)

    def test_aws_access_key_redacted(self):
        text = "aws_key = AKIA" + "C" * 16
        assert "AKIA" + "C" * 16 not in redact_secrets(text)

    def test_google_api_key_redacted(self):
        text = "key = AIza" + "D" * 30
        assert "AIza" + "D" * 30 not in redact_secrets(text)

    def test_private_key_redacted(self):
        text = (
            "-----BEGIN RSA KEY-----\n"
            "MIIEowIBAAKCAQEA1234567890abcdef\n"
            "-----END RSA KEY-----"
        )
        assert "MIIEowIBAAKCAQEA1234567890abcdef" not in redact_secrets(text)
        assert "REDACTED" in redact_secrets(text)

    def test_openssh_key_redacted(self):
        text = (
            "-----BEGIN OPENSSH KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAABAAAAMQAAAAtzc2gtZWQyNTUxOQAAACA\n"
            "-----END OPENSSH KEY-----"
        )
        assert "REDACTED" in redact_secrets(text)


class TestNormalContentPassthrough:
    def test_empty_string_returns_empty(self):
        assert redact_secrets("") == ""

    def test_normal_text_unchanged(self):
        text = "이것은 일반 텍스트입니다. 비밀이 없습니다."
        assert redact_secrets(text) == text

    def test_short_values_not_redacted(self):
        text = 'api_key = "short"'
        assert redact_secrets(text) == text

    def test_code_snippet_without_secrets_unchanged(self):
        text = "def my_function(api_key):\n    return api_key.upper()"
        assert redact_secrets(text) == text

    def test_multiline_normal_text_unchanged(self):
        text = "# README\n\n이 프로젝트는 FastAPI로 구성되었습니다.\n## 설치\npip install -r requirements.txt"
        assert redact_secrets(text) == text

    def test_spaces_only_passthrough(self):
        assert redact_secrets("   ") == "   "
