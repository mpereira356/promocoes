import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.browser import ChromiumTransport
from monitor.challenges import is_access_challenge
from monitor.robots import RobotsPolicy
from monitor.adapters.base import ReadError
from monitor.adapters.pichau import PichauAdapter
from monitor.adapters.terabyte import TerabyteAdapter
from monitor.display_money import display_money
from monitor.network import Fetcher


def test_review_captcha_widget_does_not_block_public_product():
    html = Path("tests/fixtures/terabyte_product_browser_real.html").read_text(
        encoding="utf-8"
    )
    assert "g-recaptcha-response" in html
    assert not is_access_challenge(html)
    assert is_access_challenge(
        '<title>Just a moment</title><div class="cf-chl-test"></div>'
    )
    assert is_access_challenge('<div class="g-recaptcha"></div>')


def test_pichau_real_page_pix_is_not_unlabelled_schema_card_price():
    html = Path("tests/fixtures/pichau_product_browser_real.html").read_text(
        encoding="utf-8"
    )
    r = PichauAdapter().parse(html, "https://www.pichau.com.br/product")[0]
    assert r.price == 112999 and r.payment == "Pix" and r.seller == "Pichau"
    assert r.condition == "NewCondition" and r.stock == "in_stock" and r.comparable
    schema = json.loads(
        __import__("bs4").BeautifulSoup(html, "html.parser").find("script").string
    )
    assert str(r.price / 100) != schema["offers"]["price"]
    broken = html.replace("-price_vista-", "-other-layout-")
    assert (
        not PichauAdapter()
        .parse(broken, "https://www.pichau.com.br/product")[0]
        .payment
    )


def test_terabyte_real_page_keeps_unavailable_and_no_zero_price():
    html = Path("tests/fixtures/terabyte_product_browser_real.html").read_text(
        encoding="utf-8"
    )
    r = TerabyteAdapter().parse(
        html, "https://www.terabyteshop.com.br/produto/16143/test"
    )[0]
    assert r.stock == "out_of_stock" and r.seller == "TerabyteShop"
    assert r.price and r.price > 0 and not r.payment


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1.129,99", 112999),
        ("1,129.99", 112999),
        ("999.99", 99999),
        ("999,99", 99999),
        ("000,00", None),
        ("1.2.3,45", None),
        ("1.129", None),
    ],
)
def test_display_money_separators(text, expected):
    assert display_money(text) == expected


class Request:
    def __init__(self, url):
        self.url = url
        self.method = "GET"
        self.resource_type = "document"
        self.frame = SimpleNamespace(parent_frame=None)


class Route:
    def __init__(self, url):
        self.request = Request(url)
        self.aborted = False

    async def abort(self):
        self.aborted = True

    async def continue_(self):
        pass


class Response:
    status = 200

    def __init__(self, url, body):
        self.url = url
        self.body = body

    async def text(self):
        return self.body

    async def all_headers(self):
        return {
            "content-type": "text/html; charset=utf-8",
            "content-encoding": "gzip",
            "content-length": "10",
        }


class Context:
    def __init__(self, body):
        self.body = body
        self.callback = None
        self.closed = False

    async def route(self, pattern, callback):
        self.callback = callback

    async def new_page(self):
        return self

    async def goto(self, url, **kwargs):
        r = Route(url)
        await self.callback(r)
        if r.aborted:
            raise RuntimeError("aborted")
        return Response(url, self.body)

    async def close(self):
        self.closed = True


class Browser:
    def __init__(self, body):
        self.context = Context(body)

    async def new_context(self, **kwargs):
        assert kwargs["service_workers"] == "block"
        assert kwargs["user_agent"].startswith("PriceMonitor/")
        return self.context


def transport(body, allow=True):
    policy = RobotsPolicy("User-agent: *\n" + ("Allow: /" if allow else "Disallow: /"))
    f = SimpleNamespace(
        canonical=lambda u: (u, "pichau.com.br"),
        public=AsyncMock(),
        robots={"https://www.pichau.com.br": (0, policy)},
        config=SimpleNamespace(delay=0),
    )
    t = ChromiumTransport(f)
    t.browser = Browser(body)
    return t


def test_browser_response_does_not_decompress_decoded_body_twice():
    async def run():
        t = transport("<html>Pagina ja descomprimida</html>")
        response = await t.get("https://www.pichau.com.br/product")
        assert "Pagina ja descomprimida" in response.text
        assert "content-encoding" not in response.headers
        assert t.browser.context.closed

    asyncio.run(run())


