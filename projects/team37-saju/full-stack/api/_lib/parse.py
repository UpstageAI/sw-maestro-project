"""Request body parsing shared by both endpoints.

Mirrors the original ``api/_lib/parse.ts`` contract: 64 KB body cap, JSON
parsing with a precise 400 message, and a typed payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Union

from fastapi import Request

MAX_BODY_BYTES = 64 * 1024


@dataclass
class ParsedRequest:
    api_key: str
    user_input: dict
    model: Optional[str]


@dataclass
class ParseError:
    error: str
    status: int


ParseResult = Union[ParsedRequest, ParseError]


async def parse_pipeline_request(request: Request) -> ParseResult:
    content_length_hdr = request.headers.get("content-length")
    if content_length_hdr:
        try:
            if int(content_length_hdr) > MAX_BODY_BYTES:
                return ParseError(error="Request body too large", status=413)
        except ValueError:
            pass

    body_bytes = await request.body()
    if len(body_bytes) > MAX_BODY_BYTES:
        return ParseError(error="Request body too large", status=413)

    if not body_bytes:
        return ParseError(error="apiKey와 userInput이 필요합니다.", status=400)

    try:
        raw: Any = json.loads(body_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ParseError(error="Invalid JSON body", status=400)

    if not isinstance(raw, dict):
        return ParseError(error="apiKey와 userInput이 필요합니다.", status=400)

    api_key = raw.get("apiKey")
    user_input = raw.get("userInput")
    model = raw.get("model")

    if not isinstance(api_key, str) or len(api_key) == 0:
        return ParseError(error="apiKey와 userInput이 필요합니다.", status=400)
    if not isinstance(user_input, dict):
        return ParseError(error="apiKey와 userInput이 필요합니다.", status=400)

    return ParsedRequest(
        api_key=api_key,
        user_input=user_input,
        model=model if isinstance(model, str) else None,
    )
