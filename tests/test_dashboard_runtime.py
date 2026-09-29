from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import logging_config
from app.dashboard import build_dashboard_snapshot


def test_runtime_dashboard_builds_six_panels_from_recent_logs(
    monkeypatch, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    log_path = tmp_path / "logs.jsonl"
    records = [
        {
            "ts": (now - timedelta(minutes=2)).isoformat(),
            "event": "request_received",
            "correlation_id": "req-11111111",
        },
        {
            "ts": (now - timedelta(minutes=1)).isoformat(),
            "event": "response_sent",
            "correlation_id": "req-11111111",
            "latency_ms": 240,
            "ttft_ms": 50,
            "cost_usd": 0.002,
            "tokens_in": 40,
            "tokens_out": 100,
            "quality_score": 0.9,
            "tool_success": True,
        },
        {
            "ts": (now - timedelta(hours=2)).isoformat(),
            "event": "request_failed",
            "correlation_id": "req-old0000",
            "error_type": "OldError",
        },
    ]
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    snapshot = build_dashboard_snapshot(now)

    assert snapshot["meta"]["time_range_minutes"] == 60
    assert snapshot["meta"]["record_count"] == 2
    assert [panel["id"] for panel in snapshot["panels"]] == [
        "latency",
        "traffic",
        "errors",
        "cost",
        "tokens",
        "quality",
    ]
    assert all(panel["threshold"]["label"] for panel in snapshot["panels"])
    assert snapshot["slo"]["achieved_percent"] == 100.0
