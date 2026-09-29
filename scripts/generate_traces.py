from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio


async def generate(label: str, count: int) -> list[str]:
    os.environ["LANGFUSE_PROMPT_LABEL"] = label
    from app.main import app
    from app.tracing import get_langfuse_client

    correlation_ids: list[str] = []
    id_prefix = {"baseline": "ba5", "candidate": "ca1", "production": "f00"}[label]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://cp2") as client:
        for index in range(count):
            response = await client.post(
                "/chat",
                headers={"x-request-id": f"req-{id_prefix}{index:05x}"},
                json={
                    "user_id": "cp2-student",
                    "session_id": f"cp2-{label}",
                    "feature": "monitoring",
                    "message": "How do metrics, logs, and traces identify a latency incident?",
                },
            )
            response.raise_for_status()
            correlation_ids.append(response.json()["correlation_id"])

    get_langfuse_client().flush()
    return correlation_ids


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Generate CP2 Langfuse traces")
    parser.add_argument("--label", choices=("baseline", "candidate", "production"), required=True)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")

    correlation_ids = asyncio.run(generate(args.label, args.count))
    print(f"Generated {len(correlation_ids)} traces with label={args.label}")
    for correlation_id in correlation_ids:
        print(f"  {correlation_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
