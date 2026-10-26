import asyncio
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from monitor.models import Reading
from monitor.db import DB
from monitor.network import Fetcher
from monitor.deals.models import DealOffer, DiscountFilter
from monitor.deals.evidence import assess, meets_filter
from monitor.deals.service import Deals, Limits
from monitor.deals.catalog import Category
from monitor.deals.adapters import ADAPTERS
from monitor.deals.adapters.base import CategoryPage
from monitor.deals.formatting import messages
from monitor.adapters.patoloco import PatolocoAdapter

DOMAINS = ('kabum.com.br', 'pichau.com.br', 'terabyteshop.com.br')


def offer(price, domain=DOMAINS[0], old=None, **changes):
    r = Reading('SSD Acme X1', domain, 'NewCondition', 'Pix', price, 'in_stock',
                identifiers={'brand': 'acme', 'mpn': 'ACME-X1'})
    return DealOffer(replace(r, **changes), f'https://www.{domain}/produto/123/ssd', domain, domain, old)


def test_users_45_vs_42_example_never_confirms_advertised_40_percent():
    a, b, c = offer(4500, old=7500), offer(4200, DOMAINS[1]), offer(4200, DOMAINS[2])
    result = assess(a, [a, b, c])
    assert result.status == 'not_below_market'
    assert not meets_filter(result, DiscountFilter.parse('>0'), a.reading.price)
    # The competitor's equal price is not a promotion either.
    assert assess(b, [a, b, c]).status == 'not_below_market'


def test_42_vs_45_is_6_percent_advantage_not_advertised_40():
    a, b, c = offer(4200, old=7000), offer(4500, DOMAINS[1]), offer(4600, DOMAINS[2])
    e = assess(a, [a, b, c])
    assert e.status == 'verified' and e.reference == 4500
    assert 6 < e.percent < 7 and e.inflated_reference
    assert not meets_filter(e, DiscountFilter.parse('>40'), 4200)
    assert meets_filter(e, DiscountFilter.parse('>5'), 4200)


@pytest.mark.parametrize('change', [dict(condition=''), dict(condition='UsedCondition'), dict(stock='out_of_stock'),
                                  dict(payment='Boleto'), dict(currency='USD'),
                                  dict(identifiers={'brand': 'acme', 'mpn': 'different'})])
def test_unknown_or_different_terms_are_not_market_proof(change):
    a = offer(3000)
    pool = [a, offer(4500, DOMAINS[1], **change), offer(4600, DOMAINS[2])]
    assert assess(a, pool).status == 'unconfirmed'


def test_same_store_modalities_and_expired_prices_do_not_create_peers():
    a = offer(3000)
    b = offer(4500, DOMAINS[1])
    assert assess(a, [a, b, b]).status == 'unconfirmed'
    assert assess(a, [a, b, replace(offer(4500, DOMAINS[2]), observed_at=a.observed_at - 1000)]).status == 'unconfirmed'
    assert assess(replace(a, observed_at=a.observed_at - 1000), [a, b]).status == 'unconfirmed'


def test_coupon_membership_and_variant_mismatches_cannot_validate_a_bargain():
    a, b, c = offer(3000), offer(4500, DOMAINS[1]), offer(4600, DOMAINS[2])
    assert assess(replace(a, coupon='EXCLUSIVE'), [a, b, c]).status == 'unconfirmed'
    assert assess(replace(a, members='Premium'), [a, b, c]).status == 'unconfirmed'
    sized = replace(a, reading=replace(a.reading, identifiers={**a.reading.identifiers, 'size': 'M'}))
    assert assess(sized, [a, b, c]).status == 'unconfirmed'
    assert assess(replace(a, coupon='EXCLUSIVE'), [], history={'days': 2, 'lowest': 4500, 'span_seconds': 86400}).status == 'unconfirmed'


