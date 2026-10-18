import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlsplit

import pytest

from monitor.adapters.base import ReadError
from monitor.db import DB
from monitor.discovery import DirectSearch, SearchLinks
from monitor.models import Reading
from monitor.network import Fetcher
from monitor.service import Monitor


@pytest.mark.parametrize('scope', ['all', 'site'])
def test_known_ads_from_other_stores_are_reread_when_discovery_is_limited(scope):
    async def run():
        db = DB(':memory:')
        config = SimpleNamespace(domains=('pichau.com.br', 'kabum.com.br', 'amazon.com.br'),
                                 minimum=0, percent=0, target=None, interval=18000)
        seed = Reading('Gigabyte B550 Aorus Elite AX V2', 'Pichau', 'NewCondition', 'Pix', 199900,
                       'in_stock', identifiers={'brand':'gigabyte', 'mpn':'b550 aorus elite ax v2'})
        origin = 'https://www.pichau.com.br/placa-mae-b550-aorus-elite-ax-v2'
        kabum = 'https://www.kabum.com.br/produto/473028/b550-aorus-elite-ax-v2'
        amazon = 'https://www.amazon.com.br/dp/B08KGVH7YC'
        wrong = 'https://www.kabum.com.br/produto/123/b550-aorus-elite-v2'
        try:
            ad = db.save_ad(origin, 'Pichau', seed)
            pid, _ = db.subscribe(db.request_scope(ad['id']), scope, config)
            db.save_ad(kabum, 'KaBuM', replace(seed, seller='KaBuM', price=999999))
            db.save_ad(amazon, 'Amazon Brasil', replace(seed, seller='Amazon', price=888888))
            db.save_ad(wrong, 'KaBuM', replace(seed, title='Gigabyte B550 Aorus Elite V2', identifiers={}))
            search = SimpleNamespace(links=AsyncMock(return_value=SearchLinks([], ['Amazon Brasil: índice limitado.'])))
            fetch = SimpleNamespace(canonical=lambda u: (u, urlsplit(u).hostname.removeprefix('www.')))
            monitor = Monitor(db, config, fetch, search, AsyncMock())

            async def read(url):
                if url == origin: raise ReadError('blocked_no_bypass')
                if url == amazon: raise ReadError('network_timeout')
                return [replace(seed, seller='KaBuM', price=143900)]

            monitor.read = AsyncMock(side_effect=read)
            result = await monitor.check(pid)
            read_urls = {c.args[0] for c in monitor.read.await_args_list}
            if scope == 'all':
                assert read_urls == {origin, kabum, amazon}
                assert wrong not in read_urls
                assert search.links.await_args.args[0] == 'gigabyte b550 aorus elite ax v2'
                assert 'KaBuM: 1 leitura(s), 1 com preço' in result
                assert 'Amazon Brasil: 0 leitura(s), 0 com preço, 1 falha(s)' in result
                current = db.rows('SELECT reading FROM ads WHERE url=?', (kabum,))[0]
                assert json.loads(current['reading'])['price'] == 143900
                old = db.rows('SELECT reading FROM ads WHERE url=?', (amazon,))[0]
                assert json.loads(old['reading'])['price'] == 888888  # preservado, nao anunciado como atual
                assert '8.888,88' not in result
            else:
                assert read_urls == {origin}
                search.links.assert_not_awaited()
            assert not db.rows('SELECT * FROM alerts')
        finally:
            db.conn.close()
    asyncio.run(run())


def test_chair_stores_do_not_consume_external_search_quota_for_motherboards():
    async def run():
        config = SimpleNamespace(domains=('sensetup.com.br', 'loja.elements.com.br', 'flexform.com.br'), browser=False, delay=3)
        fetch = Fetcher(config)
        fetch.html = AsyncMock(side_effect=AssertionError('chair catalog must not be requested'))
        search = DirectSearch(config, fetch)
        search.external_candidates = AsyncMock(side_effect=AssertionError('must not consume external quota'))
        try:
            links = await search.links('gigabyte b550 aorus elite ax v2')
            assert not links and len(links.notices) == 3
            assert all('não aplicável' in n for n in links.notices)
        finally:
            await fetch.close()
    asyncio.run(run())
