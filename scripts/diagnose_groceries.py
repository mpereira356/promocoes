"""Read one public Maturatta product per enabled grocer, without Telegram/alerts."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from dotenv import load_dotenv
from monitor.adapters.base import ReadError
from monitor.config import DEFAULT_DOMAINS, normalize_domains
from monitor.discovery import REASONS
from monitor.grocery_profile import postal_code
from monitor.network import Fetcher
from monitor.service import Monitor
from monitor.version import VERSION

PRODUCTS = {
    'atacadao.com.br': 'https://www.atacadao.com.br/carne-bovina-picanha-maturatta-congelada-57030/p',
    'extramercado.com.br': 'https://www.extramercado.com.br/produto/164337/picanha-resfriada-maturatta-friboi-1-5kg',
    'mercado.carrefour.com.br': 'https://mercado.carrefour.com.br/produto/picanha-resfriada-maturatta-aprox-15kg-4733378',
    'boasupermercados.com.br': 'https://www.boasupermercados.com.br/picanha-maturatta-friboi-resfriada-kg-16246/p',
}


async def diagnose(config):
    fetcher = Fetcher(config)
    monitor = Monitor(None, config, fetcher, None, None)
    async def read(domain):
        result = {'domain': domain, 'readings': []}
        try:
            readings = await asyncio.wait_for(monitor.read(PRODUCTS[domain]), 90)
            result['readings'] = [{
                'title': r.title, 'price_cents': r.price, 'unit': r.identifiers.get('price_unit'),
                'stock': r.stock, 'public_unit_price': r.public_unit_price,
                'comparable_history': r.comparable, 'reason': r.identifiers.get('regional_reason', ''),
                'visit_listing': r.visit_listing,
            } for r in readings]
        except Exception as exc:
            result['error'] = REASONS.get(str(exc), 'Leitura regional não confirmada') if isinstance(exc, ReadError) else type(exc).__name__
        print(domain + ': ' + ('preço público por kg confirmado' if any(
            r['comparable_history'] for r in result['readings']) else result.get('error', 'sem oferta regional confirmada')), flush=True)
        return result
    try:
        results = await asyncio.gather(*(read(domain) for domain in config.domains))
        return {'version': VERSION, 'cep_configured': True, 'stores': results,
                'note': 'Consulta pontual. Não cria monitoramentos nem comprova promoção por comparação de mercado.'}
    finally:
        await fetcher.close()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cep', default=os.getenv('GROCERY_POSTAL_CODE', ''))
    parser.add_argument('--mode', choices=('visit', 'delivery'), default=os.getenv('GROCERY_MODE', 'visit'))
    parser.add_argument('--output', default='data/grocery-regional-diagnostic.json')
    args = parser.parse_args()
    try:
        cep = postal_code(args.cep)
    except ValueError as exc:
        parser.error(str(exc))
    domains = normalize_domains(os.getenv('ALLOWED_DOMAINS', DEFAULT_DOMAINS))
    config = SimpleNamespace(domains=tuple(d for d in PRODUCTS if d in domains), browser=False,
                             delay=max(1, float(os.getenv('REQUEST_DELAY', '3'))), grocery_postal_code=cep,
                             grocery_mode=args.mode)
    if not config.domains:
        parser.error('Nenhum dos quatro supermercados está em ALLOWED_DOMAINS.')
    result = asyncio.run(diagnose(config))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
