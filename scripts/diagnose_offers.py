"""Diagnostica os links exatos, sem Telegram, banco ou credenciais na saída."""
import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import traceback
from types import SimpleNamespace
from dotenv import load_dotenv
from monitor.adapters.base import ReadError
from monitor.config import normalize_domains
from monitor.discovery import REASONS
from monitor.network import Fetcher
from monitor.service import Monitor
from monitor.version import VERSION


async def diagnose(config, urls):
    fetcher = Fetcher(config)
    monitor = Monitor(None, config, fetcher, None, None)
    report = {'version': VERSION, 'browser': config.browser, 'offers': []}
    try:
        for supplied in dict.fromkeys(urls):
            item = {}
            try:
                url, domain = fetcher.canonical(supplied)
                item.update(url=url, domain=domain)
                readings = await monitor.read(url)
                item['readings'] = [asdict(r) for r in readings]
                item['price_verified'] = any(r.price is not None and r.price > 0 for r in readings)
            except Exception as exc:
                item['price_verified'] = False
                item['error_type'] = type(exc).__name__
                item['reason'] = REASONS.get(str(exc), 'Leitura recusada ou formato não reconhecido') if isinstance(exc, ReadError) else 'Erro interno ou de transporte'
                # Apenas posições do código; nunca mensagem bruta, locals ou traceback completo.
                item['code_locations'] = [
                    {'file': Path(f.filename).name, 'function': f.name, 'line': f.lineno}
                    for f in traceback.extract_tb(exc.__traceback__) if 'monitor' in Path(f.filename).parts]
            report['offers'].append(item)
        report['robots'] = fetcher.robots_diagnostics
        report['page_access'] = fetcher.page_access
        return report
    finally:
        await fetcher.close()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', action='append', required=True, help='Repita para testar vários links HTTPS autorizados.')
    parser.add_argument('--browser', action=argparse.BooleanOptionalAction, default=os.getenv('PLAYWRIGHT_ENABLED', 'false').lower() == 'true')
    args = parser.parse_args()
    config = SimpleNamespace(domains=normalize_domains(os.getenv('ALLOWED_DOMAINS',
        'kabum.com.br,pichau.com.br,terabyteshop.com.br,amazon.com.br,mercadolivre.com.br')),
        browser=args.browser, delay=max(3, float(os.getenv('REQUEST_DELAY', '3'))))
    print(json.dumps(asyncio.run(diagnose(config, args.url)), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