def test_browser_robots_and_challenge_still_refused():
    async def run():
        t = transport("<html>product</html>", allow=False)
        with pytest.raises(ReadError, match="robots_disallowed"):
            await t.get("https://www.pichau.com.br/product")
        t = transport('<title>Just a moment</title><div class="cf-chl-test">')
        with pytest.raises(ReadError, match="captcha_no_bypass"):
            await t.get("https://www.pichau.com.br/product")
        assert t.browser.context.closed

    asyncio.run(run())


def test_http_routes_only_enabled_stores_to_chromium():
    async def run():
        f = Fetcher(
            SimpleNamespace(
                domains=("kabum.com.br", "pichau.com.br", "terabyteshop.com.br"),
                browser=True,
                delay=0,
            )
        )
        try:
            assert f.uses_browser("pichau.com.br") and f.uses_browser(
                "terabyteshop.com.br"
            )
            assert not f.uses_browser("kabum.com.br")
            f.config.browser = False
            assert not f.uses_browser("pichau.com.br")
        finally:
            await f.close()

    asyncio.run(run())


def test_optional_resource_dns_failure_does_not_mask_navigation_timeout():
    async def run():
        t = transport('<html/>')
        async def public(url):
            if url.endswith('.js'):
                raise OSError('simulated DNS failure')
        t.fetcher.public = public
        async def goto(url, **kwargs):
            resource = Route('https://www.pichau.com.br/optional.js')
            resource.request.resource_type = 'script'
            await t.browser.context.callback(resource)
            assert resource.aborted
            raise TimeoutError('simulated navigation timeout')
        t.browser.context.goto = goto
        with pytest.raises(ReadError, match='browser_navigation_failed_TimeoutError'):
            await t.get('https://www.pichau.com.br/product')
        assert t.browser.context.closed
    asyncio.run(run())


def test_browser_headers_with_accents_do_not_fail_response(monkeypatch):
    async def run():
        async def headers(self):
            return {'content-type': 'text/html; charset=utf-8', 'x-store-label': 'ação'}
        monkeypatch.setattr(Response, 'all_headers', headers)
        t = transport('<html>Produto</html>')
        response = await t.get('https://www.pichau.com.br/product')
        assert response.headers['x-store-label'] == 'ação'
        assert response.status_code == 200
    asyncio.run(run())


@pytest.mark.parametrize('fixture,parser,price', [
    ('pichau_ak820_unavailable_real.html', PichauAdapter, 21999),
    ('pichau_ak820pro_unavailable_real.html', PichauAdapter, 41999),
    ('terabyte_ak820pro_unavailable_real.html', TerabyteAdapter, 56990),
])
def test_real_reported_keyboard_pages_keep_price_and_unavailable(fixture, parser, price):
    html = Path('tests/fixtures', fixture).read_text(encoding='utf-8')
    reading = parser().parse(html, 'https://www.pichau.com.br/keyboard')[0]
    assert reading.price == price
    assert reading.stock == 'out_of_stock'


def test_real_terabyte_seo_title_and_cash_block_have_pix_and_boleto():
    html = Path('tests/fixtures/terabyte_cash_block_real.html').read_text(encoding='utf-8')
    url = 'https://www.terabyteshop.com.br/produto/36231/teclado-gamer-mecanico-corsair-k65-pro-mini-rgb-switch-corsair-opx-preto-ch-91a401a-na'
    readings = TerabyteAdapter().parse(html, url)
    assert {r.payment for r in readings} == {'Pix', 'Boleto'}
    assert all(r.price == 64999 and r.stock == 'in_stock' for r in readings)
    # MPN divergente no título ou URL de outra oferta impede vincular a modalidade.
    broken = html.replace('CH-91A401A-NA</h1>', 'OTHER-CODE</h1>')
    assert all(not r.payment for r in TerabyteAdapter().parse(broken, url))
    assert all(not r.payment for r in TerabyteAdapter().parse(html, url.replace('/36231/', '/99999/')))
    # Um segundo preço fora do modal torna a vinculação ambígua e é recusado.
    assert all(not r.payment for r in TerabyteAdapter().parse(html + '<p id="valVista">R$ 5,00</p>', url))
