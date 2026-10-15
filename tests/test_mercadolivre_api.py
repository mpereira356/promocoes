"""Simulacao da API oficial, sem token real ou chamadas externas."""
import asyncio
from types import SimpleNamespace
import httpx
import pytest
from monitor.adapters.base import ReadError
from monitor.mercadolivre_api import discover
from monitor.network import Fetcher


def test_api_discovers_links_without_importing_prices():
    async def run():
        def handler(request):
            assert request.headers['Authorization'] == 'Bearer simulated-token'
            assert 'simulated-token' not in str(request.url)
            return httpx.Response(200, json={'results': [
                {'permalink': 'https://produto.mercadolivre.com.br/MLB-1234567890-placa-_JM', 'title': 'Placa B550', 'price': 0},
                {'permalink': 'https://evil.org/MLB-1234567890', 'title': 'Placa B550'},
                {'permalink': 'https://www.mercadolivre.com.br/placa/p/MLB123', 'title': 'Catalogo B550'},
            ]})
        f = Fetcher(SimpleNamespace(domains=('mercadolivre.com.br',)))
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                found = await discover('b550', 'simulated-token', f, client)
            assert len(found) == 1 and found[0].title == 'Placa B550'
            assert not hasattr(found[0], 'price')
        finally:
            await f.close()
    asyncio.run(run())


@pytest.mark.parametrize('status,reason', [(401, 'mercadolivre_api_token_expired'), (403, 'mercadolivre_api_access_denied')])
def test_api_authorization_failures_not_retried(status, reason):
    async def run():
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(status, json={'message': 'private detail'})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ReadError, match=reason) as exc:
                await discover('b550', 'simulated-token', None, client)
            assert 'private detail' not in str(exc.value)
            assert len(calls) == 1
    asyncio.run(run())


def test_missing_api_token_never_requests_network():
    with pytest.raises(ReadError, match='mercadolivre_api_token_missing'):
        asyncio.run(discover('b550', '', None))
