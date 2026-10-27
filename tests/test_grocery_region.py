import asyncio
import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from monitor.adapters import adapter
from monitor.adapters.base import ReadError
from monitor.db import DB
from monitor.grocery_prices import GroceryPrices
from monitor.grocery_profile import load_profile, save_profile
from monitor.models import Reading
from monitor.network import Fetcher

CEP = '01001000'
URL = 'https://www.extramercado.com.br/produto/123/picanha-maturatta'


def sample():
    return {'status': 'success', 'content': {
        'id': 123, 'name': 'Picanha resfriada Maturatta 1,5kg', 'brand': 'Maturatta',
        'urlDetails': '/produto/123/picanha-maturatta', 'variableWeight': True,
        'thumbPath': '/img/uploads/1/test.jpg', 'sellInfos': [{
            'storeId': 7, 'sellType': '1P', 'stock': True, 'stockQuantity': 5,
            'currentPrice': 150, 'sellPrice': 150, 'comparativePrice': '1kg - R$ 100,00',
            'variableWeightPrice': {'sellPrice': 100, 'currentPrice': 100, 'productPromotions': []}}]}}


def reader(response=None, deliveries=None):
    obj = GroceryPrices(SimpleNamespace(config=SimpleNamespace(delay=0)))
    obj.extra_json = AsyncMock(side_effect=[
        {'deliveryTypes': deliveries if deliveries is not None else [
            {'type': 'normal', 'storeid': 7, 'storeName': 'Loja de teste'}]}, response or sample()])
    return obj


def test_region_profile_survives_restart_and_overrides_environment(tmp_path):
    path = str(tmp_path / 'db.sqlite')
    db = DB(path)
    config = SimpleNamespace(grocery_postal_code='')
    assert save_profile(db, config, '01001-000') == '01001-000'
    db.conn.close()
    db = DB(path)
    config.grocery_postal_code = '99999999'
    load_profile(db, config)
    assert config.grocery_postal_code == CEP
    for invalid in ('', '123', '０１００１０００', '01001000&store=5'):
        with pytest.raises(ValueError):
            save_profile(db, config, invalid)
    assert config.grocery_postal_code == CEP
    db.conn.close()


def test_extra_selects_delivery_store_and_uses_kg_not_pack_total():
    async def run():
        obj = reader()
        reading, = await obj.read(adapter('extramercado.com.br'), '', URL, CEP)
        assert reading.price == 10000  # Not 15000 for the estimated 1.5kg pack.
        assert reading.public_unit_price and reading.comparable
        assert reading.payment == ''  # No invented Pix / card condition.
        assert reading.condition == 'Resfriada · preço por kg'
        assert '01001-000' in reading.seller
        assert reading.identifiers['store_id'] == '7'
        assert 'isClienteMais=false' in obj.extra_json.await_args_list[1].args[0]
        from monitor.presentation import offer_text
        text = offer_text(reading, 'Extra Mercado')
        assert 'Preço público por kg' in text and 'Pagamento não confirmado' in text
        assert 'Alertas suspensos' not in text
    asyncio.run(run())


@pytest.mark.parametrize('field,value,code', [
    ('storeId', 8, 'regional_response_invalid'),
    ('comparativePrice', '1kg - R$ 150,00', 'regional_unit_unverified'),
    ('comparativePrice', '1 un - R$ 100,00', 'regional_unit_unverified'),
    ('nominalPrice', True, 'regional_terms_unverified'),
])
def test_extra_rejects_wrong_store_unit_and_unverified_terms(field, value, code):
    async def run():
        response = sample()
        response['content']['sellInfos'][0][field] = value
        with pytest.raises(ReadError, match=code):
            await reader(response).read(adapter('extramercado.com.br'), '', URL, CEP)
    asyncio.run(run())


def test_extra_requires_actual_delivery_not_just_a_recognized_postal_code():
    async def run():
        obj = reader(deliveries=[{'type': 'pickup', 'storeid': 7, 'storeName': 'Retirada'}])
        with pytest.raises(ReadError, match='regional_delivery_unavailable'):
            await obj.read(adapter('extramercado.com.br'), '', URL, CEP)
        assert obj.extra_json.await_count == 1
    asyncio.run(run())


@pytest.mark.parametrize('stock,quantity', [(False, 0), (True, 0), (None, 5)])
def test_extra_missing_stock_does_not_offer_a_monitorable_price(stock, quantity):
    async def run():
        response = sample()
        offer = response['content']['sellInfos'][0]
        offer['stock'], offer['stockQuantity'] = stock, quantity
        reading, = await reader(response).read(adapter('extramercado.com.br'), '', URL, CEP)
        assert reading.price is None and not reading.comparable
        assert reading.identifiers['regional_price_pending'] == 'true'
    asyncio.run(run())


