"""MCP server exposing recent news via NewsAPI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from mcp.server.fastmcp import FastMCP

from .common import build_http_client, get_env, now_iso

mcp = FastMCP("newsapi-news", log_level="WARNING")


@mcp.tool()
async def get_recent_news(
    query: str,
    page_size: int = 10,
    days_back: int = 14,
    language: str = "en",
) -> dict:
    """Fetch recent news articles for a query string."""
    q = query.strip()
    if not q:
        raise ValueError("Query must not be empty")

    capped_page_size = max(1, min(page_size, 25))
    start_date = (datetime.now(timezone.utc) - timedelta(days=max(days_back, 0))).date().isoformat()

    base_url = get_env("NEWS_BASE_URL", "https://newsapi.org").rstrip("/")
    api_key = get_env("NEWS_API_KEY")
    endpoint = f"{base_url}/v2/everything"
    params = {
        "q": q,
        "sortBy": "publishedAt",
        "pageSize": capped_page_size,
        "language": language,
        "from": start_date,
        "apiKey": api_key,
    }

    async with build_http_client() as client:
        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"newsapi request failed with status {status_code}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"newsapi request failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("newsapi returned invalid JSON") from exc

    if payload.get("status") == "error":
        message = payload.get("message") or "Unknown NewsAPI error"
        code = payload.get("code")
        if code:
            raise RuntimeError(f"NewsAPI error ({code}): {message}")
        raise RuntimeError(f"NewsAPI error: {message}")

    articles = []
    for item in payload.get("articles", []) or []:
        source_obj = item.get("source") or {}
        articles.append(
            {
                "title": item.get("title"),
                "description": item.get("description"),
                "url": item.get("url"),
                "publishedAt": item.get("publishedAt"),
                "source": source_obj.get("name"),
            }
        )

    redacted_params = {k: v for k, v in params.items() if k != "apiKey"}
    redacted_url = str(httpx.URL(endpoint, params=redacted_params))

    result = {
        "query": q,
        "from": start_date,
        "articles": articles,
        "totalResults": int(payload.get("totalResults") or 0),
        "fetched_at": now_iso(),
        "sources": {"newsapi_url": redacted_url},
    }
    return result


if __name__ == "__main__":
    mcp.run()
