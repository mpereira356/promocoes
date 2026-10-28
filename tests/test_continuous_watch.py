import asyncio
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import urlsplit
import time
import pytest

from monitor.db import DB
from monitor.models import Reading
from monitor.watch import configure_watch
from monitor.service import Monitor
from monitor.history import history_text


@pytest.fixture
def state(tmp_path):
    path = str(tmp_path / 'watch.sqlite')
    db = DB(path)
    config = SimpleNamespace(minimum=10000, percent=Decimal('20'), target=100000,
        interval=18000, user=42, chat=-1, domains=('kabum.com.br','pichau.com.br'))
    reading = Reading('Placa-Mãe MSI MAG X870 Tomahawk WiFi', 'KaBuM!', '', 'Pix',
                      239999, 'in_stock', identifiers={'brand':'msi'})
    ad = db.save_ad('https://www.kabum.com.br/produto/636779/msi-x870', 'KaBuM', reading)
    pid,_ = db.subscribe(db.request_scope(ad['id']), 'site', config)
    candidate = db.rows('SELECT * FROM candidates WHERE product=?', (pid,))[0]
    update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_chat=SimpleNamespace(id=-1),
                              effective_message=SimpleNamespace(reply_text=AsyncMock()))
    yield db,config,reading,ad,pid,candidate,update,path
    db.conn.close()


def test_one_telegram_command_configures_everything_and_is_repeat_safe(state):
    async def run():
        db,c,r,ad,pid,candidate,update,path = state
        db.run("UPDATE products SET active=0,alert_mode='drops' WHERE id=?", (pid,))
        db.record(candidate, r)
        on_check = Mock()
        await configure_watch(update,c,db,[str(pid),'15'],on_check)
        row = db.rows('SELECT * FROM products WHERE id=?',(pid,))[0]
        assert row['scope']=='all' and row['active']==1 and row['alert_mode']=='all'
        assert row['interval_seconds']==900 and row['next_due']==0 and row['monitor_policy']=='listing_price'
        assert row['minimum']==10000 and row['percent']=='20' and row['target']==100000
        assert db.rows('SELECT COUNT(*) AS n FROM checks')[0]['n']==1
        assert not db.rows('SELECT * FROM series')  # No retroactive made-up baseline.
        on_check.assert_called_once_with(pid)
        text=update.effective_message.reply_text.await_args.args[0]
        assert 'condição' in text.lower() and 'não é detecção em tempo real' in text.lower()
        await configure_watch(update,c,db,[str(pid),'15'],on_check)
        assert len(db.rows('SELECT * FROM products'))==1 and len(db.rows('SELECT * FROM candidates'))==1
        assert len(db.rows('SELECT * FROM subscriptions'))==1
    asyncio.run(run())


@pytest.mark.parametrize('value',['0','14','1441','NaN','Infinity','abc','-15','15x'])
def test_invalid_watch_minutes_never_partially_expand_or_resume(state,value):
    async def run():
        db,c,r,ad,pid,candidate,update,path = state
        before=dict(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])
        on_check=Mock()
        await configure_watch(update,c,db,[str(pid),value],on_check)
        assert dict(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])==before
        on_check.assert_not_called()
    asyncio.run(run())


@pytest.mark.parametrize('user,chat',[(99,-1),(42,-2)])
def test_watch_command_requires_authorized_user_and_chat(state,user,chat):
    async def run():
        db,c,r,ad,pid,candidate,update,path = state
        update.effective_user.id=user;update.effective_chat.id=chat
        check=Mock()
        await configure_watch(update,c,db,[str(pid),'15'],check)
        assert db.rows('SELECT scope FROM products WHERE id=?',(pid,))[0]['scope']=='site'
        check.assert_not_called();update.effective_message.reply_text.assert_not_called()
    asyncio.run(run())


def test_atomic_failure_rolls_back_scope_and_preferences(state,monkeypatch):
    db,c,r,ad,pid,candidate,update,path = state
    original=db._expand_monitor
    def broken(pid):
        original(pid)
        raise RuntimeError('simulate storage failure')
    monkeypatch.setattr(db,'_expand_monitor',broken)
    before=dict(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])
    with pytest.raises(RuntimeError):db.configure_watch(pid,15)
    assert dict(db.rows('SELECT * FROM products WHERE id=?',(pid,))[0])==before
    assert db.rows('SELECT scope FROM subscriptions')[0]['scope']=='site'


def test_published_price_policy_solves_missing_condition_without_inventing_it(state):
    db,c,r,ad,pid,candidate,update,path = state
    assert not r.comparable and r.listing_price_complete
    db.record(candidate,r)
    assert not db.rows('SELECT * FROM series')
    assert 'Ainda não há preço inicial' in history_text(db,pid)
    assert 'R$ 2.399,99' in history_text(db,pid) and 'Detalhes:' not in history_text(db,pid)
    db.configure_watch(pid,15)
    db.record(candidate,r)  # New, fresh read establishes the baseline.
    assert len(db.rows('SELECT * FROM series'))==1 and not db.rows('SELECT * FROM alerts')
    lower=replace(r,price=230000)
    db.record(candidate,lower);db.record(candidate,lower)
    db.record(candidate,replace(r,price=250000))
    alerts=db.rows('SELECT message FROM alerts')
    assert len(alerts)==2  # All changes; old drop thresholds do not block them.
    assert 'QUEDA DE PREÇO' in alerts[0]['message'] and 'AUMENTO DE PREÇO' in alerts[1]['message']
    assert all('Condição não declarada' in a['message'] for a in alerts)
    assert all('NewCondition' not in a['message'] for a in alerts)
    assert db.rows('SELECT condition FROM series')[0]['condition']==''
    db.record(candidate,replace(r,condition='NewCondition',price=190000))
    assert len(db.rows('SELECT * FROM series'))==2 and len(db.rows('SELECT * FROM alerts'))==2
    text=history_text(db,pid)
    assert 'apenas leitura' in text and 'registrado no acompanhamento' in text


