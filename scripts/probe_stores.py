"""Sondagem manual, sem busca/Telegram e sem precos nos relatorios."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from monitor.network import Fetcher
from monitor.adapters import adapter
from monitor.adapters.base import ReadError

URLS = [
    "https://www.kabum.com.br/produto/398852/placa-mae-asus-rog-strix-b550-f-gaming-wifi-ii-amd-m-2-ddr4-90mb19v0-mvaay0",
    "https://www.pichau.com.br/placa-mae-asus-rog-strix-b550-f-gaming-wi-fi-ii-ddr4-socket-am4-atx-chipset-amd-b550-rog-strix-b550-f-gaming-wifi-ii",
    "https://www.terabyteshop.com.br/produto/20306/placa-mae-asus-rog-strix-b550-f-gaming-wi-fi-ii-chipset-b550-amd-am4-atx-ddr4-90mb19v0-m0eay0",
]


async def main():
    config = SimpleNamespace(
        domains=("kabum.com.br", "pichau.com.br", "terabyteshop.com.br"), delay=3
    )
    fetcher = Fetcher(config)
    results = []
    try:
        for url in URLS:
            _, domain = fetcher.canonical(url)
            result = {"domain": domain, "url": url}
            try:
                html, final = await fetcher.html(url)
                readings = adapter(domain).parse(html, final)
                result.update(
                    status="parsed",
                    readings=len(readings),
                    comparable=all(r.comparable for r in readings),
                    fields=[
                        {
                            "title": r.title,
                            "has_price": r.price is not None,
                            "seller": bool(r.seller),
                            "condition": bool(r.condition),
                            "payment": bool(r.payment),
                            "stock": r.stock,
                        }
                        for r in readings
                    ],
                )
            except Exception as exc:
                result["status"] = (
                    str(exc) if isinstance(exc, ReadError) else type(exc).__name__
                )
            results.append(result)
            print(json.dumps(result, ensure_ascii=True))
        Path("data/probe-results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    finally:
        await fetcher.close()


asyncio.run(main())
