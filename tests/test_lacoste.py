"""Simulações de HTML e rede: não são capturas nem validações ao vivo."""
import asyncio
import json
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from monitor.adapters.lacoste import LacosteAdapter
from monitor.adapters.base import ReadError
from monitor.deals.adapters.lacoste import LacosteCategories
from monitor.deals.catalog import CategoryCatalog
from monitor.deals.models import DiscountFilter, parse_size
from monitor.deals.service import Deals, select_offers
from monitor.deals.telegram import PromotionsTelegram
from monitor.deals.formatting import messages
from monitor.deals.identity import comparable
from monitor.identity import same_product
from monitor.network import Fetcher

URL = 'https://www.lacoste.com/br/lacoste/masculino/camisetas/TH6710-23.html?color=001'


def product_html(*, stock='InStock', sizes=True, price='299.00', old='429.00'):
    product = {'@type': 'Product', 'name': 'Camiseta Pima', 'url': URL,
               'mpn': 'TH6710-23', 'brand': {'name': 'Lacoste'}, 'color': 'Branco',
               'offers': {'@type': 'Offer', 'price': price, 'priceCurrency': 'BRL',
                          'availability': 'https://schema.org/' + stock,
                          'priceSpecification': {'priceType': 'https://schema.org/StrikethroughPrice',
                                                 'price': old, 'priceCurrency': 'BRL'}}}
    html = '<main><h1>Camiseta Pima</h1><script type="application/ld+json">' + json.dumps(product) + '</script>'
    if sizes:
        html += ('<button data-size="M" data-available="true" data-color-code="001">M</button>'
                 '<button data-size="G" data-available="false">G</button>'
                 '<button data-size="P">P</button>'
                 '<button data-size="GG" data-available="true" disabled>GG</button>'
                 '<aside><button data-size="XG" data-available="true">XG</button></aside>'
                 '<button data-size="42" data-available="true" data-color-code="031">42</button>')
    return html + '</main>'


def offer(html=None, url=URL):
    html = html or product_html()
    reading = LacosteAdapter().parse(html, url)[0]
    return LacosteCategories().offer(html, url, reading)


@pytest.mark.parametrize('expression,expected', [('<30', False), ('<=30', True), ('<30,1', True),
                                                ('<=29.9', False), ('>30', False), ('>=30', True)])
def test_discount_boundaries(expression, expected):
    f = DiscountFilter.parse(expression)
    assert f.accepts(100000, 70000) is expected
    assert not f.accepts(100000, 100000)
    assert not f.accepts(None, 70000)
    assert str(DiscountFilter.parse(str(f))) == str(f)


def test_lacoste_price_sizes_and_color():
    o = offer()
    assert o.reading.price == 29900 and o.previous == 42900
    assert o.available_sizes == ['M']
    assert o.color == 'Branco'
    assert o.reading.payment == ''  # No invented Pix or instalment total.
    assert offer(product_html(sizes=False)).available_sizes == []
    assert offer(product_html(stock='OutOfStock')).reading.stock == 'out_of_stock'


def test_wrong_product_and_color_are_rejected():
    with pytest.raises(ReadError):
        offer(url=URL.replace('001', '031'))
    with pytest.raises(ReadError):
        offer(url=URL.replace('TH6710', 'TH9999'))


def test_other_colors_are_not_merged_or_compared():
    a = offer()
    b = replace(a, reading=replace(a.reading, identifiers={**a.reading.identifiers, 'color': '031'}))
    assert not comparable(a, b)
    assert same_product(a.reading, b.reading) is False
    assert len(select_offers([a, b], DiscountFilter.parse('>0'))) == 2


def test_no_aggregate_or_cart_discount_as_total():
    html = product_html().replace('"@type": "Offer"', '"@type": "AggregateOffer"')
    assert offer(html).reading.price is None
    html = product_html(old='299.00') + '<aside>+20% OFF no carrinho <del>R$ 999,00</del></aside>'
    assert offer(html).previous is None


