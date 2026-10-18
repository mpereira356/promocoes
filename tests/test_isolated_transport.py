"""A consulta publica isolada mantem as regras do Fetcher."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import httpx
import pytest
from monitor.network import Fetcher
from monitor.adapters.base import ReadError


@pytest.mark.parametrize('status,expected_calls',[(200,1),(403,1),(429,3)])
def test_isolated_transport_does_not_reuse_product_session_or_bypass_refusals(monkeypatch,status,expected_calls):
    async def run():
        f=Fetcher(SimpleNamespace(domains=('amazon.com.br',),browser=False,delay=0))
        url='https://www.amazon.com.br/gp/product/ajax/aodAjaxMain?asin=B08KGVH7YC&pc=dp'
        f.public=AsyncMock();f.allowed_by_robots=AsyncMock()
        shared=AsyncMock(side_effect=AssertionError('shared connection must not be used'))
        monkeypatch.setattr(f.client,'get',shared)
        isolated=AsyncMock()
        isolated.__aenter__.return_value=isolated
        isolated.get.return_value=httpx.Response(status,text='<div>public panel</div>',request=httpx.Request('GET',url))
        factory=Mock(return_value=isolated)
        monkeypatch.setattr(httpx,'AsyncClient',factory)
        monkeypatch.setattr('monitor.network.asyncio.sleep',AsyncMock())
        try:
            if status==200:
                assert (await f.html(url,isolated=True))[0]=='<div>public panel</div>'
            else:
                with pytest.raises(ReadError,match='blocked_no_bypass' if status==403 else 'rate_limit_deferred'):
                    await f.html(url,isolated=True)
            assert isolated.get.await_count==expected_calls
            shared.assert_not_awaited()
            assert factory.call_args.kwargs['follow_redirects'] is False
            assert factory.call_args.kwargs['headers']['User-Agent'].startswith('PriceMonitor/')
            isolated.__aexit__.assert_awaited_once()
            if status==403:assert 'amazon.com.br' in f.access_paused
        finally:await f.close()
    asyncio.run(run())
