"""Respostas simuladas; testes nao fazem chamadas externas."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from monitor.adapters.base import ReadError
from monitor.discovery import DirectSearch, LinkCandidate, SearchLinks
from monitor.external_market_search import ExternalMarketSearch
from monitor.network import Fetcher
from monitor.search_results import deliver_search

URL = 'https://www.mercadolivre.com.br/placa-b550/p/MLB123456'


def test_external_search_accepts_catalog_but_never_prices_and_caches(monkeypatch):
    async def run():
        response = httpx.Response(200, json={'results': [
            {'url': URL, 'title': 'Placa B550', 'content': 'R$ 1,00', 'price': 1},
            {'url': URL, 'title': 'Duplicado'},
            {'url': 'https://evil.org/p/MLB123', 'title': 'B550'},
            {'url': 'https://lista.mercadolivre.com.br/b550', 'title': 'Categoria'},
            {'url': 'https://www.mercadolivre.com.br/placa-z790/p/MLB654321', 'title': 'Placa B550'},
            {'url': 'https://www.mercadolivre.com.br/arquivo-b550/up/MLBU99999', 'title': 'Arquivo B550'},
        ]})
        post = AsyncMock(return_value=response)
        monkeypatch.setattr(httpx.AsyncClient, 'post', post)
        f = Fetcher(SimpleNamespace(domains=('mercadolivre.com.br',)))
        try:
            search = ExternalMarketSearch(f)
            a = await search.links('B550')
            assert a == await search.links('B550')
            assert len(a) == 1 and a[0].source == 'Tavily Search'
            assert not hasattr(a[0], 'price')
            assert post.await_count == 1
            options = post.await_args.kwargs
            assert options['headers']['X-Tavily-Access-Mode'] == 'keyless'
            assert 'Authorization' not in options['headers']
            assert options['json']['include_raw_content'] is False
        finally:
            await f.close()
    asyncio.run(run())


def test_keyless_rate_limit_waits_without_repeated_requests(monkeypatch):
    async def run():
        post = AsyncMock(return_value=httpx.Response(429, headers={'Retry-After': '600'}))
        monkeypatch.setattr(httpx.AsyncClient, 'post', post)
        search = ExternalMarketSearch(SimpleNamespace(config=SimpleNamespace(domains=('mercadolivre.com.br',))))
        for _ in range(2):
            with pytest.raises(ReadError, match='external_search_limited'):
                await search.links('B550')
        assert post.await_count == 1
    asyncio.run(run())


@pytest.mark.parametrize('already_limited', [False, True])
def test_expired_link_cache_survives_quota_without_caching_prices(monkeypatch, already_limited):
    import time
    async def run():
        post = AsyncMock(return_value=httpx.Response(429, headers={'Retry-After': '600'}))
        monkeypatch.setattr(httpx.AsyncClient, 'post', post)
        search = ExternalMarketSearch(SimpleNamespace(config=SimpleNamespace(domains=('mercadolivre.com.br',))))
        search.cache[('mercadolivre.com.br', 'b550')] = (time.monotonic() - 1, [LinkCandidate(URL, 'B550', 'Tavily Search')])
        if already_limited:
            search.cooldown = time.monotonic() + 600
        links = await search.links('B550')
        assert links[0].url == URL and not hasattr(links[0], 'price')
        assert 'cache' in links.notices[0]
        assert post.await_count == (0 if already_limited else 1)
        # Não reutilizar links indefinidamente após a validade estendida.
        search.cache[('mercadolivre.com.br', 'b550')] = (time.monotonic() - 8 * 86400, links)
        with pytest.raises(ReadError, match='external_search_limited'):
            await search.links('B550')
    asyncio.run(run())


def test_unverified_catalog_is_sent_without_reading_or_saving_offer():
    async def run():
        links = SearchLinks([URL], candidates={URL: LinkCandidate(URL, 'Placa B550', 'Tavily Search')})
        read, send = AsyncMock(), AsyncMock()
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=links)), read=read)
        f = SimpleNamespace(canonical=lambda u: (u, 'mercadolivre.com.br'))
        await deliver_search(monitor, f, None, None, 1, 'B550', send)
        text = send.await_args_list[0].args[0]
        assert URL in text and 'não foram verificados' in text and 'não ativa monitoramento' in text
        assert '/monitorar' not in text and 'R$' not in text
        read.assert_not_awaited()
        assert 'Links para conferência: 1' in send.await_args_list[-1].args[0]
    asyncio.run(run())


def test_default_marketplace_discovery_uses_index_without_requesting_store(monkeypatch):
    async def run():
        c = SimpleNamespace(domains=('mercadolivre.com.br',), browser=True)
        f = Fetcher(c)
        f.html = AsyncMock(side_effect=AssertionError('store must not be requested'))
        monkeypatch.setattr(ExternalMarketSearch, 'links', AsyncMock(return_value=[LinkCandidate(URL, 'Placa B550', 'Tavily Search')]))
        try:
            found = await DirectSearch(c, f).links('Placa B550')
            assert found == [URL]
            assert found.candidates[URL].source == 'Tavily Search'
            f.html.assert_not_awaited()
        finally:
            await f.close()
    asyncio.run(run())


def test_blocked_individual_listing_remains_unverified_without_saving():
    async def run():
        url = 'https://produto.mercadolivre.com.br/MLB-1234567890-placa-b550-_JM'
        links = SearchLinks([url], candidates={url: LinkCandidate(url, 'Placa B550', 'Tavily Search')})
        send = AsyncMock()
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=links)), read=AsyncMock(side_effect=ReadError('robots_unavailable')))
        f = SimpleNamespace(canonical=lambda u: (u, 'mercadolivre.com.br'))
        await deliver_search(monitor, f, None, None, 1, 'B550', send)
        text = send.await_args_list[0].args[0]
        assert url in text and 'não foram verificados' in text and 'Leitura da página' in text
        assert 'Ofertas enviadas: 0' in send.await_args_list[-1].args[0]
        assert 'Links para conferência: 1' in send.await_args_list[-1].args[0]
    asyncio.run(run())
