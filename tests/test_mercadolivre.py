"""Dados inteiramente simulados: nao sao snapshots do Mercado Livre."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.adapters.mercadolivre import MercadoLivreAdapter
from monitor.adapters.base import ReadError
from monitor.discovery import DirectSearch
from monitor.network import Fetcher

URL = 'https://produto.mercadolivre.com.br/MLB-1234567890-placa-b550-_JM'


def product(seller='Vendedor A', condition='NewCondition', payment='Pix'):
    return '<script type="application/ld+json">' + json.dumps({
        '@type': 'Product', 'name': 'Placa B550',
        'offers': {'@type': 'Offer', 'price': '1000.00', 'priceCurrency': 'BRL',
                   'seller': {'name': seller}, 'itemCondition': condition,
                   'acceptedPaymentMethod': payment, 'availability': 'InStock'}
    }) + '</script>'


def test_individual_offer_preserves_seller_condition_and_payment():
    a = MercadoLivreAdapter().parse(product(), URL)[0]
    b = MercadoLivreAdapter().parse(product('Vendedor B', 'UsedCondition', 'boleto'), URL)[0]
    assert a.price == b.price == 100000
    assert (a.seller, a.condition, a.payment) != (b.seller, b.condition, b.payment)


def test_missing_seller_or_payment_never_inferred():
    r = MercadoLivreAdapter().parse(product('', payment=''), URL)[0]
    assert not r.seller and not r.payment and not r.comparable


def test_catalog_cannot_become_an_individual_offer():
    with pytest.raises(ReadError, match='marketplace_individual_listing_required'):
        MercadoLivreAdapter().parse(product(), 'https://www.mercadolivre.com.br/placa/p/MLB123')


def test_only_explicit_marketplace_hosts_are_allowed():
    async def run():
        f = Fetcher(SimpleNamespace(domains=('mercadolivre.com.br',), browser=True, delay=0))
        try:
            assert f.canonical(URL)[1] == 'mercadolivre.com.br'
            assert f.canonical('https://lista.mercadolivre.com.br/b550')[1] == 'mercadolivre.com.br'
            assert f.uses_browser('mercadolivre.com.br')
            for u in ['https://evil.mercadolivre.com.br/', 'https://mercadolivre.com.br.evil.org/']:
                with pytest.raises(ReadError):
                    f.canonical(u)
        finally:
            await f.close()
    asyncio.run(run())


def test_discovery_uses_declared_form_and_individual_links_only():
    async def run():
        c = SimpleNamespace(domains=('mercadolivre.com.br',), browser=False, delay=0)
        f = Fetcher(c)
        f.html = AsyncMock(side_effect=[
            ('<form method="GET" action="https://lista.mercadolivre.com.br/pesquisa"><input name="as_word"></form>', 'https://www.mercadolivre.com.br/'),
            (f'<a href="{URL}">Placa B550</a><a href="https://www.mercadolivre.com.br/p/MLB123">Placa B550</a>', 'https://lista.mercadolivre.com.br/pesquisa'),
        ])
        try:
            found = await DirectSearch(c, f).links('Placa B550')
            assert found == [URL] and not found.notices
        finally:
            await f.close()
    asyncio.run(run())


def test_search_limit_includes_fourth_store(monkeypatch):
    from monitor.adapters import ADAPTERS
    from monitor.discovery import LinkCandidate

    class FakeStore:
        name = 'Simulada'
        sitemap_urls = ()
        def search_url(self, query):
            return None
        def search_links(self, html, url):
            return [LinkCandidate(url.split('?')[0] + '/' + str(i), 'B550') for i in range(6)]

    async def run():
        domains = ('kabum.com.br', 'pichau.com.br', 'terabyteshop.com.br', 'mercadolivre.com.br')
        for domain in domains:
            monkeypatch.setitem(ADAPTERS, domain, FakeStore)
        c = SimpleNamespace(domains=domains, browser=False, delay=0)
        f = Fetcher(c)
        async def html(url):
            return '<form action="/search"><input name="q"></form>', url
        f.html = html
        try:
            found = await DirectSearch(c, f).links('B550')
            assert len(found) == 15
            assert {f.canonical(u)[1] for u in found} == set(domains)
        finally:
            await f.close()
    asyncio.run(run())