def test_recorded_regular_price_prevents_fake_recent_discount():
    a, b, c = offer(4200, old=7000), offer(4500, DOMAINS[1]), offer(4600, DOMAINS[2])
    e = assess(a, [a, b, c], history={'days': 3, 'lowest': 4200, 'span_seconds': 172800})
    assert e.status == 'not_below_history'
    assert not meets_filter(e, DiscountFilter.parse('>0'), 4200)
    # A two-day history can prove a store-specific fall, but never best market price.
    h = assess(offer(3000), [], history={'days': 2, 'lowest': 4500, 'span_seconds': 86400})
    assert h.status == 'history_only'
    assert assess(offer(3000), [], history={'days': 1, 'lowest': 4500}).status == 'unconfirmed'
    assert assess(offer(3000), [], history={'days': 2, 'lowest': 4500, 'span_seconds': 300}).status == 'unconfirmed'
    weak = offer(3000, identifiers={'brand': 'acme', 'mpn': 'X870'})
    assert assess(weak, [], history={'days': 3, 'lowest': 4500, 'span_seconds': 172800}).status == 'unconfirmed'


def test_observations_do_not_create_monitoring_or_manufacture_history(tmp_path):
    db = DB(str(tmp_path / 'monitor.sqlite3'))
    a = offer(4200)
    now = 1800000000
    try:
        db.observe_prices(a.url, [replace(a.reading, price=4500)], now - 3 * 86400)
        db.observe_prices(a.url, [replace(a.reading, price=4600)], now - 2 * 86400)
        for _ in range(3):
            db.observe_prices(a.url, [a.reading], now)
        history = db.observed_history(a.url, a.reading, now)
        assert history == {'lowest': 4500, 'days': 2, 'span_seconds': 86400}
        assert db.rows('SELECT COUNT(*) n FROM price_observations')[0]['n'] == 3
        assert db.rows('SELECT * FROM products') == db.rows('SELECT * FROM alerts') == []
        assert db.observed_history(a.url, replace(a.reading, payment='Boleto'), now)['days'] == 0
        db.observe_prices(a.url, [replace(a.reading, condition='')], now)
        assert db.rows('SELECT COUNT(*) n FROM price_observations')[0]['n'] == 3
    finally:
        db.conn.close()


@pytest.mark.parametrize('prices,expected', [([4500, 4200, 4200], 0), ([3000, 4500, 4600], 1)])
def test_real_service_confirms_only_cross_store_saving(monkeypatch, prices, expected):
    async def run():
        cfg = SimpleNamespace(domains=DOMAINS, browser=False)
        f = Fetcher(cfg)
        offers = {d: offer(p, d, old=7500 if index == 0 else None) for index, (d, p) in enumerate(zip(DOMAINS, prices))}
        urls = {d: offers[d].url for d in DOMAINS}
        f.html = AsyncMock(side_effect=lambda url: ('<html/>', url))
        async def snapshot(url):
            d = f.canonical(url)[1]
            return [offers[d].reading], '<html/>', url
        m = SimpleNamespace(config=cfg, fetcher=f, read_snapshot=AsyncMock(side_effect=snapshot))
        for d in DOMAINS:
            monkeypatch.setattr(ADAPTERS[d], 'page', lambda html, url, domain=d: CategoryPage([urls[domain]]))
            monkeypatch.setattr(ADAPTERS[d], 'offer', lambda html, url, reading, domain=d: offers[domain])
        monkeypatch.setattr(ADAPTERS['pichau.com.br'], 'catalog_discovery', 'category')
        search = AsyncMock()
        monkeypatch.setattr('monitor.deals.service.Search.links', search)
        cat = Category('hardware/ssd', ('Hardware', 'SSD'), {d: f'https://www.{d}/hardware/ssd' for d in DOMAINS})
        try:
            report = await Deals(m).run(cat, DiscountFilter.parse('>20'), DOMAINS)
            assert report.validation == 'market' and len(report.results) == expected
            search.assert_not_awaited()  # Existing peer readings avoid extra requests.
            output = '\n'.join(messages(report))
            assert 'Pesquisa finalizada' in output
            if expected:
                assert report.results[0].evidence.reference == 4500
                assert '33.33%' in output
                assert 'Desconto anunciado' in output
            else:
                assert 'sem vantagem' in output
                assert 'Preço com vantagem verificada' not in output
        finally:
            await f.close()
    asyncio.run(run())


