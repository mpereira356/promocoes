"""Simulacoes deterministicas; fixtures *_real sao capturas reduzidas, nao testes de rede."""
import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.models import Reading
from monitor.adapters import adapter
from monitor.adapters.base import ReadError
from monitor.deals.models import DealOffer, DiscountFilter
from monitor.deals.identity import comparable, model_relation
from monitor.deals.service import Deals, Limits, select_offers, compare_offer
from monitor.deals.adapters import ADAPTERS
from monitor.deals.formatting import messages
from monitor.network import Fetcher
from monitor.service import Monitor
from monitor.deals.telegram import PromotionsTelegram, Session


def offer(title='Board B550 DDR4', price=70000, old=100000, domain='kabum.com.br', **kwargs):
    reading = Reading(title, 'Seller', 'NewCondition', 'Pix', price, 'in_stock', identifiers={'mpn': 'board123', 'brand': 'brand'})
    return DealOffer(reading, f'https://www.{domain}/produto/123/board', domain, domain, old, **kwargs)


@pytest.mark.parametrize('expression,old,current,expected', [
    ('>30', 100000, 70000, False), ('>=30', 100000, 70000, True),
    ('>30', 100000, 69999, True), ('>=30', 100000, 70001, False),
    ('>=25,5%', 100000, 74500, True), ('>0', 100000, 100000, False),
    ('>=0', None, 50000, False), ('>=0', 0, 50000, False),
    ('>=0', 100000, 0, False), ('>=0', True, 1, False),
    ('>=0', 100000, None, False), ('>=0', 1, 2, False),
])
def test_discount_exact(expression, old, current, expected):
    assert DiscountFilter.parse(expression).accepts(old, current) is expected


@pytest.mark.parametrize('expression', ['30', '<30', '>=101', '>=-1', '>nan', '>1e2', '>30x'])
def test_invalid_filters(expression):
    with pytest.raises(ValueError):
        DiscountFilter.parse(expression)


def test_identity_requires_more_than_title_and_price():
    a, b = offer(), offer(domain='pichau.com.br')
    assert comparable(a, b)
    b.reading.title = 'Different marketing title DDR4'
    assert model_relation(a, b) is True
    a.reading.identifiers = b.reading.identifiers = {}
    b.reading.title = a.reading.title
    assert model_relation(a, b) is None
    assert not comparable(a, b)


@pytest.mark.parametrize('field,value', [('payment', 'Cartao'), ('condition', 'UsedCondition'), ('stock', 'unknown'), ('currency', 'USD'), ('payment', ''), ('condition', '')])
def test_conditions_do_not_mix(field, value):
    a, b = offer(), offer(domain='pichau.com.br')
    setattr(b.reading, field, value)
    assert not comparable(a, b)


@pytest.mark.parametrize('title', ['Board B550 DDR5', 'Board B550 DDR4 Wi-Fi', 'Board B550 DDR4 Rev 2'])
def test_variants_do_not_confirm(title):
    assert model_relation(offer(), offer(title=title)) is not True


def test_identifiers_and_required_coupons():
    a, b = offer(), offer(domain='pichau.com.br')
    b.reading.identifiers = {'mpn': 'other', 'brand': 'brand'}
    assert model_relation(a, b) is False
    b.reading.identifiers = a.reading.identifiers.copy()
    b.coupon = 'CLUB'
    assert not comparable(a, b)
    b.coupon, b.members = '', 'Prime'
    assert not comparable(a, b)


def test_ranking_top_three_no_filler_and_no_repeated_products():
    pool = []
    for i, price in enumerate([70000, 60000, 50000, 40000]):
        item = offer(title=f'Board {i}', price=price)
        item.reading.identifiers = {'mpn': str(i), 'brand': 'brand'}
        pool.append(item)
    pool += [replace(pool[-1], domain='pichau.com.br'), offer(old=None)]
    selected = select_offers(pool, DiscountFilter.parse('>=30'))
    assert [o.reading.price for o in selected] == [40000, 50000, 60000]
    assert len(select_offers(pool, DiscountFilter.parse('>50'))) == 1
    assert select_offers(pool, DiscountFilter.parse('>99')) == []


