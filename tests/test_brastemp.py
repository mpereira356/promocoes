"""Fixtures públicas reduzidas da Brastemp; mutações e transporte simulados."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from monitor.adapters import adapter
from monitor.adapters.base import ReadError
from monitor.deals.adapters.brastemp import BrastempCategories
from monitor.deals.catalog import CategoryCatalog
from monitor.discovery import DirectSearch, reading_relevance
from monitor.identity import same_product
from monitor.network import Fetcher


ROOT = Path(__file__).with_name('fixtures')
URL = 'https://www.brastemp.com.br/freezer-vertical-flex-frost-free-brastemp/p'
URL220 = 'https://www.brastemp.com.br/freezer-vertical-flex-frost-free-brastemp-326196070/p'
UNAVAILABLE = 'https://www.brastemp.com.br/freezer-vertical-brastemp-flex-frost-free-228-litros---bvr28nk-326031140/p'


def fixture(name='brastemp_bvr28pb_110_real.html'):
    return (ROOT / name).read_text(encoding='utf-8')


def changed(mutate):
    soup = BeautifulSoup(fixture(), 'html.parser')
    script = soup.select_one('#__NEXT_DATA__')
    data = json.loads(script.get_text())
    mutate(data['props']['pageProps']['data']['product'])
    script.string = json.dumps(data)
    return str(soup)


def test_captured_versions_have_exact_model_voltage_and_total_card_price():
    parser = adapter('brastemp.com.br')
    a, = parser.parse(fixture(), URL)
    b, = parser.parse(fixture('brastemp_bvr28pb_220_real.html'), URL220)
    assert a.price == b.price == 364900  # Captura, nao promessa de preco atual.
    assert a.title.endswith('110V') and b.title.endswith('220V')
    assert a.identifiers['model'] == b.identifiers['model'] == 'bvr28pb'
    assert a.identifiers['gtin'] != b.identifiers['gtin']
    assert a.payment == b.payment == 'Cartão à vista (American Express)'
    assert a.seller == 'Vendedor ID 1' and a.stock == 'in_stock'
    assert a.comparable and b.comparable
    assert same_product(a, b) is False
    assert reading_relevance('freezer BVR28PB 220V', a) == 0


def test_unavailable_product_keeps_published_price_without_claiming_stock():
    r, = adapter('brastemp.com.br').parse(fixture('brastemp_bvr28nk_unavailable_real.html'), UNAVAILABLE)
    assert r.stock == 'out_of_stock' and r.price == 480900
    assert not r.payment and not r.comparable


@pytest.mark.parametrize('query', ['?idsku=999999999', '?idsku=326196069&idsku=326196070'])
def test_requested_sku_must_match_page(query):
    with pytest.raises(ReadError, match='different_model'):
        adapter('brastemp.com.br').parse(fixture(), URL+query)


@pytest.mark.parametrize('mutation,reason', [
    (lambda p: p.update(sku='999999999'), 'conflicting_product_identifiers'),
    (lambda p: p.update(gtin='7891129588707'), 'conflicting_product_identifiers'),
    (lambda p: p['isVariantOf']['skuVariants']['activeVariations'].update(Voltagem='220V'), 'conflicting_product_identifiers'),
    (lambda p: p['offers']['offers'][0].update(price=100), 'ambiguous_offer_variants'),
    (lambda p: p['offers']['offers'][0].update(availability='https://schema.org/OutOfStock'), 'ambiguous_offer_variants'),
])
def test_conflicts_never_produce_an_offer(mutation, reason):
    with pytest.raises(ReadError, match=reason):
        adapter('brastemp.com.br').parse(changed(mutation), URL)


def test_installment_values_never_become_total_or_pix():
    def mutation(p):
        p['availableInstallments'] = [dict(installmentNumber=10, installmentInterest=0,
            installmentPaymentSystemName='Visa', installmentValue=364.90, totalValuePlusInterestRate=3649)]
    r, = adapter('brastemp.com.br').parse(changed(mutation), URL)
    assert r.price == 364900 and not r.payment and not r.comparable


def test_reference_price_is_from_the_same_validated_offer():
    html = fixture()
    r, = adapter('brastemp.com.br').parse(html, URL)
    result = BrastempCategories().offer(html, URL, r)
    assert result.previous == 525800
    assert 30 < result.percent < 31
    r.seller = 'Outro vendedor'
    assert BrastempCategories().offer(html, URL, r).previous is None


def test_real_category_links_and_menu_do_not_accept_category_as_product():
    url = 'https://www.brastemp.com.br/eletrodomesticos/freezer/vertical'
    page = BrastempCategories().page(fixture('brastemp_vertical_category_real.html'), url)
    assert page.urls and all(adapter('brastemp.com.br').is_product_url(u) for u in page.urls)
    assert any(c.key == 'eletrodomesticos/freezers-verticais' for c in CategoryCatalog().available(('brastemp.com.br',)))
    with pytest.raises(ReadError, match='individual_listing_required'):
        adapter('brastemp.com.br').parse(fixture(), url)


def test_sitemap_discovery_needs_no_external_api():
    async def run():
        config = SimpleNamespace(domains=('brastemp.com.br',), browser=False)
        f = Fetcher(config)
        url = UNAVAILABLE
        f.html = AsyncMock(return_value=('<urlset><url><loc>'+url+'</loc></url></urlset>', 'https://www.brastemp.com.br/sitemap/product-0.xml'))
        search = DirectSearch(config, f)
        search.external_candidates = AsyncMock(side_effect=AssertionError('External API not needed'))
        try:
            links = await search.links('freezer vertical Brastemp BVR28NK')
            assert list(links) == [url] and not links.notices
        finally:
            await f.close()
    asyncio.run(run())
