import json
import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from monitor.adapters import adapter
from monitor.adapters.groceries import AtacadaoAdapter, ExtraMercadoAdapter, CarrefourMercadoAdapter, BoaSupermercadosAdapter
from monitor.config import DEFAULT_DOMAINS

CASES = [
    (AtacadaoAdapter, 'https://www.atacadao.com.br/carne-bovina-picanha-maturatta-congelada-57030/p'),
    (ExtraMercadoAdapter, 'https://www.extramercado.com.br/produto/164337/picanha-resfriada-maturatta'),
    (CarrefourMercadoAdapter, 'https://mercado.carrefour.com.br/produto/picanha-resfriada-maturatta-4733378'),
    (BoaSupermercadosAdapter, 'https://www.boasupermercados.com.br/exemplo/p'),
]

@pytest.mark.parametrize('factory,url', CASES)
def test_registered_discovery_and_individual_pages(factory, url):
    store = adapter(factory.domain)
    assert isinstance(store, factory)
    assert factory.domain in DEFAULT_DOMAINS.split(',')
    assert store.external_discovery
    assert store.is_product_url(url)
    assert not store.is_product_url('https://' + factory.domain + '/categoria/carnes')
    assert not store.is_product_url(url.replace(factory.domain, 'evil.example'))
    assert not store.is_product_url(url.replace('https://', 'https://user@'))
    links = store.search_links('<a href="' + url + '">Picanha Maturatta</a>', url)
    assert any(link.url == url for link in links)

@pytest.mark.parametrize('factory,url', CASES)
@pytest.mark.parametrize('price', [0, 95.90, 143.85])
def test_unregionalized_or_pack_price_never_creates_comparable_alert(factory, url, price):
    product = {'@type': 'Product', 'name': 'Picanha Maturatta resfriada 1,5kg',
               'offers': {'@type': 'Offer', 'price': price, 'priceCurrency': 'BRL',
                          'seller': {'name': factory.name}, 'itemCondition': 'https://schema.org/NewCondition',
                          'acceptedPaymentMethod': 'Pix', 'availability': 'https://schema.org/InStock'}}
    html = '<script type="application/ld+json">' + json.dumps(product) + '</script>'
    reading, = factory().parse(html, url)
    assert reading.title == product['name']
    assert reading.price is None
    assert not reading.comparable
    assert reading.stock == 'unknown'
    assert reading.identifiers['regional_price_pending'] == 'true'


def test_meat_routing_preserves_general_search_and_prioritizes_groceries():
    from monitor.search_scope import search_domains
    configured = DEFAULT_DOMAINS.split(',')
    selected = search_domains('Picanha Maturatta', configured)
    assert selected[:4] == ('atacadao.com.br', 'extramercado.com.br',
                           'mercado.carrefour.com.br', 'boasupermercados.com.br')
    assert 'kabum.com.br' not in selected
    assert search_domains('faca para picanha', configured) == tuple(configured)
    assert search_domains('placa mãe AM5', configured) == tuple(configured)
    assert search_domains('picanha', ('kabum.com.br',)) == ()


@pytest.mark.parametrize('title', ['Hambúrguer de Picanha Maturatta 180g',
                                  'Tempero sabor picanha Maturatta',
                                  'Picanha congelada Maturatta 1kg'])
def test_meat_search_rejects_substitutes_and_wrong_storage(title):
    from monitor.discovery import relevance
    assert not relevance('Picanha resfriada Maturatta', title)


def test_native_carrefour_discovery_does_not_require_external_quota():
    from monitor.discovery import DirectSearch
    async def run():
        domain = 'mercado.carrefour.com.br'
        url = 'https://' + domain + '/produto/picanha-resfriada-maturatta-4733378'
        fetcher = SimpleNamespace(
            html=AsyncMock(return_value=('<a href="' + url + '">Picanha Maturatta</a>',
                          CarrefourMercadoAdapter().discovery_url('picanha'))),
            canonical=lambda u: (u, domain),
            external_market_search=SimpleNamespace(links=AsyncMock(side_effect=AssertionError('quota must not be used'))))
        search = DirectSearch(SimpleNamespace(domains=(domain,), browser=False), fetcher)
        links = await search.links('picanha')
        assert links == [url]
        fetcher.external_market_search.links.assert_not_called()
    asyncio.run(run())


def test_regional_links_never_receive_monitor_button_or_false_no_results():
    from monitor.discovery import SearchLinks, LinkCandidate
    from monitor.search_results import deliver_search
    from monitor.models import Reading
    async def run():
        domain = 'mercado.carrefour.com.br'
        url = 'https://' + domain + '/produto/picanha-resfriada-maturatta-4733378'
        reading = Reading('Picanha Maturatta', '', '', '', None,
                          identifiers={'regional_price_pending': 'true'})
        monitor = SimpleNamespace(
            search=SimpleNamespace(links=AsyncMock(return_value=SearchLinks([url], candidates={url: LinkCandidate(url, reading.title)}))),
            read=AsyncMock(return_value=[reading]))
        fetcher = SimpleNamespace(config=SimpleNamespace(domains=(domain,)), canonical=lambda u: (u, domain))
        db = SimpleNamespace(save_ad=AsyncMock(side_effect=AssertionError('must not create monitorable ad')))
        send = AsyncMock()
        await deliver_search(monitor, fetcher, db, None, 1, 'picanha', send)
        texts = [call.args[0] for call in send.await_args_list]
        assert any(url in text for text in texts)
        assert 'Pesquisa finalizada' in texts[-1]
        assert 'CEP' in texts[-1]
        assert 'não significa que o produto esteja esgotado' in texts[-1]
        assert not any('Não encontramos ofertas' in text for text in texts)
        db.save_ad.assert_not_called()
    asyncio.run(run())


def test_regional_notices_have_correct_accents_and_are_grouped():
    from monitor.message_style import summarize_notices
    assert AtacadaoAdapter.name == 'Atacadão'
    text = '\n'.join(summarize_notices([
        f'{factory.name}: preços regionais ainda não disponíveis; falta validar CEP, loja e unidade de venda.'
        for factory, _ in CASES]))
    assert text.count('Preços regionais pendentes:') == 1
    assert 'Atacadão' in text and '?' not in text
