"""Consulta de categoria real sem banco, token Telegram ou mensagens."""
import argparse
import asyncio
import json
import os
from dataclasses import asdict
from types import SimpleNamespace
from dotenv import load_dotenv
from monitor.network import Fetcher
from monitor.service import Monitor
from monitor.config import normalize_domains
from monitor.deals.service import Deals, Limits
from monitor.deals.models import DiscountFilter
from monitor.deals.formatting import messages
from monitor.deals.adapters import ADAPTERS, CATEGORIES


async def diagnose(args):
    config = SimpleNamespace(domains=normalize_domains(args.stores), browser=args.browser,
        delay=3, provider='direct', key='', mercadolivre_token='', mercadolivre_discovery='external')
    fetcher = Fetcher(config)
    try:
        monitor = Monitor(None, config, fetcher, None, None)
        report = await Deals(monitor, Limits(args.pages, args.products, args.comparisons)).run(
            args.category, DiscountFilter.parse(args.discount), config.domains, args.cep)
        return {'coverage': [asdict(c) for c in report.coverage], 'messages': list(messages(report)),
                'examined': [asdict(o) for o in report.examined],
                'robots': fetcher.robots_diagnostics}
    finally:
        await fetcher.close()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stores', default=','.join(ADAPTERS))
    parser.add_argument('--category', choices=CATEGORIES, default='hardware/placas-mae')
    parser.add_argument('--discount', default='>=30')
    parser.add_argument('--cep', default='')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--products', type=int, default=3)
    parser.add_argument('--comparisons', type=int, default=1)
    parser.add_argument('--browser', action=argparse.BooleanOptionalAction,
                        default=os.getenv('PLAYWRIGHT_ENABLED', 'false').lower() == 'true')
    args = parser.parse_args()
    print(json.dumps(asyncio.run(diagnose(args)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
