import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from scripts.diagnose_all_stores import audit, QUERIES
from monitor.config import DEFAULT_DOMAINS
from monitor.adapters.shopee import ShopeeAdapter
from monitor.adapters.base import ReadError


def test_audit_includes_every_default_store_and_survives_one_failure(monkeypatch):
    async def run():
        config = SimpleNamespace(domains=tuple(DEFAULT_DOMAINS.split(',')), browser=False)
        assert set(config.domains) == set(QUERIES)
        async def diagnose(local, query):
            if local.domains == ('magazineluiza.com.br',):
                raise RuntimeError('internal secret must not be printed')
            return {'stores': [{'discovered_urls': ['url'], 'readings': [{'price_read': True}]}]}
        mocked = AsyncMock(side_effect=diagnose)
        monkeypatch.setattr('scripts.diagnose_all_stores.diagnose', mocked)
        report = await audit(config)
        assert len(report['stores']) == 13
        assert mocked.await_count == 13
        assert next(s for s in report['stores'] if s['domain'] == 'magazineluiza.com.br')['status'] == 'RuntimeError'
        assert 'secret' not in str(report)
        assert len(config.domains) == 13
    asyncio.run(run())


def test_shopee_shell_is_not_a_verified_product_price():
    with pytest.raises(ReadError, match='store_requires_javascript'):
        ShopeeAdapter().parse('<noscript>Please enable JavaScript on your browser.</noscript><script>"price":1</script>',
                              'https://shopee.com.br/bone-i.123.456')
