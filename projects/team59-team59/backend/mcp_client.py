import asyncio
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HWPX_STDIO_CMD = ["npx", "hwpx-mcp"]
_MCP_RPC_PATHS = ["/", "/rpc", "/mcp"]


class MCPClient:
    """Connects to hwpx-mcp via HTTP JSON-RPC; falls back to stdio subprocess."""

    def __init__(self, http_url: str) -> None:
        self.http_url = http_url.rstrip("/")
        self._http = httpx.AsyncClient(timeout=30.0)
        self._stdio_proc: asyncio.subprocess.Process | None = None
        self._stdio_lock: asyncio.Lock = asyncio.Lock()
        self._use_http: bool = True

    async def connect(self) -> None:
        """Verify HTTP connectivity; fall back to stdio subprocess if unavailable."""
        try:
            resp = await self._http.get(f"{self.http_url}/health", timeout=5.0)
            if resp.status_code == 200:
                logger.info("hwpx-mcp HTTP connection OK: %s", self.http_url)
                self._use_http = True
                return
        except Exception as exc:
            logger.warning("hwpx-mcp HTTP unavailable (%s) – using stdio fallback", exc)

        self._use_http = False
        await self._start_stdio()

    async def _start_stdio(self) -> None:
        logger.info("Spawning hwpx-mcp subprocess: %s", _HWPX_STDIO_CMD)
        self._stdio_proc = await asyncio.create_subprocess_exec(
            *_HWPX_STDIO_CMD,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await self._stdio_rpc(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "hwp-editor-chatbot", "version": "0.1.0"},
                },
                "id": 0,
            }
        )
        logger.info("hwpx-mcp stdio session initialized")

    async def _stdio_rpc(self, payload: dict[str, Any]) -> Any:
        assert self._stdio_proc is not None
        assert self._stdio_proc.stdin is not None
        assert self._stdio_proc.stdout is not None

        async with self._stdio_lock:
            self._stdio_proc.stdin.write((json.dumps(payload) + "\n").encode())
            await self._stdio_proc.stdin.drain()

            while True:
                raw = await asyncio.wait_for(
                    self._stdio_proc.stdout.readline(), timeout=30.0
                )
                if not raw:
                    raise ConnectionError("hwpx-mcp stdio closed unexpectedly")
                data: dict[str, Any] = json.loads(raw.decode())
                if data.get("id") == payload.get("id"):
                    if "error" in data:
                        raise ValueError(f"MCP error: {data['error']}")
                    return data.get("result")

    async def _http_rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": 1}
        if params is not None:
            payload["params"] = params

        last_exc: Exception = ConnectionError("hwpx-mcp HTTP unreachable")
        for path in _MCP_RPC_PATHS:
            try:
                resp = await self._http.post(
                    f"{self.http_url}{path}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    data: dict[str, Any] = resp.json()
                    if "error" in data:
                        raise ValueError(f"MCP error: {data['error']}")
                    return data.get("result")
            except ValueError:
                raise
            except Exception as exc:
                last_exc = exc
        raise last_exc

    async def list_tools(self) -> list[dict[str, Any]]:
        if self._use_http:
            result = await self._http_rpc("tools/list")
        else:
            result = await self._stdio_rpc(
                {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
            )
        if result is None:
            return []
        tools: list[dict[str, Any]] = result.get("tools", [])
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        params: dict[str, Any] = {"name": tool_name, "arguments": arguments}
        if self._use_http:
            return await self._http_rpc("tools/call", params)
        return await self._stdio_rpc(
            {"jsonrpc": "2.0", "method": "tools/call", "params": params, "id": 2}
        )

    async def close(self) -> None:
        await self._http.aclose()
        if self._stdio_proc is not None and self._stdio_proc.returncode is None:
            self._stdio_proc.terminate()
            await self._stdio_proc.wait()


def get_mcp_url() -> str:
    return os.getenv("HWPX_MCP_URL", "http://hwpx-mcp:3001")
