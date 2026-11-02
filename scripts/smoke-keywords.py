"""Read-only live keyword checks using an existing Codex Bing credential."""

import asyncio
import json
import logging
import pathlib

import tomllib

from mcp_server_bwt import main


async def run():
    logging.getLogger("httpx").setLevel(logging.WARNING)
    config = tomllib.loads((pathlib.Path.home() / ".codex/config.toml").read_text())
    main.api.api_key = config["mcp_servers"]["bing_webmaster"]["env"]["BING_WEBMASTER_API_KEY"]
    try:
        for name in ["get_keyword_data", "get_related_keywords", "get_keyword_stats"]:
            args = dict(
                site_url="https://bpbook.app/",
                query="blood pressure",
                country="us",
                language="en-US",
            )
            if name != "get_keyword_stats":
                args.update(start_date="2026-08-01", end_date="2026-10-30")
            result = await getattr(main, name)(**args)
            print(
                json.dumps(
                    {
                        "tool": name,
                        "type": type(result).__name__,
                        "rows": len(result) if isinstance(result, list) else 1,
                        "sample": result[:1] if isinstance(result, list) else result,
                    }
                )
            )
    finally:
        if main.api._client:
            await main.api._client.aclose()


asyncio.run(run())
