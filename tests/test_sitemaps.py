import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.sitemaps import parse_sitemap, sitemap_candidates, MAX_DOCUMENTS
from monitor.adapters.pichau import PichauAdapter
from monitor.adapters.terabyte import TerabyteAdapter
from monitor.adapters.base import ReadError
from monitor.network import Fetcher
from monitor.discovery import DirectSearch


def xml(kind, entries):
    child = "url" if kind == "urlset" else "sitemap"
    return (
        "<"
        + kind
        + ' xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<{child}><loc>{url}</loc></{child}>" for url in entries)
        + "</"
        + kind
        + ">"
    )


def test_parse_sitemap_ignores_image_locations_and_rejects_entity():
    data = '<urlset xmlns:image="https://example.org/image"><url><loc>https://example.org/product</loc><image:image><image:loc>https://cdn.example.org/a.jpg</image:loc></image:image></url></urlset>'
    assert parse_sitemap(data) == ("urlset", ["https://example.org/product"])
    for invalid in ["<html></html>", "<urlset>", "<!DOCTYPE a><urlset/>"]:
        with pytest.raises(ReadError, match="invalid_sitemap"):
            parse_sitemap(invalid)


def test_pichau_sitemap_product_urls_cached_and_exact_filter():
    async def run():
        c = SimpleNamespace(domains=("pichau.com.br",), delay=1, browser=False)
        f = Fetcher(c)
        wanted = (
            "https://www.pichau.com.br/placa-mae-asus-rog-strix-b550-f-gaming-wifi-ii"
        )
        f.html = AsyncMock(
            return_value=(
                xml(
                    "urlset",
                    [
                        wanted,
                        "https://www.pichau.com.br/hardware",
                        "https://evil.org/placa-mae-b550",
                        "https://www.pichau.com.br/placa-mae-b650",
                    ],
                ),
                PichauAdapter.sitemap_urls[0],
            )
        )
        try:
            a = await DirectSearch(c, f).links("ROG STRIX B550-F GAMING WIFI II")
            assert a == [wanted] and not a.notices
            assert await DirectSearch(c, f).links(
                "ROG STRIX B550-F GAMING WIFI II"
            ) == [wanted]
            f.html.assert_awaited_once()
            assert f.html.await_args.args[0].endswith("/media/sitemap.xml")
        finally:
            await f.close()

    asyncio.run(run())


def test_terabyte_uses_sitemap_never_forbidden_search():
    async def run():
        c = SimpleNamespace(domains=("terabyteshop.com.br",), delay=1, browser=False)
        f = Fetcher(c)
        product = (
            "https://www.terabyteshop.com.br/produto/20306/placa-mae-b550-f-wifi-ii"
        )

        async def html(url):
            assert "/busca" not in url
            return xml("urlset", [product]), url

        f.html = AsyncMock(side_effect=html)
        try:
            found = await DirectSearch(c, f).links("b550")
            assert found == [product]
            assert all("/sitemap" in call.args[0] for call in f.html.await_args_list)
        finally:
            await f.close()

    asyncio.run(run())


def test_sitemap_index_limits_documents_and_rejects_external_hosts():
    async def run():
        c = SimpleNamespace(domains=("pichau.com.br",), delay=1)
        f = Fetcher(c)

        async def html(url):
            if url.endswith("/media/sitemap.xml"):
                return (
                    xml(
                        "sitemapindex",
                        [
                            f"https://www.pichau.com.br/media/part{i}.xml"
                            for i in range(10)
                        ]
                        + ["https://evil.org/a.xml"],
                    ),
                    url,
                )
            return xml("urlset", ["https://www.pichau.com.br/placa-mae-b550"]), url

        f.html = AsyncMock(side_effect=html)
        try:
            found = await sitemap_candidates(PichauAdapter(), "pichau.com.br", f)
            assert len(found) == 1 and f.html.await_count <= MAX_DOCUMENTS
        finally:
            await f.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "code",
    [
        "robots_disallowed",
        "blocked_no_bypass",
        "captcha_no_bypass",
        "robots_unavailable",
    ],
)
def test_sitemap_restriction_never_uses_browser_or_search(code):
    async def run():
        c = SimpleNamespace(domains=("terabyteshop.com.br",), delay=1, browser=True)
        f = Fetcher(c)
        f.html = AsyncMock(side_effect=ReadError(code))
        f.render = AsyncMock()
        try:
            found = await DirectSearch(c, f).links("b550")
            assert not found and len(found.notices) == 1
            f.render.assert_not_awaited()
            f.html.assert_awaited_once()
        finally:
            await f.close()

    asyncio.run(run())


def test_real_reduced_pichau_sitemap_snapshot():
    from pathlib import Path

    kind, links = parse_sitemap(
        Path("tests/fixtures/pichau_sitemap_real.xml").read_text(encoding="utf-8")
    )
    assert kind == "urlset" and len(links) == 2
    assert all("b550-f-gaming" in link for link in links)
    assert all(PichauAdapter().is_product_url(link) for link in links)
