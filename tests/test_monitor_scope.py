import asyncio
import time
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from decimal import Decimal
from urllib.parse import urlsplit
from monitor.db import DB
from monitor.models import Reading
from monitor.service import Monitor
from monitor.identity import same_product
from monitor.config import DEFAULT_DOMAINS
from monitor.search_scope import search_domains


def setup(path=':memory:'):
    db = DB(path)
    config = SimpleNamespace(minimum=0, percent=Decimal('0'), target=None, interval=18000)
    reading = Reading('Placa-Mãe MSI MAG X870 Tomahawk WiFi, AMD AM5 DDR5',
        'KaBuM', 'NewCondition', 'Pix', 200000, 'in_stock',
        identifiers={'brand': 'msi', 'mpn': 'mag x870 tomahawk wifi'})
    ad = db.save_ad('https://www.kabum.com.br/produto/123/msi-mag-x870-tomahawk-wifi', 'KaBuM', reading)
    pid, _ = db.subscribe(db.request_scope(ad['id']), 'site', config)
    return db, config, reading, ad, pid


def test_expand_keeps_id_history_confirmation_filters_and_interval():
    db, config, reading, ad, pid = setup()
    candidate = db.rows('SELECT * FROM candidates WHERE product=?', (pid,))[0]
    db.record(candidate, reading)
    db.run('UPDATE products SET minimum=1234,percent=?,interval_seconds=1800 WHERE id=?', ('7',pid))
    assert db.expand_monitor(pid) == ('expanded', pid)
    row = db.rows('SELECT * FROM products WHERE id=?', (pid,))[0]
    assert row['query'] == reading.title and row['scope'] == 'all' and row['next_due'] == 0
    assert row['minimum'] == 1234 and row['percent'] == '7' and row['interval_seconds'] == 1800
    assert len(db.rows('SELECT * FROM prices')) == 1
    assert len(db.rows('SELECT * FROM candidates')) == 1
    assert db.rows('SELECT confirmed FROM candidates')[0]['confirmed'] == 1
    assert db.expand_monitor(pid) == ('already', pid)
    assert db.subscribe(db.request_scope(ad['id']), 'all', config) == (pid, False)
    db.conn.close()


def test_expanding_does_not_duplicate_an_existing_all_store_monitor():
    db, config, reading, ad, pid = setup()
    other, _ = db.subscribe(db.request_scope(ad['id']), 'all', config)
    assert db.expand_monitor(pid) == ('existing', other)
    assert db.rows('SELECT scope FROM products WHERE id=?', (pid,))[0]['scope'] == 'site'
    assert len(db.rows('SELECT * FROM products')) == 2
    db.conn.close()


def test_expanding_paused_monitor_does_not_resume_it():
    db, config, reading, ad, pid = setup()
    db.run('UPDATE products SET active=0,next_due=123 WHERE id=?', (pid,))
    db.expand_monitor(pid)
    row = db.rows('SELECT * FROM products WHERE id=?', (pid,))[0]
    assert row['active'] == 0 and row['next_due'] == 123
    db.conn.close()


def test_expanded_monitor_searches_exact_model_and_uses_persistent_interval(tmp_path):
    async def run():
        path = str(tmp_path / 'scope.sqlite')
        db, config, reading, ad, pid = setup(path)
        db.expand_monitor(pid)
        db.run('UPDATE products SET interval_seconds=1800 WHERE id=?', (pid,))
        db.conn.close()
        db = DB(path)
        search = SimpleNamespace(links=AsyncMock(return_value=[]))
        fetcher = SimpleNamespace(canonical=lambda url: (url, urlsplit(url).hostname.removeprefix('www.')))
        monitor = Monitor(db, config, fetcher, search, AsyncMock())
        monitor.read = AsyncMock(return_value=[reading])
        before = time.time()
        await monitor.check(pid)
        searched = search.links.await_args.args[0].lower()
        assert 'x870' in searched and 'tomahawk' in searched and 'x870e' not in searched
        due = db.rows('SELECT next_due FROM products WHERE id=?', (pid,))[0]['next_due']
        assert before + 1800 <= due <= time.time() + 1800
        assert len(db.rows('SELECT * FROM series')) == 1
        db.conn.close()
    asyncio.run(run())


def test_x870e_is_not_the_requested_x870_even_with_matching_identifier():
    db, config, reading, ad, pid = setup()
    assert same_product(reading, replace(reading, title=reading.title.replace('X870', 'X870E'))) is False
    db.conn.close()


def test_motherboard_search_uses_all_relevant_enabled_shops_and_keeps_future_sources():
    selected = search_domains('Placa-Mãe MSI MAG X870 Tomahawk WiFi', DEFAULT_DOMAINS.split(','))
    assert set(selected) == {'kabum.com.br','pichau.com.br','terabyteshop.com.br','patoloco.com.br',
                             'amazon.com.br','mercadolivre.com.br','magazineluiza.com.br','shopee.com.br'}
    assert search_domains('MSI MAG X870 Tomahawk WiFi', DEFAULT_DOMAINS.split(',')) == selected
    assert search_domains('Placa mae X870', ('future.example', 'lacoste.com')) == ('future.example',)
