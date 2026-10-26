"""Telegram callbacks drive the real promotions service with simulated store pages."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from monitor.adapters.base import ReadError
from monitor.deals.catalog import Category, CategoryCatalog
from monitor.deals.formatting import messages
from monitor.deals.models import Coverage, DealReport, DiscountFilter
from monitor.deals.service import Deals, Limits
from monitor.deals.telegram import PromotionsTelegram
from monitor.models import Reading
from monitor.network import Fetcher


def catalog():
    c = CategoryCatalog()
    c.items = {}
    for key, title in [('hardware/placas-mae', 'Placas-mãe'), ('perifericos/mouse', 'Mouse'), ('perifericos/teclado', 'Teclado')]:
        c.add(Category(key, ('Hardware' if key.startswith('hardware') else 'Periféricos', title),
                       {'kabum.com.br': 'https://www.kabum.com.br/' + key,
                        'terabyteshop.com.br': 'https://www.terabyteshop.com.br/' + key}))
    c.add(Category('lacoste/sale', ('Lacoste', 'Sale'), {'lacoste.com': 'https://www.lacoste.com/br/lacoste/sale/'}))
    return c


def category_page(codes):
    data = {'props': {'pageProps': {'data': {'catalogServer': {'data': [
        {'code': code, 'friendlyName': f'produto-{code}'} for code in codes]}}}}}
    return '<script id="__NEXT_DATA__">' + json.dumps(data) + '</script>'


async def snapshot(url):
    code = int(url.split('/produto/')[1].split('/')[0])
    reading = Reading(f'Produto {code}', 'KaBuM', 'NewCondition', 'Pix', 69000, 'in_stock')
    product = {'id': code, 'title': reading.title, 'prices': {'oldPrice': 1000}}
    html = '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'product': product}}}) + '</script>'
    return [reading], html, url


def test_telegram_complete_computers_flow_no_implicit_stores_or_external_search(monkeypatch):
    async def run():
        config = SimpleNamespace(domains=('kabum.com.br', 'terabyteshop.com.br', 'lacoste.com'), user=42, chat=1, browser=False)
        fetcher = Fetcher(config)
        fetcher.html = AsyncMock(return_value=(category_page([1, 2]), 'https://www.kabum.com.br/hardware/placas-mae'))
        monitor = SimpleNamespace(config=config, fetcher=fetcher, read_snapshot=AsyncMock(side_effect=snapshot))
        deals = Deals(monitor)
        deals.catalog = catalog()
        external = AsyncMock()
        monkeypatch.setattr('monitor.deals.service.Search.links', external)
        tasks, sent = [], []
        async def send(text):
            sent.append(text)
        controller = PromotionsTelegram(config, deals, send, tasks.append)
        reply = AsyncMock()
        query = SimpleNamespace(data='', answer=AsyncMock(), message=SimpleNamespace(reply_text=reply))
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_chat=SimpleNamespace(id=1),
                                 effective_message=SimpleNamespace(text='/promocoes', reply_text=reply), callback_query=query)
        async def click(text):
            markup = reply.await_args.kwargs['reply_markup']
            button = next(b for row in markup.inline_keyboard for b in row if b.text == text)
            query.data = button.callback_data
            await controller.callback(update, None)
        try:
            await controller.command(update, SimpleNamespace(args=[]))
            assert not controller.session.stores
            await click('Computadores')
            assert [p[-1] for p in controller.session.branches] == ['Placas-mãe', 'Mouse', 'Teclado']
            await click('Placas-mãe')
            markup = reply.await_args.kwargs['reply_markup']
            labels = [b.text for row in markup.inline_keyboard for b in row if b.callback_data.startswith('promo:')]
            assert labels == [f'Maior que {n}%' for n in (5, 10, 20, 30, 40, 50, 60, 70, 80)]
            controller.session.validation = 'announced'  # This test exercises navigation/extraction, not market proof.
            await click('Maior que 30%')
            assert not controller.session.stores
            await click('🔎 Pesquisar agora')
            assert tasks == [] and not controller.running
            await controller.show_stores(reply)
            await click('TODAS')
            assert controller.session.stores == {'kabum.com.br', 'terabyteshop.com.br'}
            assert 'lacoste.com' not in controller.session.stores
            await click('Limpar seleção')
            await click('⬜ KaBuM')
            await click('🔎 Pesquisar agora')
            await tasks[0]
            assert not controller.running and controller.session is None
            assert monitor.read_snapshot.await_count == 2
            assert all('kabum.com.br' in call.args[0] for call in fetcher.html.await_args_list)
            assert any('31.00%' in text for text in sent)
            external.assert_not_awaited()
        finally:
            await fetcher.close()
    asyncio.run(run())


@pytest.mark.parametrize('value', range(20, 81, 10))
def test_every_preset_excludes_exact_boundary(value):
    f = DiscountFilter.parse('>' + str(value))
    assert not f.accepts(100000, 100000 - value * 1000)
    assert f.accepts(100000, 99999 - value * 1000)


def test_all_computers_reads_a_fair_sample_of_actual_subcategories(monkeypatch):
    async def run():
        config = SimpleNamespace(domains=('kabum.com.br',), browser=False)
        fetcher = Fetcher(config)
        c = catalog()
        mapping = {'hardware/placas-mae': [1, 2, 3], 'perifericos/mouse': [4, 5, 6], 'perifericos/teclado': [7, 8, 9]}
        async def html(url):
            key = url.split('kabum.com.br/')[1]
            return category_page(mapping[key]), url
        fetcher.html = AsyncMock(side_effect=html)
        monitor = SimpleNamespace(config=config, fetcher=fetcher, read_snapshot=AsyncMock(side_effect=snapshot))
        deals = Deals(monitor, Limits(products_per_store=3))
        deals.catalog = c
        search = AsyncMock()
        monkeypatch.setattr('monitor.deals.service.Search.links', search)
        try:
            selection = c.scope(('Computadores',), config.domains)
            report = await deals.run(selection, DiscountFilter.parse('>30'), config.domains, validation='announced')
            read_codes = {int(call.args[0].split('/produto/')[1].split('/')[0]) for call in monitor.read_snapshot.await_args_list}
            assert read_codes == {1, 4, 7}
            assert len(report.results) == 3
            assert report.coverage[0].discovered == 9
            assert len(report.coverage[0].sources) == 3
            search.assert_not_awaited()
        finally:
            await fetcher.close()
    asyncio.run(run())


def test_parent_url_keeps_product_filter_and_all_scope_keeps_broad_parent():
    c = CategoryCatalog()
    mouse = c.items['perifericos/mouse']
    assert not mouse.accepts_parent_title('Teclado gamer')
    assert mouse.accepts_parent_title('Mouse Gamer Logitech')
    assert c.find('mouse', ('pichau.com.br',))[0].key == 'perifericos/mouse'
    sources = c.sources(c.scope(('Computadores',), ('pichau.com.br',)), 'pichau.com.br')
    hardware = next(source for source, url in sources if url.rstrip('/').endswith('/hardware'))
    assert hardware.key == 'hardware'  # Not an inherited memory-only filter.
    assert 'lacoste.com' not in c.stores_for(c.scope(('Computadores',), ('pichau.com.br', 'lacoste.com')), ('pichau.com.br', 'lacoste.com'))


def test_blocked_promotions_stop_the_store_and_do_not_claim_success():
    async def run():
        config = SimpleNamespace(domains=('kabum.com.br',), browser=False)
        fetcher = Fetcher(config)
        fetcher.html = AsyncMock(side_effect=ReadError('blocked_no_bypass'))
        monitor = SimpleNamespace(config=config, fetcher=fetcher, read_snapshot=AsyncMock())
        deals = Deals(monitor)
        deals.catalog = catalog()
        try:
            report = await deals.run(deals.catalog.scope(('Computadores',), config.domains), DiscountFilter.parse('>30'), config.domains, validation='announced')
            assert fetcher.html.await_count == 1
            monitor.read_snapshot.assert_not_awaited()
            output = list(messages(report))
            assert not any(text.startswith('✅') for text in output)
            assert output[0].startswith('🏁 Pesquisa finalizada')
            assert 'Não consegui verificar ofertas' in output[0]
            assert len(output) == 1
        finally:
            await fetcher.close()
    asyncio.run(run())


def test_thirteen_stores_do_not_generate_thirteen_notice_messages():
    cov = [Coverage(f'store{i}', f'Loja {i}', failed_pages=1, notices=['A loja bloqueou o acesso']) for i in range(13)]
    report = DealReport([], cov, DiscountFilter.parse('>40'), 'grupo/computadores', category_title='Computadores > Tudo')
    output = list(messages(report))
    assert len(output) == 1
    assert all(f'Loja {i}' in output[0] for i in range(13))
