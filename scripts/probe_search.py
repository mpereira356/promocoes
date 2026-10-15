"""Sonda busca direta sem token, chave ou mensagens no Telegram."""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from monitor.network import Fetcher
from monitor.search import Search


async def main():
    query = " ".join(sys.argv[1:]) or "b550"
    config = SimpleNamespace(
        domains=("kabum.com.br", "pichau.com.br", "terabyteshop.com.br"),
        delay=3,
        provider="direct",
        key="",
        browser=False,
    )
    fetcher = Fetcher(config)
    try:
        result = await Search(config, fetcher).links(query)
        report = {"query": query, "links": list(result), "notices": result.notices}
        Path("data").mkdir(exist_ok=True)
        Path("data/direct-search-probe.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=True))
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
