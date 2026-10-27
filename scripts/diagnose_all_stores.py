"""Audita cada loja com um produto pertinente, sem Telegram ou alterações no banco."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from dotenv import load_dotenv
from monitor.config import DEFAULT_DOMAINS, normalize_domains
from monitor.version import VERSION
from scripts.diagnose_stores import diagnose

QUERIES = {
    **{domain: 'Picanha Maturatta' for domain in ('atacadao.com.br', 'extramercado.com.br', 'mercado.carrefour.com.br', 'boasupermercados.com.br')},
    'patoloco.com.br': 'Placa mae MSI MAG X870E Tomahawk WiFi',
    'kabum.com.br': 'SSD Kingston NV3 1TB',
    'pichau.com.br': 'Gigabyte B550 Aorus Elite V2',
    'terabyteshop.com.br': 'Gigabyte B550 Aorus Elite V2',
    'mercadolivre.com.br': 'Boné Esportivo Leve',
    'amazon.com.br': 'Boné Esportivo Leve',
    'lacoste.com': 'Boné Esportivo Leve',
    'sensetup.com.br': 'cadeira sensetup',
    'loja.elements.com.br': 'cadeira elements',
    'flexform.com.br': 'cadeira flexform',
    'shopee.com.br': 'Boné Esportivo Leve',
    'magazineluiza.com.br': 'freezer vertical',
    'frigelar.com.br': 'freezer vertical',
    'brastemp.com.br': 'freezer vertical',
}


async def audit(config, timeout=90):
    results = []
    # Sequential requests share the same external service quota.
    for domain in config.domains:
        query = QUERIES.get(domain, 'produto')
        local = SimpleNamespace(**vars(config))
        local.domains = (domain,)
        try:
            detail = await asyncio.wait_for(diagnose(local, query), timeout)
            store = detail['stores'][0]
            readings = store.get('readings', [])
            status = ('price_read' if any(r['price_read'] for r in readings)
                      else store.get('error') or ('links_only' if store['discovered_urls'] else 'no_links'))
        except TimeoutError:
            detail, status = {}, 'timeout'
        except Exception as exc:
            detail, status = {}, type(exc).__name__
        results.append({'domain': domain, 'query': query, 'status': status, 'detail': detail})
        print(f'{domain}: {status}', flush=True)
    return {'version': VERSION, 'stores': results}


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--output', default='data/all-stores-diagnostic.json')
    args = parser.parse_args()
    if not 10 <= args.timeout <= 300:
        parser.error('--timeout deve estar entre 10 e 300 segundos por loja')
    config = SimpleNamespace(
        domains=normalize_domains(os.getenv('ALLOWED_DOMAINS', DEFAULT_DOMAINS)),
        browser=args.browser if args.browser is not None else os.getenv('PLAYWRIGHT_ENABLED', 'false').lower() == 'true',
        delay=max(1, float(os.getenv('REQUEST_DELAY', '3'))),
        mercadolivre_token=os.getenv('MERCADOLIVRE_ACCESS_TOKEN', '').strip(),
        mercadolivre_discovery=os.getenv('MERCADOLIVRE_DISCOVERY', 'external'),
        tavily_key=os.getenv('TAVILY_API_KEY', '').strip(),
    )
    report = asyncio.run(audit(config, args.timeout))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Relatório: {output}')


if __name__ == '__main__':
    main()