def test_extra_discovery_never_trusts_prices_or_foreign_product_urls():
    async def run():
        obj = reader()
        obj.extra_json.side_effect = [
            {'deliveryTypes': [{'type': 'normal', 'storeid': 7, 'storeName': 'Teste'}]},
            {'products': [
                {'id': 123, 'name': 'Picanha Maturatta', 'urlDetails': URL, 'price': 1},
                {'id': 456, 'name': 'Picanha', 'urlDetails': URL},
                {'id': 123, 'name': 'Picanha', 'urlDetails': 'https://evil.example/produto/123/picanha'}]}]
        links = await obj.discover_extra('picanha', CEP)
        assert len(links) == 1 and links[0].url == URL
        assert not hasattr(links[0], 'price')
        assert obj.extra_json.await_args.args[1]['customerPlus'] is False
    asyncio.run(run())


def test_price_drop_alert_is_per_kg_and_region_change_creates_new_baseline(tmp_path):
    async def run():
        reading, = await reader().read(adapter('extramercado.com.br'), '', URL, CEP)
        db = DB(str(tmp_path / 'test.sqlite'))
        config = SimpleNamespace(minimum=0, percent=Decimal('0'), target=None, interval=18000)
        pid = db.add('Picanha Maturatta', config)
        candidate = db.candidate(pid, URL, 'Extra Mercado')
        db.record(candidate, reading)
        db.run('UPDATE candidates SET confirmed=1 WHERE id=?', (candidate['id'],))
        candidate = db.rows('SELECT * FROM candidates WHERE id=?', (candidate['id'],))[0]
        db.record(candidate, reading)
        lower = replace(reading, price=9000)
        db.record(candidate, lower)
        alerts = db.rows('SELECT message FROM alerts')
        assert len(alerts) == 1 and 'Preço público por kg' in alerts[0]['message']
        assert 'Pagamento não confirmado' in alerts[0]['message']
        moved = replace(lower, seller=lower.seller.replace('01001-000', '02002-000'),
                        identifiers={**lower.identifiers, 'postal_code': '02002000'}, price=8000)
        db.record(candidate, moved)
        assert len(db.rows('SELECT * FROM alerts')) == 1
        assert len(db.rows('SELECT * FROM series')) == 2
        assert not replace(reading, stock='out_of_stock').comparable
        assert not replace(reading, identifiers={}).comparable
        db.conn.close()
    asyncio.run(run())


def test_regional_network_cannot_submit_orders_or_follow_post_redirects():
    async def run():
        config = SimpleNamespace(domains=('atacadao.com.br',), browser=False, delay=0)
        f = Fetcher(config)
        f.public = AsyncMock()
        f.allowed_by_robots = AsyncMock()
        try:
            with pytest.raises(ReadError, match='regional_request_not_allowed'):
                await f.request('https://www.atacadao.com.br/api/checkout/pub/orderForm/abc/items', public_post={})
            f.client.post = AsyncMock(return_value=httpx.Response(302, headers={'location': '/checkout'},
                request=httpx.Request('POST', 'https://www.atacadao.com.br/api/checkout/pub/orderForms/simulation')))
            with pytest.raises(ReadError, match='regional_selection_redirect'):
                await f.request('https://www.atacadao.com.br/api/checkout/pub/orderForms/simulation', public_post={})
            assert f.client.post.await_count == 1
        finally:
            await f.close()
    asyncio.run(run())


def packed_router(data):
    graph = []
    def encode(value):
        if value is None:
            return -5
        index = len(graph)
        graph.append(None)
        if isinstance(value, dict):
            graph[index] = {'_' + str(encode(k)): encode(v) for k, v in value.items()}
        elif isinstance(value, list):
            graph[index] = [encode(v) for v in value]
        else:
            graph[index] = value
        return index
    encode({'loaderData': {'produto-slug': data}})
    return '<script>window.router.enqueue(' + json.dumps(json.dumps(graph)) + ')</script>'


def carrefour_html(cep=CEP, unit_price=100, printed='100,00'):
    data = {'zipCode': cep, 'schema': {'sku': '123', 'offers': {'priceCurrency': 'BRL', 'price': 150}},
            'product': {'productName': 'Picanha resfriada Maturatta', 'items': [
                {'measurementUnit': 'kg', 'sellers': [{'sellerDefault': True, 'sellerId': '1',
                 'sellerName': 'Carrefour', 'commertialOffer': {'Price': unit_price,
                  'calculatedPrice': 150, 'AvailableQuantity': 5, 'teasers': [], 'GiftSkuIds': [], 'BuyTogether': []}}]}]}}
    return ('<div><div><h1 data-testid="pdp-product-name">Picanha resfriada Maturatta</h1></div>'
            '<span>R$ ' + printed + ' / kg</span></div>' + packed_router(data))


