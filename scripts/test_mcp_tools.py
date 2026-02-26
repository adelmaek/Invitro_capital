"""Simple local runner to validate MCP tool functions directly."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_servers.fmp_server import get_company_snapshot
from mcp_servers.news_server import get_recent_news


async def main() -> None:
    """Run both tool functions directly and print their results."""
    snapshot = await get_company_snapshot("AAPL")
    news = await get_recent_news(snapshot["name"] or "AAPL", page_size=5, days_back=7)

    print("Company Snapshot:")
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    print("\nRecent News:")
    print(json.dumps(news, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
