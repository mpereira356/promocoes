import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from monitor.adapters import adapter
from monitor.adapters.base import ReadError
from monitor.challenges import is_access_challenge
from monitor.discovery import DirectSearch, form_search_url, relevance, reading_relevance, candidate_relevance, LinkCandidate
from monitor.network import Fetcher


FIXTURES = Path(__file__).with_name('fixtures')
SENSETUP = 'https://sensetup.com.br/products/cadeira-ergonomica-a08-premium'
ELEMENTS = 'https://loja.elements.com.br/products/cadeira-ergonomica-elements-galatea'
FLEXFORM = 'https://www.flexform.com.br/cadeiras/cadeiras-de-escritorio/uni-all-grey'


def fixture(name):
    return (FIXTURES / name).read_text(encoding='utf-8')


@pytest.mark.parametrize(('domain', 'url', 'name', 'price'), [
    ('sensetup.com.br', SENSETUP, 'sensetup_a08_real.html', 210000),
    ('loja.elements.com.br', ELEMENTS, 'elements_galatea_real.html', 288778),
    ('flexform.com.br', FLEXFORM, 'flexform_uni_real.html', 103050),
])
def test_real_reduced_product_documents(domain, url, name, price):
    reading, = adapter(domain).parse(fixture(name), url)
    assert reading.price == price and reading.currency == 'BRL'
    assert reading.image.startswith('https://')
    assert 'mpn' not in reading.identifiers  # SKU da loja nao e codigo do fabricante.
    assert not reading.comparable  # Nenhuma modalidade de pagamento inferida.


def mutate_product(change):
    soup = BeautifulSoup(fixture('elements_galatea_real.html'), 'html.parser')
    node = soup.select_one('script[type="application/json"]')
    data = json.loads(node.get_text())
    change(data)
    node.string = json.dumps(data)
    return str(soup)


def test_variant_stock_and_price_are_not_mixed():
    parser = adapter('loja.elements.com.br')
    html = fixture('elements_galatea_real.html')
    cinza, = parser.parse(html, ELEMENTS+'?variant=52318719738226')
    preta, = parser.parse(html, ELEMENTS+'?variant=52318705975666')
    assert cinza.stock == 'in_stock' and cinza.title.endswith('Cinza')
    assert preta.stock == 'out_of_stock' and preta.title.endswith('Preta')
    generic, = parser.parse(html, ELEMENTS)
    assert generic.stock == 'unknown'
    variable = mutate_product(lambda d: d['variants'][0].update(price=200000))
    generic, = parser.parse(variable, ELEMENTS)
    assert generic.price is None and generic.starting_price == 200000
    specific, = parser.parse(variable, ELEMENTS+'?variant=52318705975666')
    assert specific.price == 288778


@pytest.mark.parametrize('html', [
    mutate_product(lambda d: d.update(handle='outro-modelo')),
    mutate_product(lambda d: d.update(title='Outro modelo')),
    mutate_product(lambda d: d.update(variants=[])),
    fixture('elements_galatea_real.html').replace('"active":"BRL"', '"active":"USD"'),
])
def test_different_product_or_missing_currency_is_refused(html):
    with pytest.raises(ReadError):
        adapter('loja.elements.com.br').parse(html, ELEMENTS)


def test_bad_reading_is_not_zero_and_unknown_variant_is_refused():
    html = mutate_product(lambda d: d['variants'][0].update(price=0))
    reading, = adapter('loja.elements.com.br').parse(html, ELEMENTS)
    assert reading.price is None and reading.starting_price is None
    with pytest.raises(ReadError):
        adapter('loja.elements.com.br').parse(html, ELEMENTS+'?variant=999999')


def test_shopify_optional_captcha_script_is_not_an_access_challenge():
    html = ('<title>Sensetup</title><script>Shopify.shop = "sensetup.myshopify.com";'
            'const lib="shopifycloud/storefront-forms-hcaptcha";</script>'
            '<form action="/search"></form><a href="/products/cadeira-a08">Cadeira A08</a>')
    assert not is_access_challenge(html)
    assert is_access_challenge(html+'<div class="hcaptcha">Resolva o desafio</div>')
    assert is_access_challenge(html.replace('<title>Sensetup</title>', '<title>Just a moment</title>'))
    assert is_access_challenge(html+'<script src="/cf-chl-challenge"></script>')


