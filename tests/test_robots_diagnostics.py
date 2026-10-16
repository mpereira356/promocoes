import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from monitor.network import Fetcher
from monitor.adapters.base import ReadError


@pytest.mark.parametrize('status,reason', [(403, 'blocked_no_bypass'), (401, 'blocked_no_bypass')])
def test_robots_diagnostic_preserves_failure_without_reading_product(status, reason):
    async def run():
        f = Fetcher(SimpleNamespace(domains=('mercadolivre.com.br',), delay=0, browser=False))
        f.public = AsyncMock()
        calls = []
        def handle(request):
            calls.append(request.url.path)
            return httpx.Response(status, text='Access denied')
        await f.client.aclose()
        f.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        try:
            with pytest.raises(ReadError, match='robots_unavailable'):
                await f.html('https://www.mercadolivre.com.br/product')
            assert calls == ['/robots.txt']
            assert f.robots_diagnostics['https://www.mercadolivre.com.br'] == {'http_status': status, 'reason': reason}
        finally:
            await f.close()
    asyncio.run(run())
