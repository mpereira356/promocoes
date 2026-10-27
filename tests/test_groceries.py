import json
import pytest
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
