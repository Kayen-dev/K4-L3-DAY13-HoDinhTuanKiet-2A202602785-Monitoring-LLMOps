from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import yaml
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from . import logging_config
from .metrics import percentile

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
DASHBOARD_HTML_PATH = Path(__file__).resolve().parent / "static" / "dashboard.html"

router = APIRouter()


def _timestamp(record: dict[str, Any]) -> datetime | None:
    value = record.get("ts")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc)


def _read_records(now: datetime, window_minutes: int) -> list[dict[str, Any]]:
    path = logging_config.LOG_PATH
    if not path.exists():
        return []
    cutoff = now - timedelta(minutes=window_minutes)
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        ts = _timestamp(record)
        if ts is not None and cutoff <= ts <= now + timedelta(seconds=5):
            records.append(record)
    return sorted(records, key=lambda item: _timestamp(item) or now)


def _minute_series(
    records: list[dict[str, Any]],
    now: datetime,
    value: Callable[[dict[str, Any]], float | None],
    *,
    mode: str = "sum",
) -> list[dict[str, float | str]]:
    buckets: dict[datetime, list[float]] = defaultdict(list)
    for record in records:
        ts = _timestamp(record)
        item = value(record)
        if ts is None or item is None:
            continue
        minute = ts.replace(second=0, microsecond=0)
        buckets[minute].append(float(item))

    end = now.replace(second=0, microsecond=0)
    points: list[dict[str, float | str]] = []
    for offset in range(59, -1, -1):
        minute = end - timedelta(minutes=offset)
        values = buckets.get(minute, [])
        if mode == "mean":
            result = mean(values) if values else 0.0
        else:
            result = sum(values)
        points.append({"label": minute.strftime("%H:%M"), "value": round(result, 6)})
    return points


def _threshold(panel: dict[str, Any]) -> dict[str, Any]:
    threshold = panel["threshold"]
    symbol = "≤" if threshold["operator"] == "lte" else "≥"
    return {
        **threshold,
        "label": f"{threshold['aggregation']} {symbol} {threshold['value']} {panel['unit']}",
    }


def _metric(
    label: str,
    value: float | int | str,
    tone: str = "neutral",
    unit: str | None = None,
) -> dict[str, Any]:
    return {"label": label, "value": value, "tone": tone, "unit": unit}


