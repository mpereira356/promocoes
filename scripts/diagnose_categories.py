"""Lista ou atualiza categorias publicas sem Telegram, token ou banco."""
import argparse
import asyncio
import json
import os
from types import SimpleNamespace
from dotenv import load_dotenv
from monitor.config import normalize_domains
from monitor.network import Fetcher
from monitor.deals.catalog import CategoryCatalog
from monitor.deals.adapters import ADAPTERS


async def diagnose(args):
    config=SimpleNamespace(domains=normalize_domains(args.stores),browser=args.browser,delay=3)
    catalog=CategoryCatalog()
    notices=[]
    if args.refresh:
        fetcher=Fetcher(config)
        try:
            notices=await catalog.refresh(fetcher,config.domains)
        finally:
            await fetcher.close()
    items=catalog.available(config.domains)
    result={'categories':len(items),'groups':sorted({c.path[0] for c in items}),'notices':notices,
            'scope':'Links de navegacao; nao comprova preco, estoque ou acesso a todas as categorias.'}
    if args.list:
        result['items']=[{'key':c.key,'title':c.title,'urls':c.urls} for c in items]
    return result


def main():
    load_dotenv()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stores',default=','.join(ADAPTERS))
    parser.add_argument('--refresh',action='store_true')
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--browser',action=argparse.BooleanOptionalAction,
        default=os.getenv('PLAYWRIGHT_ENABLED','false').lower()=='true')
    print(json.dumps(asyncio.run(diagnose(parser.parse_args())),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