@pytest.mark.parametrize('patch',[{'price':0},{'price':None},{'price':True},{'payment':''},
    {'seller':''},{'currency':'USD'},{'stock':'unknown'},{'stock':'out_of_stock'}])
def test_published_watch_does_not_bypass_other_missing_fields(state,patch):
    db,c,r,ad,pid,candidate,update,path = state
    db.configure_watch(pid,15)
    db.record(candidate,replace(r,**patch))
    assert not db.rows('SELECT * FROM series') and not db.rows('SELECT * FROM alerts')


def test_existing_other_monitor_is_not_merged_or_reconfigured(state):
    db,c,r,ad,pid,candidate,update,path = state
    other,_=db.subscribe(db.request_scope(ad['id']),'all',c)
    assert db.configure_watch(pid,15)==('existing',other)
    assert db.rows('SELECT scope FROM products WHERE id=?',(pid,))[0]['scope']=='site'
    assert all(row['monitor_policy']=='strict' for row in db.rows('SELECT * FROM products'))


def test_persistent_watch_scheduler_runs_overdue_once_then_waits_after_restart(state,monkeypatch):
    async def run():
        db,c,r,ad,pid,candidate,update,path=state
        db.configure_watch(pid,15);db.conn.close()
        reopened=DB(path)
        saved=reopened.rows('SELECT * FROM products WHERE id=?',(pid,))[0]
        assert saved['interval_seconds']==900 and saved['monitor_policy']=='listing_price'
        assert saved['active']==1 and saved['scope']=='all' and saved['alert_mode']=='all'
        m=Monitor(reopened,c,None,None,AsyncMock())
        async def check(pid):reopened.run('UPDATE products SET next_due=? WHERE id=?',(time.time()+900,pid))
        m.check=AsyncMock(side_effect=check)
        async def stop(_):raise asyncio.CancelledError()
        monkeypatch.setattr('monitor.service.asyncio.sleep',stop)
        with pytest.raises(asyncio.CancelledError):await m.scheduler()
        m.check.assert_awaited_once_with(pid)
        reopened.conn.close();reopened=DB(path)
        m=Monitor(reopened,c,None,None,AsyncMock());m.check=AsyncMock()
        with pytest.raises(asyncio.CancelledError):await m.scheduler()
        m.check.assert_not_awaited();reopened.conn.close()
    asyncio.run(run())


def test_stale_queued_scheduler_job_does_not_repeat_a_manual_check(state,monkeypatch):
    async def run():
        db,c,r,ad,pid,candidate,update,path=state
        db.configure_watch(pid,15)
        m=Monitor(db,c,None,None,AsyncMock());m.check=AsyncMock()
        async def runner(factory):
            if getattr(factory,'__name__','')=='<lambda>':
                db.run('UPDATE products SET next_due=? WHERE id=?',(time.time()+900,pid))
            return await factory()
        async def stop(_):raise asyncio.CancelledError()
        monkeypatch.setattr('monitor.service.asyncio.sleep',stop)
        with pytest.raises(asyncio.CancelledError):await m.scheduler(runner)
        m.check.assert_not_awaited()
    asyncio.run(run())


def test_real_kabum_fixture_retains_unknown_condition_but_can_watch_public_price(state):
    from monitor.adapters.kabum import KabumAdapter
    db,c,r,ad,pid,candidate,update,path=state
    html=Path('tests/fixtures/kabum_x870_published_real.html').read_text(encoding='utf-8')
    reading,=KabumAdapter().parse(html,'https://www.kabum.com.br/produto/636779/msi')
    assert reading.price==239999 and reading.condition=='' and reading.payment=='Pix'
    assert not reading.comparable and reading.listing_price_complete


def test_full_monitor_check_records_unknown_condition_price_and_delivers_changes_once(state):
    async def run():
        db,c,r,ad,pid,candidate,update,path=state
        db.configure_watch(pid,15)
        search=SimpleNamespace(links=AsyncMock(return_value=[]))
        fetcher=SimpleNamespace(canonical=lambda u:(u,urlsplit(u).hostname.removeprefix('www.')))
        send=AsyncMock()
        monitor=Monitor(db,c,fetcher,search,send)
        monitor.read=AsyncMock(return_value=[r])
        first=await monitor.check(pid)
        assert 'Condição não declarada' in first and len(db.rows('SELECT * FROM series'))==1
        send.assert_not_awaited()
        monitor.read=AsyncMock(return_value=[replace(r,price=230000)])
        await monitor.check(pid)
        await monitor.check(pid)
        send.assert_awaited_once()
        assert 'QUEDA DE PREÇO' in send.await_args.args[0]
        assert db.rows('SELECT sent_at FROM alerts')[0]['sent_at'] is not None
        assert db.rows('SELECT next_due FROM products WHERE id=?',(pid,))[0]['next_due']>time.time()+895
    asyncio.run(run())
