from __future__ import annotations

import re
from collections.abc import Iterable

from app.core.models import MaskedToken, MaskingResult


class PIIGuard:
    EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    PHONE_RE = re.compile(r"\b(?:01[0-9]|0[2-6][0-9]?)-?\d{3,4}-?\d{4}\b")
    RRN_RE = re.compile(r"\b\d{6}-?[1-4]\d{6}\b")
    LABELED_NAME_RE = re.compile(r"(?im)^(?:name|이름)\s*[:：]\s*([가-힣A-Za-z ]{2,30})$")

    def mask(self, text: str) -> MaskingResult:
        masked_text = text
        tokens: list[MaskedToken] = []
        counters = {"name": 0, "email": 0, "phone": 0, "rrn": 0}

        def apply(pattern: re.Pattern[str], kind: str, value_from_match: callable | None = None) -> None:
            nonlocal masked_text

            def replace(match: re.Match[str]) -> str:
                original = value_from_match(match) if value_from_match else match.group(0)
                counters[kind] += 1
                token = f"[{kind.upper()}_{counters[kind]:03d}]"
                tokens.append(MaskedToken(token=token, original=original, kind=kind))  # type: ignore[arg-type]
                if value_from_match:
                    return match.group(0).replace(original, token)
                return token

            masked_text = pattern.sub(replace, masked_text)

        apply(self.EMAIL_RE, "email")
        apply(self.PHONE_RE, "phone")
        apply(self.RRN_RE, "rrn")
        apply(self.LABELED_NAME_RE, "name", lambda match: match.group(1).strip())

        failure_reasons = list(self._detect_leftovers(masked_text))
        return MaskingResult(
            masked_text=masked_text,
            tokens=tokens,
            safe_for_llm=len(failure_reasons) == 0,
            failure_reasons=failure_reasons,
        )

    def _detect_leftovers(self, text: str) -> Iterable[str]:
        if self.EMAIL_RE.search(text):
            yield "Unmasked email detected after masking."
        if self.PHONE_RE.search(text):
            yield "Unmasked phone number detected after masking."
        if self.RRN_RE.search(text):
            yield "Unmasked resident registration number detected after masking."