def test_reference_discount_independent_of_other_store_price():
    a, b = offer(), offer(price=60000, old=None, domain='pichau.com.br')
    result = compare_offer(a, [a, b])
    assert result.offer.percent == 30
    assert result.lowest is b
    assert 'preço menor' in result.comparison
    assert result.offer.reading.price == 70000
    b.reading.price = 80000
    assert 'Menor' in compare_offer(a, [a, b]).comparison


def test_only_three_purchase_options():
    a = offer()
    others = [offer(price=50000+i, domain=d) for i, d in enumerate(['pichau.com.br', 'amazon.com.br', 'terabyteshop.com.br'])]
    assert len(compare_offer(a, [a]+others).options) == 3


def test_kabum_reference_bound_product_and_no_double_coupon():
    a = offer()
    product = {'id': 123, 'title': a.reading.title, 'prices': {'oldPrice': 1000, 'price': 800, 'priceWithDiscount': 700}, 'stamps': {'title': 'CUPOM TESTE'}}
    html = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'product': product}}}) + '</script>'
    parsed = ADAPTERS[a.domain].offer(html, a.url, a.reading)
    assert parsed.previous == 100000 and parsed.reading.price == 70000
    assert parsed.percent == 30 and not parsed.coupon and parsed.notes
    assert ADAPTERS[a.domain].offer(html, a.url.replace('/123/', '/456/'), a.reading).previous is None
    # price sem oldPrice nao pode ser usado como referencia.
    del product['prices']['oldPrice']
    html = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'product': product}}}) + '</script>'
    assert ADAPTERS[a.domain].offer(html, a.url, a.reading).previous is None


def test_pichau_real_reduced_capture_not_installment():
    html = Path('tests/fixtures/pichau_product_browser_real.html').read_text(encoding='utf-8')
    url = 'https://www.pichau.com.br/placa-mae-b550'
    reading = adapter('pichau.com.br').parse(html, url)[0]
    parsed = ADAPTERS['pichau.com.br'].offer(html, url, reading)
    assert reading.price == 112999
    assert parsed.previous == 164705
    assert 31 < parsed.percent < 32
    assert parsed.reading.payment == 'Pix'
    assert ADAPTERS['pichau.com.br'].offer(html, url, replace(reading, price=132940, payment='')).previous is None


def test_recommendation_strikethrough_never_reference():
    a = offer(domain='terabyteshop.com.br')
    html = f'<h1>{a.reading.title}</h1><div>12x R$ 58,33</div><aside><del>R$ 5.000,00</del></aside>'
    assert ADAPTERS[a.domain].offer(html, a.url, a.reading).previous is None


def test_kabum_category_double_json_and_actual_pagination():
    data = {'catalogServer': {'data': [{'code': 123, 'friendlyName': 'board'}], 'pagination': {'current': 1, 'next': 2}}}
    html = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'data': json.dumps(data)}}}) + '</script>'
    page = ADAPTERS['kabum.com.br'].page(html, ADAPTERS['kabum.com.br'].category_url('hardware/placas-mae'))
    assert page.urls == ['https://www.kabum.com.br/produto/123/board']
    assert 'page_number=2' in page.next_url


def test_pichau_category_card_and_next_only_same_category():
    url = ADAPTERS['pichau.com.br'].category_url('hardware/placas-mae')
    html = '<a data-cy="list-product" href="/placa-mae-b550"><h2>Board</h2></a><a href="?page=2">2</a><a href="https://evil.example/">2</a>'
    page = ADAPTERS['pichau.com.br'].page(html, url)
    assert len(page.urls) == 1 and page.next_url == url + '?page=2'


