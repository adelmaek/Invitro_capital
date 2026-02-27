# DIFF SUMMARY:
# - Updated direct run_analysis call to prompt-only signature.
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.service import run_analysis


REQUIRED_KEYS = {"company", "thesis", "signal", "insights", "sources"}


def main() -> None:
    output = asyncio.run(
        run_analysis(
            prompt="Analyze ticker AAPL. Return only JSON.",
        )
    )
    print(output)

    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON output: {exc}") from exc

    missing = REQUIRED_KEYS - set(payload.keys())
    if missing:
        raise SystemExit(f"Missing required keys: {sorted(missing)}")

    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        raise
