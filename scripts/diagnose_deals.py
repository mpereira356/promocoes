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
        delay=3, provider=os.getenv('SEARCH_PROVIDER', 'direct'), key=os.getenv('SEARCH_API_KEY', ''),
        tavily_key=os.getenv('TAVILY_API_KEY', ''), mercadolivre_token='', mercadolivre_discovery='external')
    fetcher = Fetcher(config)
    try:
        monitor = Monitor(None, config, fetcher, None, None)
        deals = Deals(monitor, Limits(args.pages, args.products, args.comparisons))
        category = args.category if args.category in CATEGORIES else deals.catalog.request(args.category, fetcher)
        report = await deals.run(category, DiscountFilter.parse(args.discount), config.domains, args.cep,
                                 validation=getattr(args, 'validation', 'market'))
        return {'coverage': [asdict(c) for c in report.coverage], 'messages': list(messages(report)),
                'examined': [asdict(o) for o in report.examined],
                'validation': report.validation, 'unconfirmed': report.unconfirmed,
                'not_advantageous': report.not_advantageous,
                'evidence': [{'url': r.offer.url, 'status': r.evidence.status,
                              'reference': r.evidence.reference, 'saving_percent': str(r.evidence.percent),
                              'peer_stores': [p.domain for p in r.evidence.peers],
                              'history_days': r.evidence.history_days} for r in report.results if r.evidence],
                'robots': fetcher.robots_diagnostics}
    finally:
        await fetcher.close()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stores', default=','.join(ADAPTERS))
    parser.add_argument('--category', default='hardware/placas-mae', help='Chave do catalogo, tema livre ou link HTTPS da categoria')
    parser.add_argument('--discount', default='>=30')
    parser.add_argument('--validation', choices=('market', 'announced'), default='market',
                        help='market exige evidência; announced é diagnóstico legado sem comprovação de vantagem')
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