def build_dashboard_snapshot(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    config = yaml.safe_load(DASHBOARD_CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]
    panel_config = {panel["id"]: panel for panel in config["panels"]}
    records = _read_records(now, int(config["time_range_minutes"]))
    requests = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]

    latencies = [int(record.get("latency_ms", 0)) for record in responses]
    ttfts = [int(record.get("ttft_ms", 0)) for record in responses]
    costs = [float(record.get("cost_usd", 0)) for record in responses]
    tokens_in = sum(int(record.get("tokens_in", 0)) for record in responses)
    tokens_out = sum(int(record.get("tokens_out", 0)) for record in responses)
    qualities = [float(record.get("quality_score", 0)) for record in responses]

    error_rate = (len(failures) / len(requests) * 100) if requests else 0.0
    tool_events = [record for record in records if record.get("tool_success") is not None]
    retrieval_success = (
        sum(record.get("tool_success") is True for record in tool_events)
        / len(tool_events)
        * 100
        if tool_events
        else 100.0
    )
    error_breakdown = Counter(
        str(record.get("error_type") or "Unknown") for record in failures
    )

    latency_cfg = panel_config["latency"]
    latency_p95 = percentile(latencies, 95)
    traffic_cfg = panel_config["traffic"]
    request_rate = len(requests) / int(config["time_range_minutes"])
    errors_cfg = panel_config["errors"]
    cost_cfg = panel_config["cost"]
    total_cost = round(sum(costs), 6)
    tokens_cfg = panel_config["tokens"]
    quality_cfg = panel_config["quality"]
    quality_avg = round(mean(qualities), 3) if qualities else 0.0

    panels = [
        {
            "id": "latency",
            "title": latency_cfg["title"],
            "unit": latency_cfg["unit"],
            "threshold": _threshold(latency_cfg),
            "healthy": latency_p95 <= latency_cfg["threshold"]["value"],
            "metrics": [
                _metric("P50", round(percentile(latencies, 50), 1)),
                _metric("P95", round(latency_p95, 1), "primary"),
                _metric("P99", round(percentile(latencies, 99), 1)),
                _metric("TTFT P95", round(percentile(ttfts, 95), 1)),
            ],
            "series": [
                {
                    "name": "Latency",
                    "values": _minute_series(
                        responses, now, lambda item: item.get("latency_ms"), mode="mean"
                    ),
                },
                {
                    "name": "TTFT",
                    "values": _minute_series(
                        responses, now, lambda item: item.get("ttft_ms"), mode="mean"
                    ),
                },
            ],
        },
        {
            "id": "traffic",
            "title": traffic_cfg["title"],
            "unit": traffic_cfg["unit"],
            "threshold": _threshold(traffic_cfg),
            "healthy": request_rate >= traffic_cfg["threshold"]["value"],
            "metrics": [
                _metric("Requests", len(requests), "primary"),
                _metric("Rate / min", round(request_rate, 2)),
            ],
            "series": [
                {
                    "name": "Requests",
                    "values": _minute_series(
                        requests, now, lambda _: 1.0
                    ),
                }
            ],
        },
        {
            "id": "errors",
            "title": errors_cfg["title"],
            "unit": errors_cfg["unit"],
            "threshold": _threshold(errors_cfg),
            "healthy": error_rate <= errors_cfg["threshold"]["value"],
            "metrics": [
                _metric("Error rate", round(error_rate, 2), "primary"),
                _metric("Retrieval success", round(retrieval_success, 2)),
                _metric("Failures", len(failures), unit="count"),
            ],
            "breakdown": dict(error_breakdown) or {"No errors": 0},
            "series": [
                {
                    "name": "Failures",
                    "values": _minute_series(failures, now, lambda _: 1.0),
                },
                {
                    "name": "Retrieval failures",
                    "values": _minute_series(
                        tool_events,
                        now,
                        lambda item: 1.0 if item.get("tool_success") is False else 0.0,
                    ),
                },
            ],
        },
        {
            "id": "cost",
            "title": cost_cfg["title"],
            "unit": cost_cfg["unit"],
            "threshold": _threshold(cost_cfg),
            "healthy": total_cost <= cost_cfg["threshold"]["value"],
            "metrics": [
                _metric("Window total", total_cost, "primary"),
                _metric("Average / response", round(mean(costs), 6) if costs else 0),
            ],
            "series": [
                {
                    "name": "Cost",
                    "values": _minute_series(
                        responses, now, lambda item: item.get("cost_usd")
                    ),
                }
            ],
        },
        {
            "id": "tokens",
            "title": tokens_cfg["title"],
            "unit": tokens_cfg["unit"],
            "threshold": _threshold(tokens_cfg),
            "healthy": tokens_in + tokens_out <= tokens_cfg["threshold"]["value"],
            "metrics": [
                _metric("Input", tokens_in, "primary"),
                _metric("Output", tokens_out),
                _metric("Total", tokens_in + tokens_out),
            ],
            "series": [
                {
                    "name": "Input",
                    "values": _minute_series(
                        responses, now, lambda item: item.get("tokens_in")
                    ),
                },
                {
                    "name": "Output",
                    "values": _minute_series(
                        responses, now, lambda item: item.get("tokens_out")
                    ),
                },
            ],
        },
        {
            "id": "quality",
            "title": quality_cfg["title"],
            "unit": quality_cfg["unit"],
            "threshold": _threshold(quality_cfg),
            "healthy": quality_avg >= quality_cfg["threshold"]["value"],
            "metrics": [
                _metric("Mean score", quality_avg, "primary"),
                _metric("Samples", len(qualities), unit="count"),
            ],
            "series": [
                {
                    "name": "Quality",
                    "values": _minute_series(
                        responses,
                        now,
                        lambda item: item.get("quality_score"),
                        mode="mean",
                    ),
                }
            ],
        },
    ]

    slo_target = 99.5
    good_requests = sum(latency <= 3000 for latency in latencies)
    achieved = (good_requests / len(requests) * 100) if requests else 100.0
    allowed_bad = len(requests) * (100 - slo_target) / 100
    bad_requests = max(0, len(requests) - good_requests)

    return {
        "meta": {
            "title": config["title"],
            "generated_at": now.isoformat(),
            "time_range_minutes": config["time_range_minutes"],
            "refresh_seconds": config["refresh_seconds"],
            "record_count": len(records),
            "has_data": bool(records),
        },
        "slo": {
            "name": "Fast successful requests",
            "target_percent": slo_target,
            "achieved_percent": round(achieved, 2),
            "good_requests": good_requests,
            "total_requests": len(requests),
            "remaining_bad_requests": round(allowed_bad - bad_requests, 2),
            "healthy": achieved >= slo_target,
        },
        "panels": panels,
    }


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML_PATH.read_text(encoding="utf-8"))


@router.get("/dashboard/data")
async def dashboard_data() -> dict[str, Any]:
    return build_dashboard_snapshot()