def test_patoloco_real_capture_does_not_invent_condition_or_use_internal_sku():
    html = Path('tests/fixtures/patoloco_product_real.html').read_text(encoding='utf-8')
    url = 'https://patoloco.com.br/placa-mae-msi-mag-x870e-tomahawk-wifi-amd-socket-am5-atx-ddr5-udimm-wi-fi-7-preto-x870etomahawkwifi'
    readings = PatolocoAdapter().parse(html, url)
    assert {r.price for r in readings} == {245389}
    assert {r.payment for r in readings} == {'Pix', 'Boleto'}
    assert all(r.condition == '' and not r.comparable for r in readings)
    assert readings[0].identifiers['mpn'] == 'x870etomahawkwifi'
    assert 'PM.MS.2545' not in str(readings[0].identifiers)


def test_comparison_query_budget_is_global_and_cannot_grow_per_product(monkeypatch):
    async def run():
        cfg = SimpleNamespace(domains=DOMAINS, browser=False)
        f = Fetcher(cfg)
        urls = [f'https://www.kabum.com.br/produto/{index}/ssd' for index in range(9)]
        f.html = AsyncMock(side_effect=lambda url: ('<html/>', url))
        async def snapshot(url):
            o = offer(3000)
            o.reading.identifiers['mpn'] = 'model-' + url.split('/produto/')[1]
            return [o.reading], '<html/>', url
        m = SimpleNamespace(config=cfg, fetcher=f, read_snapshot=AsyncMock(side_effect=snapshot))
        for domain in DOMAINS:
            monkeypatch.setattr(ADAPTERS[domain], 'page', lambda html, url, d=domain: CategoryPage(urls if d == DOMAINS[0] else []))
            monkeypatch.setattr(ADAPTERS[domain], 'offer', lambda html, url, r, d=domain: DealOffer(r, url, d, d))
        monkeypatch.setattr(ADAPTERS['pichau.com.br'], 'catalog_discovery', 'category')
        search = AsyncMock(return_value=[])
        monkeypatch.setattr('monitor.deals.service.Search.links', search)
        cat = Category('hardware/ssd', ('Hardware', 'SSD'), {d: f'https://www.{d}/hardware/ssd' for d in DOMAINS})
        try:
            report = await Deals(m, Limits(comparison_queries=3)).run(cat, DiscountFilter.parse('>5'), DOMAINS)
            assert search.await_count == 3
            assert m.read_snapshot.await_count == 9
            assert not report.results and report.unconfirmed == 9
        finally:
            await f.close()
    asyncio.run(run())


def test_expanded_scans_overlap_different_stores_with_bounded_concurrency(monkeypatch):
    async def run():
        domains = (*DOMAINS, 'patoloco.com.br')
        cfg = SimpleNamespace(domains=domains, browser=False)
        f = Fetcher(cfg)
        active = peak = 0
        async def html(url):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(.01)
            active -= 1
            return '<html/>', url
        f.html = AsyncMock(side_effect=html)
        for d in domains:
            monkeypatch.setattr(ADAPTERS[d], 'page', lambda html, url: CategoryPage([]))
        monkeypatch.setattr(ADAPTERS['pichau.com.br'], 'catalog_discovery', 'category')
        m = SimpleNamespace(config=cfg, fetcher=f, read_snapshot=AsyncMock())
        c = Category('hardware/ssd', ('Hardware', 'SSD'), {d: f'https://www.{d}/hardware/ssd' for d in domains})
        try:
            report = await Deals(m).run(c, DiscountFilter.parse('>5'), domains, depth='expanded')
            assert peak == 3 and f.html.await_count == 4
            assert len(report.coverage) == 4 and report.depth == 'expanded'
        finally:
            await f.close()
    asyncio.run(run())
