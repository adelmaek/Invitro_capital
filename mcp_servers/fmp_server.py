"""MCP server exposing structured company fundamentals via FMP stable APIs."""

from __future__ import annotations

import asyncio
import logging

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .common import build_http_client, get_env, now_iso, safe_float

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("fmp-financials")


class CompanySnapshot(BaseModel):
    """Normalized company fundamentals snapshot."""

    ticker: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    website: str | None = None
    exchange: str | None = None
    currency: str | None = None
    price: float | None = None
    market_cap: float | None = None
    pe_ttm: float | None = None
    ps_ttm: float | None = None
    gross_margin_ttm: float | None = None
    operating_margin_ttm: float | None = None
    net_margin_ttm: float | None = None
    debt_to_equity_ttm: float | None = None
    revenue_latest: float | None = None
    net_income_latest: float | None = None
    period_latest: str | None = None
    fetched_at: str
    sources: dict = Field(default_factory=dict)


async def _get_json(
    client: httpx.AsyncClient, url: str, endpoint_name: str
) -> list[dict] | dict:
    """Fetch JSON and raise clear errors for HTTP failures."""
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise RuntimeError(f"{endpoint_name} request failed with status {status_code}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"{endpoint_name} request failed: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"{endpoint_name} returned invalid JSON") from exc


@mcp.tool()
async def get_company_snapshot(ticker: str) -> dict:
    """Fetch and normalize company profile, key metrics (TTM), and latest income statement for a public ticker."""
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker must not be empty")
    logger.info("get_company_snapshot invoked ticker=%s", symbol)

    base_url = get_env("FMP_BASE_URL", "https://financialmodelingprep.com/stable").rstrip("/")
    api_key = get_env("FMP_API_KEY")

    profile_url = f"{base_url}/profile?symbol={symbol}&apikey={api_key}"
    ratios_ttm_url = f"{base_url}/ratios-ttm?symbol={symbol}&apikey={api_key}"
    income_url = f"{base_url}/income-statement?symbol={symbol}&limit=1&apikey={api_key}"
    profile_url_redacted = str(httpx.URL(f"{base_url}/profile", params={"symbol": symbol}))
    ratios_ttm_url_redacted = str(httpx.URL(f"{base_url}/ratios-ttm", params={"symbol": symbol}))
    income_url_redacted = str(
        httpx.URL(f"{base_url}/income-statement", params={"symbol": symbol, "limit": 1})
    )

    try:
        async with build_http_client() as client:
            profile_raw, metrics_raw, income_raw = await asyncio.gather(
                _get_json(client, profile_url, "profile"),
                _get_json(client, ratios_ttm_url, "ratios-ttm"),
                _get_json(client, income_url, "income-statement"),
            )
    except Exception:
        logger.exception("get_company_snapshot failed ticker=%s", symbol)
        raise

    profile = profile_raw[0] if isinstance(profile_raw, list) and profile_raw else {}
    metrics = metrics_raw[0] if isinstance(metrics_raw, list) and metrics_raw else {}
    income = income_raw[0] if isinstance(income_raw, list) and income_raw else {}

    if not profile and not income:
        raise ValueError("Unknown ticker or no data returned")

    snapshot = CompanySnapshot(
        ticker=symbol,
        name=profile.get("companyName"),
        sector=profile.get("sector"),
        industry=profile.get("industry"),
        description=profile.get("description"),
        website=profile.get("website"),
        exchange=profile.get("exchangeShortName") or profile.get("exchange"),
        currency=profile.get("currency"),
        price=safe_float(profile.get("price")),
        market_cap=safe_float(profile.get("mktCap") if "mktCap" in profile else profile.get("marketCap")),
        pe_ttm=safe_float(metrics.get("peRatioTTM") if "peRatioTTM" in metrics else metrics.get("priceToEarningsRatioTTM")),
        ps_ttm=safe_float(metrics.get("priceToSalesRatioTTM")),
        gross_margin_ttm=safe_float(metrics.get("grossProfitMarginTTM")),
        operating_margin_ttm=safe_float(metrics.get("operatingProfitMarginTTM")),
        net_margin_ttm=safe_float(metrics.get("netProfitMarginTTM")),
        debt_to_equity_ttm=safe_float(
            metrics.get("debtEquityRatioTTM")
            if "debtEquityRatioTTM" in metrics
            else metrics.get("debtToEquityRatioTTM")
        ),
        revenue_latest=safe_float(income.get("revenue")),
        net_income_latest=safe_float(income.get("netIncome")),
        period_latest=income.get("date"),
        fetched_at=now_iso(),
        sources={
            "profile_url": profile_url_redacted,
            "ratios_ttm_url": ratios_ttm_url_redacted,
            "income_statement_url": income_url_redacted,
        },
    )
    logger.info(
        "get_company_snapshot completed ticker=%s name=%s period=%s",
        symbol,
        snapshot.name,
        snapshot.period_latest,
    )
    return snapshot.model_dump()


if __name__ == "__main__":
    mcp.run()
