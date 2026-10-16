import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.adapters.amazon import AmazonAdapter
from monitor.challenges import is_access_challenge
from monitor.discovery import DirectSearch, LinkCandidate, relevance
from monitor.external_market_search import ExternalMarketSearch
from monitor.identity import same_product
from monitor.identity import search_terms
from monitor.models import Reading
from monitor.network import Fetcher


@pytest.mark.parametrize('candidate', [
    'Teclado Mecânico Corsair K65 Pro Mini RGB Switch OPX',
    'Teclado Mecânico SuperFrame Player Pro RGB 60 Red',
    'Teclado Mecânico Fallen Pantera Pro TKL RGB',
    'Teclado Logitech G PRO X 60 LIGHTSPEED RGB',
    'Teclado Sem Fio Mecânico Gamer Logitech G515 RGB Bluetooth Lightspeed',
    'Teclado Mecânico Gamer Logitech G915 X Lightspeed RGB USB Bluetooth',
])
def test_logitech_g_pro_rejects_reported_wrong_brands_and_x_variant(candidate):
    assert relevance('Teclado Mecanico Logitech G PRO RGB', candidate) == 0


def test_logitech_g_pro_accepts_actual_model_and_generic_g_keeps_variants():
    correct = 'Teclado Mecânico Gamer Logitech G PRO Layout US RGB LIGHTSYNC Switch GX Blue 920-009388'
    assert relevance('Teclado Mecanico Logitech G PRO RGB', correct)
    assert relevance('Teclado Gamer Logitech G', 'Teclado Logitech G PRO X 60 RGB')


def test_exact_logitech_code_overrides_different_marketing_titles():
    kabum = 'Teclado Sem Fio Mecânico Gamer Logitech G PRO X 60 Lightspeed RGB Bluetooth Compatível com Windows Preto - 920-011902'
    pichau = 'Teclado Mecanico Logitech G Pro X Lightspeed RGB 60% Switch Optico GX Tactile Tri-Mode Preto 920-011902'
    assert search_terms(kabum) == 'Logitech 920-011902'
    assert relevance(kabum, pichau) == 1
    assert relevance(kabum, pichau.replace('920-011902', '920-011903')) == 0
    assert relevance(kabum, 'Capa para ' + pichau) == 0
    # O código descoberto no título auxilia a busca, sem confirmar identidade sozinho.
    a = Reading(kabum, '', '', '', None, identifiers={'brand': 'logitech g'})
    b = Reading(pichau, '', '', '', None, identifiers={'brand': 'logitech', 'mpn': '920 011902'})
    assert same_product(a, b) is None


def test_declared_mpn_is_preferred_over_marketing_title():
    ids = {'brand': 'logitech g', 'mpn': '920 011902'}
    assert search_terms('Descrição comprida', ids) == 'logitech 920-011902'
    assert ids == {'brand': 'logitech g', 'mpn': '920 011902'}


def test_direct_discovery_uses_part_code_for_external_lookup(monkeypatch):
    async def run():
        c = SimpleNamespace(domains=('pichau.com.br',), browser=False, delay=0)
        f = Fetcher(c)
        f.html = AsyncMock(return_value=('<urlset/>', 'https://www.pichau.com.br/media/sitemap.xml'))
        url = 'https://www.pichau.com.br/teclado-logitech-920-011902'
        lookup = AsyncMock(return_value=[LinkCandidate(url, 'Teclado Logitech GX Tactile 920-011902', 'Tavily Search')])
        monkeypatch.setattr(ExternalMarketSearch, 'links', lookup)
        try:
            links = await DirectSearch(c, f).links('Teclado Logitech G PRO X 60 sem fio Bluetooth Windows Preto 920-011902')
            assert links == [url]
            lookup.assert_awaited_once_with('Logitech 920-011902', 'pichau.com.br')
        finally:
            await f.close()
    asyncio.run(run())


@pytest.mark.parametrize('candidate', [
    'Placa Mae Gigabyte B550 Aorus Elite AX V2',
    'Placa Mae Gigabyte Aorus B550 Elite AX V2',
    'Placa Mae Gigabyte B550 Gaming X V2',
    'Placa Mae Gigabyte B650 Aorus Elite V2',
])
def test_aorus_elite_does_not_return_ax_gaming_x_or_different_chipset(candidate):
    assert relevance('Gigabyte B550 Aorus Elite V2', candidate) == 0


def test_variant_conflict_cannot_be_auto_confirmed_even_with_equal_identifier():
    seed = Reading('Gigabyte B550 Aorus Elite V2', '', '', '', None, identifiers={'mpn': 'same'})
    other = Reading('Gigabyte B550 Aorus Elite AX V2', '', '', '', None, identifiers={'mpn': 'same'})
    assert same_product(seed, other) is False


def test_accents_ordinals_and_separated_capacity_in_search():
    assert relevance('Echo Dot 5', 'Echo Dot 5ª geração') == 1
    assert relevance('SSD 500 GB', 'SSD 500GB') == 1
    assert relevance('Echo Dot 5', 'Suporte para Echo Dot 5') == 0


def test_pichau_empty_sitemap_uses_external_index_without_price_from_index(monkeypatch):
    async def run():
        c = SimpleNamespace(domains=('pichau.com.br',), browser=False, delay=0)
        f = Fetcher(c)
        url = 'https://www.pichau.com.br/placa-mae-gigabyte-b550-aorus-elite-v2'
        f.html = AsyncMock(return_value=('<urlset/>', 'https://www.pichau.com.br/media/sitemap.xml'))
        lookup = AsyncMock(return_value=[LinkCandidate(url, 'Gigabyte B550 Aorus Elite V2', 'Tavily Search')])
        monkeypatch.setattr(ExternalMarketSearch, 'links', lookup)
        try:
            links = await DirectSearch(c, f).links('Gigabyte B550 Aorus Elite V2')
            assert links == [url] and not links.notices
            lookup.assert_awaited_once_with('Gigabyte B550 Aorus Elite V2', 'pichau.com.br')
        finally:
            await f.close()
    asyncio.run(run())


def test_amazon_real_reduced_unavailable_page_never_invents_zero_or_seller():
    html = Path('tests/fixtures/amazon_unavailable_real.html').read_text(encoding='utf-8')
    r = AmazonAdapter().parse(html, 'https://www.amazon.com.br/dp/B08MPZ14FY')[0]
    assert 'B550 AORUS ELITE V2' in r.title
    assert r.stock == 'out_of_stock' and r.price is None
    assert not r.seller and not r.condition and not r.payment and not r.comparable


def test_amazon_challenge_is_not_a_product():
    assert is_access_challenge("<h1>JavaScript is disabled</h1>In order to continue, we need to verify that you're not a robot.")


def test_amazon_real_hidden_price_is_not_coupon_or_cart_price():
    html = Path('tests/fixtures/amazon_hidden_price_real.html').read_text(encoding='utf-8')
    r = AmazonAdapter().parse(html, 'https://www.amazon.com.br/dp/B09B8VGCR8')[0]
    assert 'Echo Dot' in r.title and r.seller == 'Amazon.com.br'
    assert r.price is None and r.stock == 'unknown' and not r.comparable


@pytest.mark.parametrize('url,expected', [
    ('https://www.amazon.com.br/name/dp/B08MPZ14FY', True),
    ('https://www.amazon.com.br/gp/product/B08MPZ14FY', True),
    ('https://www.amazon.com.br/s?k=b550', False),
    ('https://evil.org/dp/B08MPZ14FY', False),
])
def test_amazon_accepts_only_product_links(url, expected):
    assert AmazonAdapter().is_product_url(url) is expected
