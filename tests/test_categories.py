"""Menu/consultas simulados; seed e recortes derivam de links reais documentados."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.deals.catalog import CategoryCatalog, Category, category_links
from monitor.deals.telegram import PromotionsTelegram
from monitor.deals.service import Deals
from monitor.deals.models import DiscountFilter
from monitor.adapters.base import ReadError
from monitor.network import Fetcher


def test_ddr4_context_parent_category_and_accessories():
    catalog = CategoryCatalog()
    category = catalog.items['hardware/memoria-ram/ddr4']
    assert category.search_query == 'memória RAM DDR4'
    assert catalog.parent_urls(category)['kabum.com.br'] == 'https://kabum.com.br/hardware/memoria-ram'
    assert category.accepts_title('Memória RAM Kingston Fury DDR4 16GB')
    assert category.accepts_title('Memória notebook DDR4 8GB')
    assert not category.accepts_title('Memória RAM DDR5 16GB')
    assert not category.accepts_title('Adaptadora DDR4 testador conversor')
    assert not category.accepts_title('Memória RAM sem geração declarada')


def test_catalog_multiple_departments_and_domain_scope():
    catalog = CategoryCatalog()
    available = catalog.available(('pichau.com.br','terabyteshop.com.br','kabum.com.br'))
    groups = {c.path[0] for c in available}
    assert {'Hardware', 'Periféricos', 'Pets', 'Casa e Lazer', 'Notebooks', 'Monitores'} <= groups
    assert len(available) > 100 and len(groups) > 20
    assert all('pichau.com.br' in c.urls for c in catalog.available(('pichau.com.br',)))
    assert catalog.available(('unknown.example',)) == []
    assert catalog.find('notebook', ('pichau.com.br',))
    assert catalog.find('placa mãe', ('pichau.com.br',))[0].key == 'hardware/placas-mae'


def test_discovery_only_navigation_not_products_and_not_other_domains():
    html = '''<div class="header-mega-menu-container">
    <a href="/perifericos/teclado">Teclado</a>
    <a href="/produto/123/teclado">Teclado produto</a>
    <a href="/Central.obj">Conta</a>
    <a href="https://evil.example/pets">Pets</a></div>
    <aside><a href="/fake">Categoria falsa fora do menu</a></aside>'''
    rows = category_links(html, 'https://www.terabyteshop.com.br/', 'terabyteshop.com.br')
    assert [r['url'] for r in rows] == ['https://www.terabyteshop.com.br/perifericos/teclado']
    html = '<div class="embla__slide"><a title="Pets" href="/pets">Pets</a></div>'
    assert category_links(html,'https://www.pichau.com.br/','pichau.com.br')[0]['title'] == 'Pets'


@pytest.mark.parametrize('domain,filename', [('pichau.com.br','pichau_categories_menu_real.html'),('terabyteshop.com.br','terabyte_categories_menu_real.html')])
def test_navigation_from_reduced_real_capture(domain,filename):
    from pathlib import Path
    html=Path('tests/fixtures',filename).read_text(encoding='utf-8')
    rows=category_links(html,'https://www.'+domain+'/',domain)
    assert len(rows)==6 and all(r['domain']==domain for r in rows)


def test_custom_requests_are_not_restricted_to_seed_and_reject_unsafe_url():
    async def scenario():
        fetcher = Fetcher(SimpleNamespace(domains=('pichau.com.br',), browser=False))
        catalog = CategoryCatalog()
        request = catalog.request('brinquedos', fetcher)
        assert request.query == 'brinquedo' and request.urls == {}
        direct = catalog.request('https://www.pichau.com.br/casa-e-lazer', fetcher)
        assert direct.urls['pichau.com.br'].endswith('/casa-e-lazer')
        for text in ('https://localhost/private', 'https://evil.example/pets', 'http://www.pichau.com.br/pets'):
            with pytest.raises((ReadError,ValueError)):
                catalog.request(text,fetcher)
        await fetcher.close()
    asyncio.run(scenario())


def test_refresh_adds_category_caches_and_preserves_catalog_on_failure():
    async def scenario():
        catalog = CategoryCatalog()
        config = SimpleNamespace(domains=('terabyteshop.com.br','pichau.com.br'), browser=False)
        fetcher = Fetcher(config)
        async def html(url):
            if 'pichau' in url:
                raise ReadError('blocked_no_bypass')
            return '<div class="header-mega-menu-container"><a href="/novo-departamento">Novo departamento</a></div>', url
        fetcher.html = AsyncMock(side_effect=html)
        before = len(catalog.items)
        notices = await catalog.refresh(fetcher,config.domains)
        assert len(catalog.items) == before+1
        assert any('preservado' in n for n in notices)
        await catalog.refresh(fetcher,config.domains)
        assert fetcher.html.await_count == 2
        await fetcher.close()
    asyncio.run(scenario())


def test_paged_ui_selects_actual_category_and_rejects_old_page_buttons():
    async def scenario():
        config = SimpleNamespace(user=42,chat=-1,domains=('pichau.com.br','terabyteshop.com.br'))
        catalog = CategoryCatalog()
        controller = PromotionsTelegram(config,SimpleNamespace(catalog=catalog),AsyncMock(),lambda c:None)
        reply = AsyncMock()
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42),effective_chat=SimpleNamespace(id=-1),
            effective_message=SimpleNamespace(text='/promocoes',reply_text=reply))
        await controller.command(update,SimpleNamespace(args=[]))
        markup = reply.await_args.kwargs['reply_markup']
        old = markup.inline_keyboard[0][0].callback_data
        next_button = next(b for row in markup.inline_keyboard for b in row if b.text.startswith('Próxima'))
        query = SimpleNamespace(data=next_button.callback_data,answer=AsyncMock(),message=SimpleNamespace(reply_text=reply))
        update.callback_query=query
        await controller.callback(update,None)
        assert 'página 2/' in reply.await_args.args[0]
        count = reply.await_count
        query.data=old
        await controller.callback(update,None)
        assert reply.await_count == count and query.answer.await_args.kwargs['show_alert']
        update.effective_message.text='/categoria pets'
        await controller.command(update,SimpleNamespace(args=['pets']))
        choice=reply.await_args.kwargs['reply_markup'].inline_keyboard[0][0]
        query.data=choice.callback_data
        await controller.callback(update,None)
        assert controller.session.category.key == 'pets' and controller.session.stage == 'filter'
        assert all(len(b.callback_data.encode())<=64 for row in reply.await_args.kwargs['reply_markup'].inline_keyboard for b in row)
    asyncio.run(scenario())


def test_custom_query_reads_prices_without_database_or_scheduling(monkeypatch):
    from monitor.models import Reading
    from monitor.deals.formatting import messages
    async def scenario():
        config=SimpleNamespace(domains=('kabum.com.br',),browser=False,provider='direct')
        fetcher=Fetcher(config)
        reading=Reading('Brinquedo teste','Seller','NewCondition','Pix',70000,'in_stock')
        url='https://www.kabum.com.br/produto/123/brinquedo'
        import json
        html='<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'product':{'id':123,'title':reading.title,'prices':{'oldPrice':1000}}}}})+'</script>'
        monitor=SimpleNamespace(config=config,fetcher=fetcher,read_snapshot=AsyncMock(return_value=([reading],html,url)))
        search=AsyncMock(return_value=[url])
        monkeypatch.setattr('monitor.deals.service.Search.links',search)
        deals=Deals(monitor)
        request=deals.catalog.request('brinquedos',fetcher)
        report=await deals.run(request,DiscountFilter.parse('>=30'),config.domains)
        assert len(report.results)==1 and report.coverage[0].category_pages==0
        assert report.coverage[0].product_pages==1 and 'termo' in report.coverage[0].notices[0]
        assert 'brinquedos' in '\n'.join(messages(report))
        search.assert_awaited_once_with('brinquedo')
        await fetcher.close()
    asyncio.run(scenario())


def test_selected_nonhardware_category_reaches_execution_without_reset_to_motherboards():
    from monitor.deals.models import DealReport
    async def scenario():
        config=SimpleNamespace(user=42,chat=-1,domains=('pichau.com.br',))
        catalog=CategoryCatalog()
        report=DealReport([],[],DiscountFilter.parse('>=30'),'pets',category_title='Pets')
        deals=SimpleNamespace(catalog=catalog,run=AsyncMock(return_value=report))
        tasks=[]
        controller=PromotionsTelegram(config,deals,AsyncMock(),tasks.append)
        reply=AsyncMock()
        update=SimpleNamespace(effective_user=SimpleNamespace(id=42),effective_chat=SimpleNamespace(id=-1),
            effective_message=SimpleNamespace(text='/categoria pets',reply_text=reply))
        await controller.command(update,SimpleNamespace(args=['pets']))
        query=SimpleNamespace(answer=AsyncMock(),message=SimpleNamespace(reply_text=reply))
        update.callback_query=query
        def button(action):
            return next(b.callback_data for row in reply.await_args.kwargs['reply_markup'].inline_keyboard for b in row if b.callback_data.endswith(':'+action))
        query.data=button('pick0')
        await controller.callback(update,None)
        query.data=button('ge30')
        await controller.callback(update,None)
        query.data=button('run')
        await controller.callback(update,None)
        await tasks[0]
        assert deals.run.await_args.args[0].key=='pets'
        assert controller.running is False and controller.session is None
    asyncio.run(scenario())