@pytest.mark.parametrize('failure,reason', [(ReadError('blocked_no_bypass'), 'bloqueou'), (OSError('simulated DNS failure'), 'conexão')])
def test_manual_run_partial_failure_no_database_and_no_future_jobs(failure, reason):
    async def scenario():
        config = SimpleNamespace(domains=('kabum.com.br', 'pichau.com.br'), browser=False, provider='disabled')
        fetcher = Fetcher(config)
        a = offer()
        category = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'data': {'catalogServer': {'data': [{'code': 123, 'friendlyName': 'board'}]}}}}}) + '</script>'
        product = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'product': {'id':123, 'title': a.reading.title, 'prices': {'oldPrice': 1000}}}}}) + '</script>'
        async def html(url):
            if 'pichau' in url:
                raise failure
            return category, url
        fetcher.html = html
        monitor = SimpleNamespace(config=config, fetcher=fetcher, read_snapshot=AsyncMock(return_value=([a.reading], product, a.url)))
        # Nao ha db, scheduler, send ou alertas disponiveis neste objeto.
        report = await Deals(monitor).run('hardware/placas-mae', DiscountFilter.parse('>=30'), config.domains, '01001000')
        assert len(report.results) == 1
        assert report.coverage[1].category_pages == 1
        assert any(reason in n for n in report.coverage[1].notices)
        output = '\n'.join(messages(report))
        assert '🏆' in output and 'concluída' in output and '01001000' in output
        assert 'não comprova uma queda histórica' in output
        assert 'Comparação: não confirmada' in output
        assert monitor.read_snapshot.await_count == 1
        await fetcher.close()
    asyncio.run(scenario())


def test_suspicious_reference_flag_not_historical_claim():
    assert offer(price=20000).suspicious
    assert not offer(price=50000).suspicious


def test_snapshot_shared_with_existing_reads_and_no_writes():
    async def scenario():
        config = SimpleNamespace(domains=('kabum.com.br',), browser=False)
        fetcher = Fetcher(config)
        monitor = Monitor(None, config, fetcher, None, None)
        count = 0
        async def load(url):
            nonlocal count
            count += 1
            await asyncio.sleep(.01)
            return [offer().reading], '<html/>', url
        monitor._load_snapshot = load
        url = offer().url
        first, snapshot = await asyncio.gather(monitor.read(url), monitor.read_snapshot(url))
        assert count == 1 and first == snapshot[0]
        await fetcher.close()
    asyncio.run(scenario())


def test_telegram_unauthorized_and_duplicate_run():
    async def scenario():
        config = SimpleNamespace(user=42, chat=-1, domains=('kabum.com.br',))
        scheduled, output = [], []
        async def send(text):
            output.append(text)
        async def execute(session):
            output.append('execute')
        controller = PromotionsTelegram(config, None, send, scheduled.append)
        controller.execute = execute
        reply = AsyncMock()
        update = SimpleNamespace(effective_user=SimpleNamespace(id=99), effective_chat=SimpleNamespace(id=-1), effective_message=SimpleNamespace(text='/promocoes', reply_text=reply))
        await controller.command(update, SimpleNamespace(args=[]))
        assert controller.session is None and not reply.called
        update.effective_user.id = 42
        await controller.command(update, SimpleNamespace(args=[]))
        assert controller.session.stage == 'category'
        controller.session.stage = 'stores'
        controller.session.discount = DiscountFilter.parse('>=30')
        controller.session.category = controller.catalog.items['hardware/placas-mae']
        update.callback_query = SimpleNamespace(data=f'promo:{controller.session.nonce}:{controller.session.revision}:run', answer=AsyncMock(), message=SimpleNamespace(reply_text=reply))
        await controller.callback(update, None)
        await controller.callback(update, None)
        assert len(scheduled) == 1
        await scheduled[0]
        # Token antigo nao pode iniciar pesquisa de outra selecao.
        controller.running = False
        controller.session = Session()
        await controller.callback(update, None)
        assert len(scheduled) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize('domain,fixture', [('kabum.com.br', 'kabum_category_real.html'), ('pichau.com.br', 'pichau_category_real.html')])
def test_reduced_real_category_capture(domain, fixture):
    store = ADAPTERS[domain]
    html = Path('tests/fixtures', fixture).read_text(encoding='utf-8')
    page = store.page(html, store.category_url('hardware/placas-mae'))
    assert len(page.urls) == 3 and page.next_url
    assert all(domain in url for url in page.urls)


