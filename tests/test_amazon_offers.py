import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.adapters.amazon import AmazonAdapter
from monitor.adapters.base import ReadError
from monitor.service import Monitor
from monitor.amazon_offers import AmazonOffersReader
from monitor.amazon_offers import browser_error

URL = 'https://www.amazon.com.br/Gigabyte-B550-AORUS-ELITE-AX/dp/B08KGVH7YC'
HTML = Path('tests/fixtures/amazon_aod_real.html').read_text(encoding='utf-8')


def test_real_aod_price_is_bound_to_seller_condition_and_product():
    r = AmazonAdapter().parse(HTML, URL)[0]
    assert r.price == 172711
    assert r.seller == 'Amazon Global (ID A2EB9PYM83FCP9)'
    assert r.condition == 'NewCondition'
    assert not r.payment and r.stock == 'unknown' and not r.comparable


def test_shipping_or_coupon_cannot_replace_main_offer_price():
    html = HTML.replace('</div></div>', '<span>Entrega R$ 8,90. Cupom R$ 20,00</span></div></div>')
    assert AmazonAdapter().parse(html, URL)[0].price == 172711
    assert AmazonAdapter().parse(HTML.replace('1.727,11', '000,00'), URL)[0].price is None


def test_segmented_price_is_read_and_conflicting_representations_are_refused():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(HTML, 'html.parser')
    label = soup.select_one('.apex-pricetopay-accessibility-label')
    label.decompose()
    assert AmazonAdapter().parse(str(soup), URL)[0].price == 172711
    soup = BeautifulSoup(HTML, 'html.parser')
    soup.select_one('.apex-pricetopay-accessibility-label').string = 'R$ 2.000,00'
    assert AmazonAdapter().parse(str(soup), URL)[0].price is None


def test_hidden_price_layout_uses_only_same_asin_public_panel():
    html = '<span id="productTitle">Produto real</span><div id="priceNotAvailable_feature_div">Preco oculto</div>'
    a = AmazonAdapter()
    assert a.hidden_price_panel_url(html, URL) == 'https://www.amazon.com.br/dp/B08KGVH7YC/ref=olp-opf-redir?aod=1'
    assert a.hidden_price_panel_url(html, 'https://evil.org/dp/B08KGVH7YC') is None
    assert a.hidden_price_panel_url('<span id="productTitle">Sem painel</span>', URL) is None


def test_aod_from_another_product_is_rejected():
    html = HTML.replace('id="aod-asin-title-text"', 'id="different-title"')
    with pytest.raises(ReadError, match='conflicting_product_title'):
        AmazonAdapter().parse(html, URL)


def test_buying_options_link_must_be_declared_for_same_asin():
    a = AmazonAdapter()
    html = '<div id="buybox-see-all-buying-choices"><a href="/gp/offer-listing/B08KGVH7YC/ref=dp_olp_unknown_mbc">Ver ofertas</a></div>'
    assert a.buying_options_url(html, URL).startswith('https://www.amazon.com.br/gp/offer-listing/B08KGVH7YC/')
    assert a.buying_options_url(html.replace('B08KGVH7YC', 'B08MPZ14FY'), URL) is None
    assert a.buying_options_url(html.replace('/gp/offer-listing/', 'https://evil.org/gp/offer-listing/'), URL) is None


def test_monitor_uses_browser_only_for_declared_options_when_price_missing():
    async def run():
        main = '<span id="productTitle">Gigabyte B550 AORUS ELITE AX V2</span><div id="buybox-see-all-buying-choices"><a href="/gp/offer-listing/B08KGVH7YC/ref=dp_olp_unknown_mbc">Ver ofertas</a></div>'
        f = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), html=AsyncMock(return_value=(main, URL)))
        m = Monitor(None, SimpleNamespace(browser=True), f, None, None)
        m.amazon_offers = SimpleNamespace(html=AsyncMock(return_value=HTML))
        r = await m.read(URL)
        assert r[0].price == 172711
        m.amazon_offers.html.assert_awaited_once()
    asyncio.run(run())


def test_robots_restriction_stops_selenium_before_start(monkeypatch):
    async def run():
        f = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), allowed_by_robots=AsyncMock(side_effect=ReadError('robots_disallowed')))
        reader = AmazonOffersReader(f)
        load = AsyncMock()
        monkeypatch.setattr(reader, '_load', load)
        with pytest.raises(ReadError, match='robots_disallowed'):
            await reader.html('https://www.amazon.com.br/gp/offer-listing/B08KGVH7YC/ref=test')
        load.assert_not_called()
    asyncio.run(run())


@pytest.mark.parametrize('message,expected', [
    ('tab crashed; private details', 'amazon_browser_crashed'),
    ('net::ERR_NAME_NOT_RESOLVED secret', 'amazon_browser_connection_failed'),
    ('net::ERR_TUNNEL_CONNECTION_FAILED secret', 'amazon_browser_connection_failed'),
    ('private unrelated details', 'amazon_browser_start_failed'),
])
def test_browser_failure_is_classified_without_private_details(message, expected):
    assert browser_error(RuntimeError(message), 'amazon_browser_start_failed') == expected


def test_real_cart_price_requirement_stops_before_selenium():
    async def run():
        html = Path('tests/fixtures/amazon_ak820_cart_price_real.html').read_text(encoding='utf-8')
        url = 'https://www.amazon.com.br/dp/B0H9BWD7NP'
        assert AmazonAdapter().price_requires_cart(html)
        assert not AmazonAdapter().price_requires_cart('<aside>adicione este item ao seu carrinho</aside>')
        f = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), html=AsyncMock(return_value=(html, url)))
        monitor = Monitor(None, SimpleNamespace(browser=True), f, None, None)
        monitor.amazon_offers = SimpleNamespace(html=AsyncMock())
        with pytest.raises(ReadError, match='amazon_price_requires_cart'):
            await monitor.read(url)
        monitor.amazon_offers.html.assert_not_called()
    asyncio.run(run())