@pytest.mark.parametrize('wrong_cep,unit_price,printed,valid', [
    (CEP, 100, '100,00', True), ('99999999', 100, '100,00', False), (CEP, 150, '100,00', False)])
def test_carrefour_requires_product_region_and_explicit_kg_rate(wrong_cep, unit_price, printed, valid):
    async def run():
        url = 'https://mercado.carrefour.com.br/produto/picanha-maturatta-123'
        response = {'result': {'postalCode': CEP, 'regionId': 'region-test',
                               'regionContextProps': {'deliveryType': 'residential'}}}
        f = SimpleNamespace(config=SimpleNamespace(delay=0), allowed_by_robots=AsyncMock(),
            request=AsyncMock(side_effect=[(json.dumps(response), ''),
                (carrefour_html(wrong_cep, unit_price, printed), url)]))
        obj = GroceryPrices(f)
        try:
            if valid:
                reading, = await obj.carrefour(adapter('mercado.carrefour.com.br'), url, CEP)
                assert reading.price == 10000 and reading.public_unit_price
                assert f.request.await_args.kwargs['fresh'] is True
            else:
                with pytest.raises(ReadError):
                    await obj.carrefour(adapter('mercado.carrefour.com.br'), url, CEP)
        finally:
            await obj.close()
    asyncio.run(run())


@pytest.mark.parametrize('availability,slas,unit,valid', [
    ('available', [{'deliveryChannel': 'delivery'}], 'kg', True),
    ('withoutStock', [], 'kg', False), ('available', [], 'kg', False),
    ('available', [{'deliveryChannel': 'pickup-in-point'}], 'kg', False),
    ('available', [{'deliveryChannel': 'delivery'}], 'un', False),
])
def test_atacadao_requires_stock_delivery_and_unit_independently(availability, slas, unit, valid):
    async def run():
        product = {'@type': 'Product', 'name': 'Picanha Maturatta congelada', 'sku': '123',
                   'offers': {'@type': 'Offer', 'price': 0, 'priceCurrency': 'BRL'}}
        html = '<script type="application/ld+json">' + json.dumps(product) + '</script>'
        regions = [{'sellers': [{'id': 'atacadaobr7', 'name': 'Loja de teste'}]}]
        simulation = {'items': [{'id': '123', 'seller': 'atacadaobr7', 'requestIndex': 0,
            'availability': availability, 'measurementUnit': unit, 'unitMultiplier': 1,
            'sellingPrice': 10000, 'priceDefinition': {'pricePerUnit': 10000}, 'priceTags': []}],
            'logisticsInfo': [{'itemIndex': 0, 'slas': slas}]}
        f = SimpleNamespace(allowed_by_robots=AsyncMock(), request=AsyncMock(
            side_effect=[(json.dumps(regions), ''), (json.dumps(simulation), '')]))
        obj = GroceryPrices(f)
        reading, = await obj.atacadao(adapter('atacadao.com.br'), html,
                                     'https://www.atacadao.com.br/picanha-maturatta/p', CEP)
        assert reading.comparable is valid
        assert reading.price == (10000 if valid else None)
        assert f.request.await_args.kwargs['public_post']['postalCode'] == CEP
    asyncio.run(run())


def test_boa_zero_price_out_of_stock_is_not_a_discount():
    async def run():
        obj = GroceryPrices(None)
        obj.boa_session = AsyncMock(return_value={'channel': '{"regionId":"test"}'})
        obj.boa_query = AsyncMock(return_value={'product': {
            'sku': '123', 'name': 'Picanha Maturatta', 'offers': {'offers': [
                {'availability': 'https://schema.org/OutOfStock', 'price': 0}]}}})
        reading, = await obj.boa(adapter('boasupermercados.com.br'), '',
                                'https://www.boasupermercados.com.br/picanha-maturatta-123/p', CEP)
        assert reading.price is None and not reading.comparable
        assert 'indisponível' in reading.identifiers['regional_reason']
    asyncio.run(run())


def test_public_router_payload_is_data_and_never_executed():
    from monitor.public_payloads import router_data
    assert router_data(packed_router({'zipCode': CEP}))['produto-slug']['zipCode'] == CEP
    for script in ['<script>x.enqueue(__import__("os"))</script>',
                   '<script>x.enqueue("[0]")</script>',
                   '<script>x.enqueue("[{\\"_99\\":2}]")</script>']:
        with pytest.raises(ReadError):
            router_data(script)
