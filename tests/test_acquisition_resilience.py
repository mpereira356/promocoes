import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from monitor.adapters.base import ReadError
from monitor.network import Fetcher
from monitor.external_market_search import ExternalMarketSearch
from monitor.store_status import store_status


def test_store_pauses_survive_restart_without_retrying_blocked_requests(tmp_path):
    async def run():
        c = SimpleNamespace(domains=('kabum.com.br', 'pichau.com.br'), db=str(tmp_path / 'monitor.sqlite3'))
        f = Fetcher(c)
        f.pause_access('kabum.com.br')
        f.pause_rate('pichau.com.br', 7 * 86400)
        await f.close()
        state = json.loads((tmp_path / 'store-backoff.json').read_text(encoding='utf-8'))
        assert set(state) == {'access', 'rate'}
        restarted = Fetcher(c)
        restarted.public = AsyncMock()
        try:
            assert restarted.rate_paused['pichau.com.br'] > time.monotonic() + 6 * 86400
            with pytest.raises(ReadError, match='domain_access_cooldown'):
                await restarted.request('https://www.kabum.com.br/produto/1')
            with pytest.raises(ReadError, match='store_rate_cooldown'):
                await restarted.request('https://www.pichau.com.br/placa-mae')
            restarted.public.assert_not_awaited()
        finally:
            await restarted.close()
    asyncio.run(run())


def test_expired_and_invalid_backoff_do_not_disable_stores_forever(tmp_path):
    async def run():
        c = SimpleNamespace(domains=('kabum.com.br',), db=str(tmp_path / 'monitor.sqlite3'))
        p = tmp_path / 'store-backoff.json'
        for contents in ('invalid json', json.dumps({'access': {'kabum.com.br': time.time() - 1}}),
                         json.dumps({'access': {'kabum.com.br': float('inf')}})):
            p.write_text(contents, encoding='utf-8')
            f = Fetcher(c)
            try:
                assert not f.access_paused
            finally:
                await f.close()
    asyncio.run(run())


def test_optional_official_search_key_replaces_keyless_auth_and_never_supplies_price(monkeypatch):
    async def run():
        post = AsyncMock(return_value=httpx.Response(200, json={'results': [{
            'url': 'https://www.kabum.com.br/produto/123/ssd-x1', 'title': 'SSD X1', 'price': 1}]}))
        monkeypatch.setattr(httpx.AsyncClient, 'post', post)
        f = Fetcher(SimpleNamespace(domains=('kabum.com.br',), tavily_key='test-key'))
        try:
            result = await ExternalMarketSearch(f).links('SSD X1', 'kabum.com.br')
            assert len(result) == 1
            assert not hasattr(result[0], 'price')
            headers = post.await_args.kwargs['headers']
            assert headers['Authorization'] == 'Bearer test-key'
            assert 'X-Tavily-Access-Mode' not in headers
        finally:
            await f.close()
    asyncio.run(run())


def test_store_status_does_not_confuse_http_200_with_verified_price():
    f = SimpleNamespace(access_paused={}, rate_paused={'pichau.com.br': time.monotonic() + 120},
                        page_access={'kabum.com.br': {'http_status': 200}})
    text = store_status(f, ('kabum.com.br', 'pichau.com.br'))
    assert 'preço depende dos dados' in text
    assert 'pausa após bloqueio/limite' in text