@pytest.mark.parametrize('domain', ['amazon.com.br', 'mercadolivre.com.br', 'terabyteshop.com.br'])
def test_generic_reference_only_same_offer_price_and_seller(domain):
    a = offer(domain=domain)
    data = {'@type':'Product', 'name':a.reading.title, 'model':'Board-123', 'offers':{
        '@type':'Offer', 'price':700, 'seller':{'name':'Seller'},
        'priceSpecification':{'@type':'UnitPriceSpecification', 'price':1000, 'priceCurrency':'BRL', 'priceType':'https://schema.org/StrikethroughPrice'}}}
    def html():
        return '<script type="application/ld+json">' + json.dumps(data) + '</script>'
    parsed = ADAPTERS[domain].offer(html(), a.url, a.reading)
    assert parsed.previous == 100000 and parsed.model == 'Board-123'
    data['offers']['seller']['name'] = 'Other seller'
    assert ADAPTERS[domain].offer(html(), a.url, a.reading).previous is None
    data['offers']['seller']['name'] = 'Seller'
    data['offers']['price'] = 12.50  # Parcela em outra oferta nao corresponde ao total.
    assert ADAPTERS[domain].offer(html(), a.url, a.reading).previous is None


@pytest.mark.parametrize('model', ['B550', 'Pro', 'Gamer', '123'])
def test_model_generic_chipset_is_not_identity(model):
    a = offer()
    data = {'@type':'Product','name':a.reading.title,'model':model}
    html = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
    assert ADAPTERS[a.domain].offer(html, a.url, a.reading).model == ''


def test_query_all_qualifying_products_but_present_only_three(monkeypatch):
    async def scenario():
        config = SimpleNamespace(domains=('kabum.com.br','pichau.com.br'), browser=False, provider='direct')
        fetcher = Fetcher(config)
        links = [{'code':i, 'friendlyName':f'board-{i}'} for i in range(1,5)]
        catalog = '<script id="__NEXT_DATA__">' + json.dumps({'props':{'pageProps':{'data':{'catalogServer':{'data':links}}}}}) + '</script>'
        async def html(url):
            if 'pichau' in url:
                raise ReadError('blocked_no_bypass')
            return catalog, url
        fetcher.html = html
        async def read_snapshot(url):
            code = int(url.split('/produto/')[1].split('/')[0])
            a = offer(title=f'Unique {code}', price=50000-code)
            a.reading.identifiers['mpn'] = str(code)
            product = {'id':code,'title':a.reading.title,'prices':{'oldPrice':1000}}
            return [a.reading], '<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'product':product}}})+'</script>', url
        queries = []
        async def search(self, query):
            queries.append(query)
            return []
        monkeypatch.setattr('monitor.deals.service.Search.links', search)
        monitor = SimpleNamespace(config=config, fetcher=fetcher, read_snapshot=read_snapshot)
        report = await Deals(monitor).run('hardware/placas-mae', DiscountFilter.parse('>30'), config.domains)
        assert len(queries) == 4 and len(report.results) == 3
        assert any('A loja bloqueou o acesso' in n for n in report.coverage[1].notices)
        await fetcher.close()
    asyncio.run(scenario())


def test_manual_lock_rejects_duplicate_without_extra_requests():
    async def scenario():
        config = SimpleNamespace(domains=('kabum.com.br',))
        monitor = SimpleNamespace(config=config, fetcher=object())
        deals = Deals(monitor)
        async with deals.lock:
            with pytest.raises(ValueError, match='andamento'):
                await deals.run('hardware/placas-mae', DiscountFilter.parse('>30'), config.domains)
    asyncio.run(scenario())


def test_page_audit_does_not_count_other_async_tasks():
    from monitor.network import PAGE_AUDIT
    async def scenario():
        async def outside():
            assert PAGE_AUDIT.get() is None
        other = asyncio.create_task(outside())
        token = PAGE_AUDIT.set([])
        try:
            await other
            assert PAGE_AUDIT.get() == []
        finally:
            PAGE_AUDIT.reset(token)
    asyncio.run(scenario())


