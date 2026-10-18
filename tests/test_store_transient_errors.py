import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from monitor.adapters import adapter
from monitor.adapters.base import ReadError
from monitor.network import Fetcher


URL = 'https://sensetup.com.br/products/cadeira-ergonomica-a08-premium-openbox'
HTML = Path(__file__).with_name('fixtures').joinpath('sensetup_a08_openbox_real.html').read_text(encoding='utf-8')


@pytest.mark.parametrize(('failure', 'reason', 'status'), [
    ('timeout', 'network_timeout', None),
    ('connection', 'network_connection_failure', None),
    (503, 'store_temporarily_unavailable', 503),
    (429, 'rate_limit_deferred', 429),
])
def test_retry_exhaustion_has_exact_reason_and_sanitized_attempts(monkeypatch, failure, reason, status):
    async def run():
        f = Fetcher(SimpleNamespace(domains=('sensetup.com.br',), browser=False, delay=0))
        f.public = AsyncMock()
        f.allowed_by_robots = AsyncMock()
        calls = []

        def handler(request):
            calls.append(request)
            if failure == 'timeout': raise httpx.ReadTimeout('sensitive detail', request=request)
            if failure == 'connection': raise httpx.ConnectError('sensitive detail', request=request)
            return httpx.Response(failure, request=request)

        await f.client.aclose()
        f.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr('monitor.network.asyncio.sleep', AsyncMock())
        try:
            with pytest.raises(ReadError, match=reason): await f.html(URL)
            assert len(calls) == 3
            audit = f.page_access['sensetup.com.br']
            assert audit['http_status'] == status
            assert len(audit['attempts']) == 3
            assert 'sensitive detail' not in str(audit)
            assert 'https://' not in str(audit)
            if status == 429:
                with pytest.raises(ReadError, match='store_rate_cooldown'): await f.html(URL)
                assert len(calls) == 3
        finally: await f.close()
    asyncio.run(run())


@pytest.mark.parametrize('failure', ['timeout', 503])
def test_transient_failure_recovers_to_actual_openbox_price(monkeypatch, failure):
    async def run():
        f = Fetcher(SimpleNamespace(domains=('sensetup.com.br',), browser=False, delay=0))
        f.public = AsyncMock()
        f.allowed_by_robots = AsyncMock()
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            if calls == 1:
                if failure == 'timeout': raise httpx.ReadTimeout('temporary', request=request)
                return httpx.Response(503, request=request)
            return httpx.Response(200, text=HTML, request=request)

        await f.client.aclose()
        f.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        monkeypatch.setattr('monitor.network.asyncio.sleep', AsyncMock())
        try:
            html, final = await f.html(URL)
            reading, = adapter('sensetup.com.br').parse(html, final)
            assert reading.price == 159000 and reading.stock == 'out_of_stock'
            assert 'OpenBox' in reading.title and reading.condition == ''
            assert calls == 2
            assert f.page_access['sensetup.com.br']['attempts'][-1]['http_status'] == 200
        finally: await f.close()
    asyncio.run(run())


def test_long_retry_after_prevents_requests_to_other_products(monkeypatch):
    async def run():
        f = Fetcher(SimpleNamespace(domains=('sensetup.com.br',), browser=False, delay=0))
        f.public = AsyncMock()
        f.allowed_by_robots = AsyncMock()
        get = AsyncMock(return_value=httpx.Response(429, headers={'Retry-After':'600'}, request=httpx.Request('GET', URL)))
        monkeypatch.setattr(f.client, 'get', get)
        monkeypatch.setattr('monitor.network.asyncio.sleep', AsyncMock())
        try:
            with pytest.raises(ReadError, match='rate_limit_deferred'): await f.html(URL)
            with pytest.raises(ReadError, match='store_rate_cooldown'):
                await f.html(URL.replace('-openbox', ''))
            assert get.await_count == 1
        finally: await f.close()
    asyncio.run(run())


def test_exhausted_network_failure_preserves_saved_openbox_reading(monkeypatch):
    from monitor.db import DB
    from monitor.service import Monitor
    from monitor.search_results import deliver_search
    import json

    async def run():
        db = DB(':memory:')
        r, = adapter('sensetup.com.br').parse(HTML, URL)
        db.save_ad(URL, 'Sensetup', r)
        config = SimpleNamespace(domains=('sensetup.com.br',), browser=False, delay=0)
        f = Fetcher(config)
        f.public = AsyncMock()
        f.allowed_by_robots = AsyncMock()
        monkeypatch.setattr(f.client, 'get', AsyncMock(side_effect=httpx.ReadTimeout('sensitive')))
        monkeypatch.setattr('monitor.network.asyncio.sleep', AsyncMock())
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        send = AsyncMock()
        try:
            await deliver_search(Monitor(db,config,f,None,send), f, db, bot, 42, URL, send)
            assert json.loads(db.rows('SELECT reading FROM ads')[0]['reading'])['price'] == 159000
            assert not db.rows('SELECT * FROM alerts')
            assert 'Ofertas enviadas: 0' in send.await_args.args[0]
            assert any('tempo limite' in call.args[0] for call in send.await_args_list)
        finally:
            await f.close()
            db.conn.close()
    asyncio.run(run())


@pytest.mark.parametrize('date_header', [False, True])
def test_retry_after_on_last_attempt_is_respected(monkeypatch, date_header):
    import time
    from datetime import datetime, timezone
    from email.utils import format_datetime

    async def run():
        f = Fetcher(SimpleNamespace(domains=('sensetup.com.br',), browser=False, delay=0))
        f.public = AsyncMock()
        f.allowed_by_robots = AsyncMock()
        header = format_datetime(datetime.fromtimestamp(time.time()+600, timezone.utc)) if date_header else '600'
        get = AsyncMock(side_effect=[httpx.Response(503), httpx.Response(503),
                                    httpx.Response(429, headers={'Retry-After': header})])
        monkeypatch.setattr(f.client, 'get', get)
        monkeypatch.setattr('monitor.network.asyncio.sleep', AsyncMock())
        try:
            with pytest.raises(ReadError, match='rate_limit_deferred'): await f.html(URL)
            assert f.rate_paused['sensetup.com.br'] - time.monotonic() > 590
            assert len(f.page_access['sensetup.com.br']['attempts']) == 3
            with pytest.raises(ReadError, match='store_rate_cooldown'): await f.html(URL)
            assert get.await_count == 3
        finally: await f.close()
    asyncio.run(run())
