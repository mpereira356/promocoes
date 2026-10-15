"""Diagnostico sem Telegram/SQLite: descoberta e uma oferta por loja."""

import argparse
import asyncio
import json
import os
from types import SimpleNamespace
from dotenv import load_dotenv
from monitor.config import normalize_domains
from monitor.network import Fetcher
from monitor.discovery import DirectSearch
from monitor.adapters import adapter
from monitor.adapters.base import ReadError
from monitor.version import VERSION


async def diagnose(config, query):
    fetcher = Fetcher(config)
    report = {
        "version": VERSION,
        "chromium": config.browser,
        "query": query,
        "stores": [],
    }
    try:
        links = await DirectSearch(config, fetcher).links(query)
        report["discovery_notices"] = links.notices
        for domain in config.domains:
            urls = [url for url in links if fetcher.canonical(url)[1] == domain]
            item = {"domain": domain, "discovered_urls": urls}
            if urls:
                try:
                    body, final = await fetcher.html(urls[0])
                    readings = adapter(domain).parse(body, final)
                    item["readings"] = [
                        {
                            "title": r.title,
                            "price_read": r.price is not None,
                            "payment": r.payment,
                            "seller": r.seller,
                            "condition": r.condition,
                            "stock": r.stock,
                            "comparable": r.comparable,
                        }
                        for r in readings
                    ]
                except Exception as exc:
                    item["error"] = (
                        str(exc) if isinstance(exc, ReadError) else type(exc).__name__
                    )
            report["stores"].append(item)
        return report
    finally:
        await fetcher.close()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Diagnostico de lojas sem tokens na saida e sem enviar Telegram."
    )
    parser.add_argument(
        "--browser", action=argparse.BooleanOptionalAction, default=None
    )
    parser.add_argument("--query", default="Gigabyte B550 Aorus Elite V2")
    parser.add_argument('--store', help='Dominio para diagnosticar isoladamente, ex.: mercadolivre.com.br')
    args = parser.parse_args()
    browser = (
        args.browser
        if args.browser is not None
        else os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true"
    )
    c = SimpleNamespace(
        browser=browser,
        delay=max(1, float(os.getenv("REQUEST_DELAY", "3"))),
        domains=normalize_domains(
            args.store or os.getenv("ALLOWED_DOMAINS", "pichau.com.br,terabyteshop.com.br,mercadolivre.com.br")
        ),
        mercadolivre_token=os.getenv('MERCADOLIVRE_ACCESS_TOKEN', '').strip(),
    )
    print(
        json.dumps(asyncio.run(diagnose(c, args.query)), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
