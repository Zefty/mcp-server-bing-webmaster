from unittest.mock import AsyncMock

import pytest

from mcp_server_bwt import main


@pytest.mark.parametrize(
    "name,endpoint,response",
    [
        ("get_keyword_data", "GetKeyword", {"Query": "receipt to csv", "Impressions": 12}),
        ("get_related_keywords", "GetRelatedKeywords", [{"Query": "receipt csv"}]),
    ],
)
async def test_keyword_request_contract(monkeypatch, name, endpoint, response):
    request = AsyncMock(return_value=response)
    monkeypatch.setattr(main.api, "_make_request", request)
    result = await getattr(main, name)(
        site_url="https://gexpense.app/",
        query="receipt to csv",
        country="au",
        language="en-AU",
        start_date="2026-10-01",
        end_date="2026-10-30",
    )
    request.assert_awaited_once_with(
        endpoint,
        params={
            "q": "receipt to csv",
            "country": "au",
            "language": "en-AU",
            "startDate": "2026-10-01",
            "endDate": "2026-10-30",
        },
    )
    assert result == response


@pytest.mark.parametrize("rows", [[], [{"Query": "blood pressure log", "Impressions": 10}]])
async def test_trends_accept_lists_through_mcp(monkeypatch, rows):
    request = AsyncMock(return_value=rows)
    monkeypatch.setattr(main.api, "_make_request", request)
    result = await main.mcp.call_tool(
        "get_keyword_stats",
        {
            "site_url": "https://bpbook.app/",
            "query": "blood pressure log",
            "country": "us",
            "language": "en-US",
        },
    )
    request.assert_awaited_once_with(
        "GetKeywordStats",
        params={
            "q": "blood pressure log",
            "country": "us",
            "language": "en-US",
        },
    )
    assert result is not None


@pytest.mark.parametrize("name", ["get_keyword_data", "get_related_keywords"])
async def test_defaults_and_invalid_date_ranges(monkeypatch, name):
    request = AsyncMock(return_value={} if name == "get_keyword_data" else [])
    monkeypatch.setattr(main.api, "_make_request", request)
    await getattr(main, name)(site_url="https://example.com/", query="receipt")
    params = request.call_args.kwargs["params"]
    assert params["q"] == "receipt"
    assert params["country"] == "us"
    assert params["language"] == "en-US"
    assert params["startDate"] <= params["endDate"]
    request.reset_mock()
    with pytest.raises(ValueError):
        await getattr(main, name)(
            site_url="", query="receipt", start_date="2026-11-01", end_date="2026-10-01"
        )
    request.assert_not_awaited()


@pytest.mark.parametrize(
    "endpoint,method", [("SubmitUrl", "GET"), ("RemoveSite", "POST"), ("GetKeyword", "POST")]
)
async def test_read_only_blocks_mutations_before_http(monkeypatch, endpoint, method):
    client = main.BingWebmasterAPI("test-only")
    client.read_only = True
    transport = AsyncMock()
    monkeypatch.setattr(client, "_ensure_client", transport)
    with pytest.raises(ValueError, match="disabled"):
        await client._make_request(endpoint, method=method)
    transport.assert_not_awaited()


async def test_read_only_tool_catalog(monkeypatch):
    # A fresh process avoids changing the shared server's registered tools.
    import os
    import subprocess
    import sys

    script = """
import asyncio
from mcp_server_bwt.main import mcp, configure_read_only
async def check():
    await configure_read_only()
    names = [tool.name for tool in await mcp.list_tools()]
    assert 'get_keyword_data' in names
    assert all(name.startswith('get_') for name in names)
asyncio.run(check())
"""
    subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "BING_WEBMASTER_READ_ONLY": "true"},
        check=True,
    )
