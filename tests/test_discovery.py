import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from monitor.adapters.kabum import KabumAdapter
from monitor.adapters.terabyte import TerabyteAdapter
from monitor.adapters.base import ReadError
from monitor.discovery import DirectSearch, relevance, form_search_url
from monitor.network import Fetcher
from monitor.search import Search


def config(domains=("kabum.com.br",)):
    return SimpleNamespace(
        domains=domains, provider="direct", key="", browser=False, delay=1
    )


def catalog(items):
    data = {"props": {"pageProps": {"data": {"catalogServer": {"data": items}}}}}
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(data)
        + "</script>"
    )


def test_real_reduced_kabum_catalog_snapshot():
    html = Path("tests/fixtures/kabum_catalog_real.html").read_text(encoding="utf-8")
    found = KabumAdapter().search_links(html, "https://www.kabum.com.br/busca/b550")
    assert len(found) == 3
    assert found[0].url.startswith("https://www.kabum.com.br/produto/692460/")
    assert found[0].title.startswith("Placa-Mãe Husky")
    assert not hasattr(found[0], "price")


def test_real_serialized_vacuum_catalog_excludes_breadcrumb_categories():
    html = Path('tests/fixtures/kabum_vacuum_catalog_real.html').read_text(encoding='utf-8')
    store = KabumAdapter()
    found = store.search_links(html, 'https://www.kabum.com.br/eletroportateis/aspirador-de-po/aspirador-de-po-portatil')
    assert len(found) == 3
    assert all(store.is_product_url(c.url) for c in found)
    assert not any('/eletroportateis/' in c.url for c in found)
    assert all(not hasattr(c, 'price') for c in found)


@pytest.mark.parametrize('url,valid', [
    ('https://www.kabum.com.br/produto/625300/aspirador', True),
    ('https://kabum.com.br/produto/625300', True),
    ('https://www.kabum.com.br/eletroportateis/aspirador-de-po', False),
    ('https://www.kabum.com.br/busca/aspirador', False),
    ('https://evil.example/produto/625300/aspirador', False),
])
def test_kabum_individual_product_url_contract(url, valid):
    assert KabumAdapter().is_product_url(url) is valid


def test_kabum_category_cannot_be_parsed_as_individual_offer():
    html = '<script type="application/ld+json">' + json.dumps({'@type': 'Product', 'name': 'Recomendação', 'offers': {'@type': 'Offer', 'price': 1}}) + '</script>'
    with pytest.raises(ReadError, match='individual_listing_required'):
        KabumAdapter().parse(html, 'https://www.kabum.com.br/eletroportateis/aspirador-de-po')


@pytest.mark.parametrize(
    "title",
    [
        "Placa Mae Asus ROG STRIX X870-F GAMING WIFI II",
        "Placa Mae Asus ROG STRIX B650-F GAMING WIFI II",
        "Teclado gamer RGB",
    ],
)
def test_different_chipset_not_suggested(title):
    assert relevance("Placa Mae Asus ROG STRIX B550-F GAMING WIFI II", title) == 0


def test_compatible_title_and_wifi_normalization():
    assert (
        relevance("ROG STRIX B550-F GAMING WIFI II", "ROG Strix B550-F Gaming Wi-Fi II")
        == 1
    )


def test_search_form_uses_declared_get_only():
    assert (
        form_search_url(
            '<form action="/search"><input name="q"></form>',
            "https://www.pichau.com.br/",
            "asus b550",
        )
        == "https://www.pichau.com.br/search?q=asus+b550"
    )
    with pytest.raises(ReadError, match="search_form_not_supported"):
        form_search_url(
            '<form method="post" action="/search"><input name="q"></form>',
            "https://www.pichau.com.br/",
            "b550",
        )


def test_no_made_up_url_for_malformed_catalog():
    items = [
        {"code": "bad", "friendlyName": "some-product", "name": "b550"},
        {"code": 1, "friendlyName": "//evil.org", "name": "b550"},
    ]
    assert not KabumAdapter().search_links(catalog(items), "https://www.kabum.com.br/")


def test_terabyte_only_product_paths():
    html = '<a href="/produto/20306/placa-mae">ROG B550-F WiFi II</a><a href="/busca?str=b550">b550</a>'
    found = TerabyteAdapter().search_links(html, "https://www.terabyteshop.com.br/")
    assert len(found) == 1 and "/produto/20306/" in found[0].url


def test_direct_no_api_and_deduplicated_links():
    async def run():
        c = config()
        f = Fetcher(c)
        f.html = AsyncMock(
            return_value=(
                catalog(
                    [
                        {
                            "code": 42,
                            "friendlyName": "placa-b550",
                            "name": "Placa B550",
                        },
                        {
                            "code": 42,
                            "friendlyName": "placa-b550",
                            "name": "Placa B550",
                        },
                        {
                            "code": 99,
                            "friendlyName": "placa-b650",
                            "name": "Placa B650",
                        },
                    ]
                ),
                "https://www.kabum.com.br/busca/b550",
            )
        )
        try:
            search = Search(c, f)
            assert search.configuration_error() is None
            with patch("monitor.search.httpx.AsyncClient") as external:
                found = await search.links("b550")
                external.assert_not_called()
            assert found == ["https://www.kabum.com.br/produto/42/placa-b550"]
            assert not found.notices
        finally:
            await f.close()

    asyncio.run(run())


def test_blocked_store_does_not_hide_success():
    async def run():
        c = config(("kabum.com.br", "pichau.com.br"))
        f = Fetcher(c)

        async def html(url):
            if "pichau.com.br" in url:
                raise ReadError("blocked_no_bypass")
            return (
                catalog(
                    [{"code": 42, "friendlyName": "placa-b550", "name": "Placa B550"}]
                ),
                url,
            )

        f.html = AsyncMock(side_effect=html)
        try:
            found = await DirectSearch(c, f).links("b550")
            assert len(found) == 1
            assert "Pichau" in found.notices[0] and "bloqueou o acesso" in found.notices[0]
            assert (
                f.html.await_count == 2
            )  # Nenhuma segunda tentativa para contornar 403.
        finally:
            await f.close()

    asyncio.run(run())


def test_unknown_store_and_empty_search_reported():
    async def run():
        c = config(("kabum.com.br", "example.org"))
        f = Fetcher(c)
        f.html = AsyncMock(
            return_value=("<html></html>", "https://www.kabum.com.br/busca/b550")
        )
        try:
            found = await DirectSearch(c, f).links("b550")
            assert not found
            assert len(found.notices) == 2
        finally:
            await f.close()

    asyncio.run(run())
