"""Fluxos de UI simulados: autorizacao, filtros guiados e remocao confirmada."""
import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.db import DB
from monitor.menu import BotMenu
from monitor.deals.telegram import PromotionsTelegram
from monitor.deals.service import Deals
from monitor.network import Fetcher


@pytest.fixture
def setup():
    db=DB(':memory:')
    config=SimpleNamespace(user=42,chat=-1,minimum=0,percent=Decimal('0'),target=None,interval=18000,domains=('pichau.com.br',))
    promotions=SimpleNamespace(running=False,refreshing=False,session=None,command=AsyncMock())
    dispatch=AsyncMock()
    ui=BotMenu(config,db,promotions,dispatch,'Exemplo de filtros\n/configurar 1 50 5 1500')
    message=SimpleNamespace(text='/menu',reply_text=AsyncMock())
    update=SimpleNamespace(effective_user=SimpleNamespace(id=42),effective_chat=SimpleNamespace(id=-1),effective_message=message,callback_query=None)
    yield db,config,ui,dispatch,update
    db.conn.close()


def click(update,data):
    update.callback_query=SimpleNamespace(data=data,answer=AsyncMock(),edit_message_text=AsyncMock())


def test_grocery_location_button_and_plain_postal_code_entry(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        config.domains=('extramercado.com.br',)
        await ui.home(update)
        keyboard=update.effective_message.reply_text.await_args.kwargs['reply_markup']
        assert any(button.callback_data=='ui:markets' for row in keyboard.inline_keyboard for button in row)
        click(update,'ui:markets')
        await ui.callback(update,None)
        assert dispatch.await_args.kwargs['name']=='/mercados'
        await ui.prompt(update,'grocerycep')
        update.callback_query=None
        update.effective_message.text='01001-000'
        await ui.text(update,SimpleNamespace())
        assert dispatch.await_args.kwargs=={'name':'/cep','args':['01001000']}
        assert ui.pending is None
    asyncio.run(scenario())


def test_meat_search_requests_missing_cep_and_resumes_same_query(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        config.domains=('extramercado.com.br',)
        config.grocery_postal_code=''
        assert await ui.require_grocery_region(update,'picanha Maturatta')
        assert ui.pending.kind=='grocerycep'
        assert not dispatch.await_count
        update.effective_message.text='inválido'
        await ui.text(update,None)
        assert ui.pending.kind=='grocerycep' and not dispatch.await_count
        update.effective_message.text='01001-000'
        await ui.text(update,None)
        calls=dispatch.await_args_list
        assert [(call.kwargs['name'],call.kwargs['args']) for call in calls] == [
            ('/cep',['01001000']),('/buscar',['picanha','Maturatta'])]
        assert ui.pending is None
    asyncio.run(scenario())


def test_grocery_setup_does_not_interrupt_configured_or_unrelated_searches(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        config.domains=('extramercado.com.br','kabum.com.br')
        config.grocery_postal_code=''
        assert not await ui.require_grocery_region(update,'SSD Kingston 1TB')
        config.grocery_postal_code='01001000'
        assert not await ui.require_grocery_region(update,'picanha')
        assert ui.pending is None
    asyncio.run(scenario())


def test_monitor_card_does_not_confuse_confirmed_model_with_price_history(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        from monitor.models import Reading
        reading=Reading('MSI MAG X870 Tomahawk WiFi','KaBuM','','',200000)
        ad=db.save_ad('https://www.kabum.com.br/produto/123/msi', 'KaBuM', reading)
        pid,_=db.subscribe(db.request_scope(ad['id']),'site',config)
        row=db.rows('SELECT * FROM products WHERE id=?',(pid,))[0]
        await ui.detail(update,ui.card_token(row))
        text=update.effective_message.reply_text.await_args.args[0]
        assert '1 oferta(s) confirmada(s)' in text
        assert 'Ofertas com histórico de preço: 0' in text
        assert 'Ainda sem preço inicial comparável' in text
        buttons=update.effective_message.reply_text.await_args.kwargs['reply_markup']
        expand=next(b for r in buttons.inline_keyboard for b in r if b.callback_data.endswith(':expand'))
        click(update,expand.callback_data)
        await ui.callback(update,None)
        assert dispatch.await_args.kwargs=={'name':'/abrangencia','args':[str(pid),'todas']}
    asyncio.run(scenario())


def test_start_menu_shortcuts_and_unauthorized_access(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        update.effective_message.text='/start'
        await ui.home(update)
        calls=update.effective_message.reply_text.await_args_list
        assert calls[0].kwargs['reply_markup'].is_persistent
        assert len(calls[1].kwargs['reply_markup'].inline_keyboard)>3
        update.effective_user.id=99
        click(update,'ui:monitor')
        await ui.callback(update,None)
        assert ui.pending is None and not dispatch.called
        update.callback_query.answer.assert_awaited_once()
    asyncio.run(scenario())


def test_search_input_dispatches_once_without_registering_monitoring(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        click(update,'ui:search')
        await ui.callback(update,None)
        assert ui.pending.kind=='search'
        update.callback_query=None
        update.effective_message.text='SSD Kingston NV3 1TB'
        await ui.text(update,None)
        assert dispatch.await_args.kwargs=={'name':'/buscar','args':['SSD','Kingston','NV3','1TB']}
        assert not db.rows('SELECT * FROM products')
        await ui.text(update,None)
        assert dispatch.await_count==1
    asyncio.run(scenario())


def test_filters_require_confirmation_accept_comma_and_reject_replay(setup):
    db,config,ui,dispatch,update=setup
    pid=db.add('Produto teste',config)
    token=ui.card_token(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])
    async def scenario():
        await ui.wizard(update,token)
        for value in ('50,90','5','-'):
            update.effective_message.text=value
            await ui.text(update,None)
        assert not dispatch.called and ui.pending.kind=='apply'
        assert db.rows('SELECT minimum FROM products WHERE id=?',(pid,))[0]['minimum']==0
        data='ui:apply:'+ui.pending.token
        click(update,data)
        await ui.callback(update,None)
        assert dispatch.await_args.kwargs=={'name':'/configurar','args':[str(pid),'50.90','5','-']}
        await ui.callback(update,None)
        assert dispatch.await_count==1
    asyncio.run(scenario())


def test_cancel_filters_and_stale_product_cannot_mutate_other_product(setup):
    db,config,ui,dispatch,update=setup
    pid=db.add('Produto original',config)
    token=ui.card_token(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])
    async def scenario():
        await ui.wizard(update,token)
        update.effective_message.text='-1'
        await ui.text(update,None)
        assert ui.pending.values==[]
        click(update,'ui:cancel')
        await ui.callback(update,None)
        assert ui.pending is None and not dispatch.called
        db.run('UPDATE products SET query=? WHERE id=?',('Outro produto',pid))
        click(update,'ui:card:'+token+':pause')
        await ui.callback(update,None)
        assert not dispatch.called
    asyncio.run(scenario())


def test_delete_requires_separate_confirmation_bound_to_product(setup):
    db,config,ui,dispatch,update=setup
    pid=db.add('Produto para remover',config)
    token=ui.card_token(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])
    async def scenario():
        click(update,'ui:card:'+token+':delete')
        await ui.callback(update,None)
        assert not dispatch.called and db.rows('SELECT id FROM products WHERE id=?',(pid,))
        confirm='ui:remove:'+ui.pending.token
        click(update,confirm)
        await ui.callback(update,None)
        assert dispatch.await_args.kwargs=={'name':'/remover','args':[str(pid)]}
        await ui.callback(update,None)
        assert dispatch.await_count==1
    asyncio.run(scenario())


def test_list_pagination_and_action_uses_clicked_id(setup):
    db,config,ui,dispatch,update=setup
    for i in range(8):db.add('Produto '+str(i),config)
    async def scenario():
        await ui.listing(update)
        markup=update.effective_message.reply_text.await_args.kwargs['reply_markup']
        assert any('Próxima' in b.text for row in markup.inline_keyboard for b in row)
        data=markup.inline_keyboard[0][0].callback_data
        token=data.split(':')[2]
        expected=ui.product(token)['id']
        click(update,'ui:card:'+token+':check')
        await ui.callback(update,None)
        assert dispatch.await_args.kwargs=={'name':'/verificar','args':[str(expected)]}
    asyncio.run(scenario())


def test_deleted_id_reuse_does_not_revive_old_card(setup):
    db,config,ui,dispatch,update=setup
    pid=db.add('Mesmo produto',config)
    token=ui.card_token(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])
    ui.forget(pid)
    db.run('DELETE FROM products WHERE id=?',(pid,))
    assert db.add('Mesmo produto',config)==pid
    assert ui.product(token) is None


def test_group_input_uses_reply_to_authorized_user_and_ignores_casual_messages(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        update.effective_chat.type='group'
        update.effective_message.message_id=123
        ui.remember(update)
        click(update,'ui:search')
        await ui.callback(update,None)
        kwargs=update.effective_message.reply_text.await_args.kwargs
        assert kwargs['reply_markup'].force_reply and kwargs['reply_markup'].selective
        assert kwargs['reply_parameters'].message_id==123
        ui.clear()
        update.callback_query=None
        update.effective_message.text='Mensagem comum do grupo'
        before=update.effective_message.reply_text.await_count
        await ui.text(update,None)
        assert update.effective_message.reply_text.await_count==before
        assert not dispatch.called
    asyncio.run(scenario())


def test_ambiguous_thousands_input_does_not_become_one_real_fifty(setup):
    db,config,ui,dispatch,update=setup
    pid=db.add('Produto',config)
    token=ui.card_token(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])
    async def scenario():
        await ui.wizard(update,token)
        update.effective_message.text='1.500'
        await ui.text(update,None)
        assert ui.pending.values==[] and ui.pending.step==0 and not dispatch.called
        update.effective_message.text='1500'
        await ui.text(update,None)
        assert ui.pending.values==['1500.00']
    asyncio.run(scenario())


def test_discount_retry_and_cep_returns_to_stores(setup):
    db,config,ui,dispatch,update=setup
    async def scenario():
        config.browser=False
        fetcher=Fetcher(config)
        promotions=PromotionsTelegram(config,SimpleNamespace(fetcher=fetcher),AsyncMock(),lambda c:None)
        ui.promotions=promotions
        promotions.new_session()
        promotions.session.category=promotions.catalog.items['pets']
        promotions.session.stage='filter'
        await ui.prompt(update,'discount')
        update.effective_message.text='abc'
        await ui.text(update,None)
        assert ui.pending.kind=='discount'
        update.effective_message.text='>30'
        await ui.text(update,None)
        assert promotions.session.stage=='stores'
        await ui.prompt(update,'cep')
        update.effective_message.text='01001-000'
        await ui.text(update,None)
        assert promotions.session.cep=='01001000'
        markup=update.effective_message.reply_text.await_args.kwargs['reply_markup']
        assert any(b.callback_data.endswith(':run') for row in markup.inline_keyboard for b in row)
        await fetcher.close()
    asyncio.run(scenario())
