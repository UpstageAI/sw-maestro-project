"""흔한 시크릿 패턴을 마스킹. 완벽하지 않지만 사고 방지용 1차 필터."""
import re

PATTERNS = [
    # api_key / secret / token / password — @·!·. 등 특수문자 포함 값도 감지
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-@!#$%&*.]{16,})['\"]?"),
     r"\1=***REDACTED***"),
    # Bearer 토큰 (Authorization 헤더 형식)
    (re.compile(r"(?i)Bearer\s+([A-Za-z0-9_\-\.]{16,})"),
     "Bearer ***REDACTED***"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "sk-***REDACTED***"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "ghp_***REDACTED***"),
    (re.compile(r"AIza[0-9A-Za-z_-]{30,}"), "AIza***REDACTED***"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AKIA***REDACTED***"),
    (re.compile(r"-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----[\s\S]+?-----END \1 KEY-----"),
     "-----REDACTED PRIVATE KEY-----"),
]


def redact_secrets(text: str) -> str:
    if not text:
        return text
    for pat, repl in PATTERNS:
        text = pat.sub(repl, text)
    return text
