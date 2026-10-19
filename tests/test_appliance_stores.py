"""Fixtures Frigelar capturadas; demais cenarios simulados, sem acesso a lojas."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from monitor.adapters import adapter
from monitor.adapters.base import ReadError
from monitor.discovery import DirectSearch, LinkCandidate, relevance
from monitor.identity import same_product
from monitor.models import Reading
from monitor.network import Fetcher


EOS = 'https://www.frigelar.com.br/freezer-vertical-eos-242-litros-ecogelo-efv300-110v/p/kit8956'
CONSUL = 'https://www.frigelar.com.br/freezer-vertical-consul-slim-142-litros-cvu20gbbna-220v/p/kit1199'
SHOPEE = 'https://shopee.com.br/Freezer-Brastemp-i.1648122739.58252082479'
MAGALU = 'https://www.magazineluiza.com.br/freezer-vertical-eos/p/fj08fac8dk/pi/frid/'


@pytest.mark.parametrize('url,fixture,price,stock', [
    (EOS, 'frigelar_eos_real.html', 248900, 'in_stock'),
    (CONSUL, 'frigelar_consul_real.html', 179308, 'out_of_stock'),
])
def test_captured_frigelar_price_and_availability(url, fixture, price, stock):
    html = (Path(__file__).with_name('fixtures') / fixture).read_text(encoding='utf-8')
    r, = adapter('frigelar.com.br').parse(html, url)
    assert r.price == price and r.stock == stock and r.condition == 'NewCondition'
    assert r.currency == 'BRL' and not r.payment and not r.seller
    assert not r.comparable  # Preco generico nao se torna Pix ou preco comparavel.


@pytest.mark.parametrize('domain,url', [('shopee.com.br', SHOPEE), ('magazineluiza.com.br', MAGALU)])
def test_simulated_structured_product_and_missing_offer(domain, url):
    parser = adapter(domain)
    data = {'@type': 'Product', 'name': 'Freezer Vertical Modelo Teste 220V',
            'offers': {'@type': 'Offer', 'price': '1999.90', 'priceCurrency': 'BRL',
                       'availability': 'https://schema.org/OutOfStock'}}
    r, = parser.parse('<script type="application/ld+json">'+json.dumps(data)+'</script>', url)
    assert r.price == 199990 and r.stock == 'out_of_stock'
    assert not r.payment and not r.seller and not r.comparable
    with pytest.raises(ReadError, match='structured_product_missing_or_ambiguous'):
        parser.parse('<html><script>/* JS shell, no offer */</script></html>', url)
    with pytest.raises(ReadError, match='individual_listing_required'):
        parser.parse('<html></html>', 'https://'+domain+'/list/Freezer/Vertical')


@pytest.mark.parametrize('domain,url', [('shopee.com.br', SHOPEE), ('magazineluiza.com.br', MAGALU), ('frigelar.com.br', EOS)])
def test_search_discovers_individual_links_and_discards_categories(domain, url):
    async def run():
        config = SimpleNamespace(domains=(domain,), browser=False)
        fetcher = Fetcher(config)
        search = DirectSearch(config, fetcher)
        # Simula sitemap vazio para exercitar a alternativa pelo índice.
        fetcher.html = AsyncMock(return_value=('<urlset/>', 'https://'+domain+'/productSitemap.xml'))
        search.external_candidates = AsyncMock(return_value=[
            LinkCandidate('https://'+domain+'/list/freezer', 'Freezer vertical'),
            LinkCandidate(url, 'Freezer Vertical Modelo Teste')])
        try:
            links = await search.links('freezer vertical')
            assert list(links) == [url]
            assert not links.notices
        finally:
            await fetcher.close()
    asyncio.run(run())


@pytest.mark.parametrize('title', ['Freezer Horizontal 220V', 'Gaveta para Freezer Vertical',
                                 'Termostato para Freezer Vertical', 'Refrigerador vertical'])
def test_freezer_query_excludes_other_types_and_parts(title):
    assert not relevance('freezer vertical', title)


def test_plural_and_conflicting_voltage_capacity_are_distinct():
    assert relevance('freezers verticais', 'Freezer Vertical EOS 242 Litros 110V')
    def r(title):
        return Reading(title, 'Loja', 'NewCondition', 'Pix', 10000,
                       identifiers={'mpn': 'same-code', 'brand': 'eos'})
    seed = r('Freezer Vertical EOS 242 Litros 110V')
    for title in ('Freezer Vertical EOS 242 Litros 220V', 'Freezer Vertical EOS 172 Litros 110V',
                  'Freezer Horizontal EOS 242 Litros 110V'):
        assert same_product(seed, r(title)) is False


def test_frigelar_sitemap_uses_product_slug_without_external_search():
    async def run():
        config = SimpleNamespace(domains=('frigelar.com.br',), browser=False)
        f = Fetcher(config)
        f.html = AsyncMock(return_value=('<urlset><url><loc>'+EOS+'</loc></url></urlset>',
                                       'https://www.frigelar.com.br/productSitemap.xml'))
        search = DirectSearch(config, f)
        search.external_candidates = AsyncMock(side_effect=AssertionError('No external search needed'))
        try:
            result = await search.links('freezer vertical EOS 242')
            assert list(result) == [EOS] and not result.notices
            assert '242 litros' in result.candidates[EOS].title
        finally:
            await f.close()
    asyncio.run(run())


def test_only_official_mobile_magalu_host_is_authorized():
    async def run():
        f = Fetcher(SimpleNamespace(domains=('magazineluiza.com.br',)))
        try:
            assert f.canonical(MAGALU.replace('www.', 'm.'))[1] == 'magazineluiza.com.br'
            with pytest.raises(ReadError):
                f.canonical(MAGALU.replace('www.', 'evil.'))
        finally:
            await f.close()
    asyncio.run(run())


@pytest.mark.parametrize('domains,updated', [
    ('kabum.com.br,pichau.com.br,terabyteshop.com.br', True),
    ('kabum.com.br,pichau.com.br,terabyteshop.com.br,mercadolivre.com.br,amazon.com.br,sensetup.com.br,loja.elements.com.br,flexform.com.br', True),
    ('amazon.com.br,frigelar.com.br', False),
])
def test_vps_upgrade_updates_standard_store_lists_but_preserves_custom(tmp_path, domains, updated):
    installer = Path('deploy/install-kali.sh').read_text(encoding='utf-8')
    script = installer.split('python3 - "$install_dir/.env" <<\'PY\'\n', 1)[1].split('\nPY', 1)[0]
    env = tmp_path / '.env'
    original = 'TELEGRAM_CHAT_ID=-123\nALLOWED_DOMAINS='+domains+'\nDATABASE_PATH=keep.sqlite\n'
    env.write_text(original, encoding='utf-8')
    subprocess.run([sys.executable, '-', str(env)], input=script, text=True, check=True, capture_output=True)
    result = env.read_text(encoding='utf-8')
    assert 'DATABASE_PATH=keep.sqlite' in result and 'TELEGRAM_CHAT_ID=-123' in result
    if updated:
        assert 'shopee.com.br,magazineluiza.com.br,frigelar.com.br' in result
    else:
        assert result == original
