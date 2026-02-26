from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.service import run_analysis


REQUIRED_KEYS = {"company", "thesis", "signal", "insights", "sources"}


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting smoke test")

    output = asyncio.run(run_analysis("AAPL"))
    logger.info("run_analysis returned output (length=%d)", len(output))
    print(output)

    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Output is not valid JSON")
        raise SystemExit(f"Invalid JSON output: {exc}") from exc

    missing = REQUIRED_KEYS - set(payload.keys())
    if missing:
        logger.error("Missing required keys: %s", sorted(missing))
        raise SystemExit(f"Missing required keys: {sorted(missing)}")

    logger.info("Smoke test JSON validation passed")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.getLogger(__name__).exception("Smoke test failed")
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        raise
