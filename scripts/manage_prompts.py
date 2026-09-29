from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langfuse import get_client

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

PROMPT_NAME = "day13-chat"
BASELINE_PROMPT = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
CANDIDATE_PROMPT = (
    "Feature={{feature}}\n"
    "Docs={{docs}}\n"
    "Question={{message}}\n"
    "Answer in at most 4 concise sentences and cite only the supplied docs."
)


def _labels(prompt: Any) -> set[str]:
    return set(getattr(prompt, "labels", []) or []) - {"latest"}


def _get_prompt(client: Any, label: str) -> Any | None:
    try:
        return client.get_prompt(
            PROMPT_NAME,
            label=label,
            type="text",
            cache_ttl_seconds=0,
            max_retries=1,
            fetch_timeout_seconds=5,
        )
    except Exception:
        return None


def bootstrap(client: Any) -> tuple[Any, Any]:
    baseline = _get_prompt(client, "baseline")
    if baseline is None:
        baseline = client.create_prompt(
            name=PROMPT_NAME,
            prompt=BASELINE_PROMPT,
            labels=["baseline", "production"],
            type="text",
            tags=["day13", "cp2"],
            commit_message="CP2 baseline prompt",
        )
        print(f"Created baseline v{baseline.version}")
    else:
        labels = _labels(baseline) | {"baseline", "production"}
        client.update_prompt(
            name=PROMPT_NAME,
            version=int(baseline.version),
            new_labels=sorted(labels),
        )
        print(f"Using baseline v{baseline.version}")

    candidate = _get_prompt(client, "candidate")
    if candidate is None:
        candidate = client.create_prompt(
            name=PROMPT_NAME,
            prompt=CANDIDATE_PROMPT,
            labels=["candidate"],
            type="text",
            tags=["day13", "cp2"],
            commit_message="CP2 concise candidate prompt",
        )
        print(f"Created candidate v{candidate.version}")
    else:
        print(f"Using candidate v{candidate.version}")

    return baseline, candidate


def move_production(client: Any, target_label: str) -> None:
    target = _get_prompt(client, target_label)
    if target is None:
        raise RuntimeError(f"Prompt label '{target_label}' does not exist; run bootstrap first")
    labels = _labels(target) | {target_label, "production"}
    client.update_prompt(
        name=PROMPT_NAME,
        version=int(target.version),
        new_labels=sorted(labels),
    )
    action = "Promoted" if target_label == "candidate" else "Rolled back"
    print(f"{action} production to v{target.version} ({target_label})")


def show_status(client: Any) -> None:
    for label in ("baseline", "candidate", "production"):
        prompt = _get_prompt(client, label)
        version = getattr(prompt, "version", "missing")
        print(f"{label}: {version}")


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        print("Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY in .env")
        return 1

    parser = argparse.ArgumentParser(description="Manage the CP2 day13-chat prompt lifecycle")
    parser.add_argument(
        "action",
        choices=("bootstrap", "promote", "rollback", "status"),
        nargs="?",
        default="status",
    )
    args = parser.parse_args()
    client = get_client()

    if args.action == "bootstrap":
        bootstrap(client)
    elif args.action == "promote":
        move_production(client, "candidate")
    elif args.action == "rollback":
        move_production(client, "baseline")
    show_status(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