def test_chair_matching_rejects_other_models_and_colors():
    assert relevance('cadeiras ergonomicas', 'Cadeira ergonomica Elements Galatea')
    assert candidate_relevance('Cadeira Sensetup', LinkCandidate(SENSETUP, 'cadeira ergonomica a08 premium'))
    assert relevance('Cadeira Elements Galatea', 'cadeira ergonomica elements galatea')
    assert not relevance('Cadeira Elements Galatea', 'cadeira ergonomica elements sophy')
    assert not relevance('Cadeira Uni All Grey', 'Cadeira Uni Pro Grey n Blue')
    assert not relevance('Cadeira A08', 'Mesa A08')
    reading, = adapter('loja.elements.com.br').parse(fixture('elements_galatea_real.html'), ELEMENTS)
    assert not reading_relevance('Cadeira Sensetup Galatea', reading)


@pytest.mark.parametrize('domain', ['sensetup.com.br', 'loja.elements.com.br', 'flexform.com.br'])
def test_chair_category_links_are_product_urls_from_same_store(domain):
    from monitor.deals.adapters import ADAPTERS
    from monitor.deals.catalog import CategoryCatalog
    category = CategoryCatalog().items['cadeiras/ergonomicas']
    assert domain in category.urls
    store = ADAPTERS[domain]
    html = fixture('chair_category_'+domain.replace('.', '_')+'_real.html')
    page = store.page(html, category.urls[domain])
    assert page.urls and all(adapter(domain).is_product_url(u) for u in page.urls)


def test_discount_reference_stays_bound_to_same_variant():
    from monitor.deals.adapters import ADAPTERS
    store = ADAPTERS['sensetup.com.br']
    html = fixture('sensetup_a08_real.html')
    reading, = adapter(store.domain).parse(html, SENSETUP)
    offer = store.offer(html, SENSETUP, reading)
    assert offer.previous == 239990 and offer.reading.price == 210000
    # Referencia nao representa queda historica nem confirma disponibilidade.
    assert offer.reading.stock == 'unknown' and not offer.reading.comparable


@pytest.mark.parametrize(('domain','url','name'), [
    ('sensetup.com.br', SENSETUP, 'sensetup_a08_real.html'),
    ('loja.elements.com.br', ELEMENTS, 'elements_galatea_real.html'),
    ('flexform.com.br', FLEXFORM, 'flexform_uni_real.html'),
])
def test_delivery_saves_price_and_finishes_without_creating_monitoring(domain, url, name):
    from monitor.db import DB
    from monitor.service import Monitor
    from monitor.search_results import deliver_search

    async def run():
        db = DB(':memory:')
        config = SimpleNamespace(domains=(domain,), browser=False, delay=3)
        fetcher = Fetcher(config)
        fetcher.html = AsyncMock(return_value=(fixture(name), url))
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        send = AsyncMock()
        monitor = Monitor(db, config, fetcher, None, send)
        try:
            await deliver_search(monitor, fetcher, db, bot, 42, url, send)
            assert len(db.rows('SELECT * FROM ads')) == 1
            assert not db.rows('SELECT * FROM products')
            assert bot.send_photo.await_count + bot.send_message.await_count == 1
            assert 'Com preço: 1' in send.await_args.args[0]
        finally:
            await fetcher.close()
            db.conn.close()
    asyncio.run(run())


def test_flexform_get_search_form_and_product_url_safety():
    url = form_search_url(fixture('flexform_search_form_real.html'), 'https://www.flexform.com.br/',
                          'Cadeira Uni All Grey', adapter('flexform.com.br').search_fields)
    assert '/busca?' in url and 'term=Cadeira+Uni+All+Grey' in url
    for domain, product in [('sensetup.com.br', SENSETUP), ('loja.elements.com.br', ELEMENTS), ('flexform.com.br', FLEXFORM)]:
        parser = adapter(domain)
        assert parser.is_product_url(product)
        assert not parser.is_product_url('https://evil.example'+product[product.index('/', 8):])
        assert not parser.is_product_url('https://'+domain+'/collections/cadeiras')


@pytest.mark.parametrize(('domain','url','query'), [
    ('sensetup.com.br', SENSETUP, 'Cadeira A08 Premium'),
    ('loja.elements.com.br', ELEMENTS, 'Cadeira Elements Galatea'),
])
def test_sitemap_discovery_without_external_api(domain, url, query):
    async def run():
        config = SimpleNamespace(domains=(domain,), browser=False, delay=3)
        fetcher = Fetcher(config)
        xml = '<urlset><url><loc>'+url+'</loc></url></urlset>'
        fetcher.html = AsyncMock(return_value=(xml, 'https://'+domain+'/sitemap.xml'))
        search = DirectSearch(config, fetcher)
        search.external_candidates = AsyncMock(side_effect=AssertionError('No external API'))
        try:
            results = await search.links(query)
            assert results == [url] and not results.notices
        finally:
            await fetcher.close()
    asyncio.run(run())
