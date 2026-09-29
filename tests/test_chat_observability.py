from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx

from app import logging_config
from app.main import app
from app.pii import hash_user_id


def test_response_propagates_incoming_request_id() -> None:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.get(
                "/health", headers={"x-request-id": "req-deadbeef"}
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-deadbeef"
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])
    assert float(response.headers["x-response-time-ms"]) >= 0
    assert response.json()["correlation_id"] == response.headers["x-request-id"]

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    request_event = next(event for event in events if event["event"] == "request_received")
    response_event = next(event for event in events if event["event"] == "response_sent")

    assert request_event["correlation_id"] == response.headers["x-request-id"]
    assert request_event["user_id_hash"] == hash_user_id("student-01")
    assert request_event["session_id"] == "session-01"
    assert request_event["feature"] == "qa"
    assert request_event["model"]
    assert request_event["env"]
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True
