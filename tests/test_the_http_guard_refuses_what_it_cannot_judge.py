"""The HTTP guard answers every request it cannot accept with a refusal (audit 2026-09-27 C-14).

docs/research/2026-09-27-the-http-guard-refuses-what-it-cannot-judge.md
"""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("starlette")

import mcp_http  # noqa: E402

TOKEN = "test-token-value-not-a-real-secret"


def _guard(app) -> mcp_http.LoopbackGuard:
    return mcp_http.LoopbackGuard(app, token=TOKEN, allowed_hosts={"127.0.0.1:8765"})


def _http_scope(authorization: bytes) -> dict:
    return {"type": "http", "client": ("127.0.0.1", 5), "headers": [
        (b"host", b"127.0.0.1:8765"), (b"authorization", b"Bearer " + authorization)]}


def test_a_non_ascii_bearer_token_is_a_wrong_token() -> None:
    assert _guard(None).refusal(_http_scope("é".encode("latin-1"))) == (401, "a valid bearer token is required")


def test_a_websocket_never_reaches_the_app() -> None:
    reached: list[str] = []
    sent: list[dict] = []

    async def app(scope, receive, send) -> None:
        reached.append(scope["type"])

    async def receive() -> dict:
        return {"type": "websocket.connect"}

    async def send(message: dict) -> None:
        sent.append(message)

    asyncio.run(_guard(app)({"type": "websocket", "headers": []}, receive, send))

    assert (reached, sent) == ([], [{"type": "websocket.close", "code": 1008}])