@pytest.mark.parametrize('size,count', [('M', 1), ('G', 0), ('P', 0), ('42', 0), ('', 1)])
def test_size_filter_reaches_actual_deals_and_summary(size, count):
    async def run():
        config = SimpleNamespace(domains=('lacoste.com',), browser=False)
        html = product_html()
        fetcher = Fetcher(config)
        fetcher.html = AsyncMock(return_value=(f'<a href="{URL}">Camiseta Pima</a>', 'https://www.lacoste.com/br/lacoste/sale/'))
        monitor = SimpleNamespace(config=config, fetcher=fetcher,
                                  read_snapshot=AsyncMock(return_value=(LacosteAdapter().parse(html, URL), html, URL)))
        try:
            report = await Deals(monitor).run('lacoste/sale', DiscountFilter.parse('>25'), config.domains, size=size, validation='announced')
            assert len(report.results) == count
            assert report.size == size
            assert 'Tamanho:' in '\n'.join(messages(report))
        finally:
            await fetcher.client.aclose()
    asyncio.run(run())


def test_search_links_pagination_and_brazil_only():
    page = LacosteCategories().page(f'<a href="{URL}">Camiseta</a><a href="?page=2" rel="next">Mais</a>'
                                    '<a href="https://www.lacoste.com/fr/TH6710.html">FR</a>',
                                    'https://www.lacoste.com/br/lacoste/sale/')
    assert page.urls == [URL]
    assert page.next_url.endswith('?page=2')
    assert 'q=polo+verde' in LacosteAdapter().search_url('polo verde')
    assert parse_size('todos') == ''
    with pytest.raises(ValueError):
        parse_size('M ou G')


def test_telegram_lacoste_discount_size_and_execution():
    async def run():
        config = SimpleNamespace(domains=('lacoste.com', 'kabum.com.br'), user=1, chat=2)
        background = []
        deals = SimpleNamespace(catalog=CategoryCatalog(), run=AsyncMock())
        controller = PromotionsTelegram(config, deals, AsyncMock(), background.append)
        reply = AsyncMock()
        controller.new_session()
        await controller.select(deals.catalog.items['lacoste/sale'], reply)
        assert controller.session.stores == set()
        markup = reply.call_args.kwargs['reply_markup']
        assert any(b.callback_data.endswith(':gt30') for row in markup.inline_keyboard for b in row)
        message = SimpleNamespace(reply_text=AsyncMock())
        query = SimpleNamespace(data='', message=message, answer=AsyncMock())
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1), effective_chat=SimpleNamespace(id=2))
        def action(value):
            query.data = f'promo:{controller.session.nonce}:{controller.session.revision}:{value}'
        action('gt30')
        await controller.callback(update, None)
        assert controller.session.stage == 'size'
        action('sizeM')
        await controller.callback(update, None)
        assert controller.session.stage == 'stores' and controller.session.size == 'M'
        action('store0')
        await controller.callback(update, None)
        action('run')
        await controller.callback(update, None)
        assert len(background) == 1
        # Return a real report so formatting and final delivery are also exercised.
        from monitor.deals.models import DealReport
        deals.run.return_value = DealReport([], [], DiscountFilter.parse('<30'), 'lacoste/sale', category_title='Lacoste', size='M')
        await background[0]
        assert deals.run.call_args.kwargs == {'size': 'M', 'depth': 'expanded', 'validation': 'market'}
        assert deals.run.call_args.args[2] == ['lacoste.com']
    asyncio.run(run())


def test_real_lacoste_shirt_price_reference_and_color():
    html = Path('tests/fixtures/lacoste_product_real.html').read_text(encoding='utf-8')
    url = 'https://www.lacoste.com/br/lacoste/masculino/vestu%C3%A1rio/camisetas/TH6710-23.html?color=001'
    r = LacosteAdapter().parse(html, url)[0]
    result = LacosteCategories().offer(html, url, r)
    assert r.price == 29900 and result.previous == 42900
    assert result.color == 'Branco'
    assert r.identifiers['mpn'] == 'th6710 23 001'
    assert result.available_sizes == []  # Size endpoint is not requested.


def test_real_lacoste_ean_alias_has_verified_single_size():
    html = Path('tests/fixtures/lacoste_cap_real.html').read_text(encoding='utf-8')
    url = 'https://www.lacoste.com/br/lacoste/3666165004870.html'
    r = LacosteAdapter().parse(html, url)[0]
    result = LacosteCategories().offer(html, url, r)
    assert r.price == 46900 and r.stock == 'in_stock'
    assert result.available_sizes == ['TU'] and result.color == 'Azul Marinho'
    assert r.identifiers['mpn'] == 'rk2662 23 166'
    with pytest.raises(ReadError):
        LacosteAdapter().parse(html, url.replace('3666165004870', '9999999999999'))
    with pytest.raises(ReadError):
        LacosteAdapter().parse(html, url + '?color=001')
    with pytest.raises(ReadError):
        LacosteAdapter().parse(html, url + '?size=M')