def test_report_separates_store_notices_without_duplicate_labels():
    from monitor.deals.models import Coverage, DealReport
    a = offer()
    cov = Coverage(a.domain, 'KaBuM', notices=['⚠️ Falha na leitura da oferta: ' + a.url] * 2)
    report = DealReport([compare_offer(a, [a])], [cov], DiscountFilter.parse('>=30'), 'hardware/placas-mae')
    output = list(messages(report))
    assert len(output) == 3
    assert 'Comparação: não confirmada' in output[0]
    assert 'Falha na leitura' not in output[1]
    assert output[2].count(a.url) == 1
    assert '⚠️ ⚠️' not in '\n'.join(output)


@pytest.mark.parametrize('failure', [ReadError('blocked_no_bypass'), OSError('simulated DNS failure')])
def test_marketplace_catalog_discarded_before_product_request(monkeypatch, failure):
    async def scenario():
        config = SimpleNamespace(domains=('mercadolivre.com.br',), browser=False, provider='direct')
        fetcher = Fetcher(config)
        catalog = 'https://www.mercadolivre.com.br/board/p/MLB123456'
        individual = 'https://produto.mercadolivre.com.br/MLB-123456-board-_JM'
        async def search(self, query):
            return [catalog, individual]
        monkeypatch.setattr('monitor.deals.service.Search.links', search)
        snapshot = AsyncMock(side_effect=failure)
        monitor = SimpleNamespace(config=config, fetcher=fetcher, read_snapshot=snapshot)
        category = Deals(monitor).catalog.request('produto de teste', fetcher)
        report = await Deals(monitor).run(category, DiscountFilter.parse('>30'), config.domains)
        snapshot.assert_awaited_once_with(individual)
        assert report.coverage[0].product_pages == 1
        assert any('catálogo' in n for n in report.coverage[0].notices)
        await fetcher.close()
    asyncio.run(scenario())


def test_delivery_failure_does_not_report_search_failure():
    from telegram.error import TimedOut
    from monitor.deals.models import DealReport
    async def scenario():
        report = DealReport([], [], DiscountFilter.parse('>30'), 'hardware/placas-mae')
        config = SimpleNamespace(domains=('kabum.com.br',))
        deals = SimpleNamespace(run=AsyncMock(return_value=report))
        send = AsyncMock(side_effect=[TimedOut(), None])
        controller = PromotionsTelegram(config, deals, send, None)
        controller.running = True
        session = Session(category=controller.catalog.items['hardware/placas-mae'],
            discount=report.filter, stores={'kabum.com.br'})
        await controller.execute(session)
        assert not controller.running and controller.session is None
        assert 'Telegram não recebeu 1' in send.await_args_list[-1].args[0]
        assert not any('falha inesperada' in call.args[0] for call in send.await_args_list)
    asyncio.run(scenario())


def test_terabyte_real_cash_reference_ignores_recommendations():
    from monitor.adapters.terabyte import TerabyteAdapter
    html = Path('tests/fixtures/terabyte_cash_block_real.html').read_text(encoding='utf-8')
    url = 'https://www.terabyteshop.com.br/produto/36231/teclado-gamer-mecanico-corsair-k65-pro-mini-rgb-switch-corsair-opx-preto-ch-91a401a-na'
    reading = TerabyteAdapter().parse(html, url)[0]
    deal = ADAPTERS['terabyteshop.com.br'].offer(html, url, reading)
    assert deal.previous == 96590 and deal.reading.price == 64999
    assert DiscountFilter.parse('>=30').accepts(deal.previous, reading.price)
    # Um preço riscado de recomendação fora do bloco principal não substitui a referência.
    html = html.replace('<del>R$ 965,90</del>', '') + '<aside><p class="precode"><del>R$ 9.999,99</del></p></aside>'
    assert ADAPTERS['terabyteshop.com.br'].offer(html, url, reading).previous is None
