import asyncio
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from monitor.db import DB
from monitor.loans import Loans, TZ, parse_amount, parse_date
from monitor.menu import BotMenu


def timestamp(hour, day=20):
    return datetime(2030, 10, day, hour, tzinfo=TZ).timestamp()


@pytest.mark.parametrize(('text', 'expected'), [('150', 15000), ('1.250,50', 125050), ('R$ 25,99', 2599)])
def test_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize('text', ['0', '-10', 'nan', '1.250', 'abc', '10,555'])
def test_invalid_amount(text):
    with pytest.raises(ValueError): parse_amount(text)


def test_date_validation():
    assert parse_date('20/10/2030', date(2030, 10, 20)) == '2030-10-20'
    for text in ('19/10/2030', '31/02/2030', 'amanha'):
        with pytest.raises(ValueError): parse_date(text, date(2030, 10, 20))


def test_two_reminders_and_no_repeats_after_database_reopen(tmp_path):
    async def run():
        path = tmp_path / 'loans.db'
        db = DB(path)
        loans = Loans(db)
        loans.add('Joao', 15000, '2030-10-20')
        send = AsyncMock()
        await loans.tick(send, timestamp(8))
        assert send.await_count == 0
        await asyncio.gather(loans.tick(send, timestamp(9)), loans.tick(send, timestamp(9)))
        assert send.await_count == 1
        db.conn.close()
        db = DB(path)
        loans = Loans(db)
        await loans.tick(send, timestamp(12))
        assert send.await_count == 1
        await loans.tick(send, timestamp(18))
        await loans.tick(send, timestamp(20))
        await loans.tick(send, timestamp(20, day=21))
        assert send.await_count == 2
        assert '150,00' in send.await_args.args[0]
        db.conn.close()
    asyncio.run(run())


def test_payment_stops_and_postponement_creates_two_new_reminders():
    async def run():
        db = DB(':memory:')
        loans = Loans(db)
        lid = loans.add('Maria', 5000, '2030-10-20')
        send = AsyncMock()
        await loans.tick(send, timestamp(9))
        loans.postpone(lid, '2030-10-21')
        await loans.tick(send, timestamp(18))
        assert send.await_count == 1
        await loans.tick(send, timestamp(9, day=21))
        assert send.await_count == 2
        loans.pay(lid)
        loans.postpone(lid, '2030-10-22')
        await loans.tick(send, timestamp(18, day=21))
        assert send.await_count == 2
        assert loans.get(lid)['due'] == '2030-10-21'
        db.conn.close()
    asyncio.run(run())


def test_send_failure_retries_and_missed_reminders_are_spaced():
    async def run():
        db = DB(':memory:')
        loans = Loans(db)
        loans.add('Ana', 12000, '2030-10-20')
        send = AsyncMock(side_effect=RuntimeError('network'))
        await loans.tick(send, timestamp(19))
        assert not db.rows('SELECT * FROM loan_reminders')
        send.side_effect = None
        await loans.tick(send, timestamp(19))
        await loans.tick(send, timestamp(19)+30)
        assert send.await_count == 2  # uma falha e um envio
        await loans.tick(send, timestamp(20))
        assert send.await_count == 3
        db.conn.close()
    asyncio.run(run())


def test_menu_wizard_authorization_payment_and_cancel():
    async def run():
        db = DB(':memory:')
        ui = BotMenu(SimpleNamespace(user=42, chat=42), db,
                     SimpleNamespace(running=False, refreshing=False, session=None), AsyncMock(), '')
        message = SimpleNamespace(text='', reply_text=AsyncMock())
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_chat=SimpleNamespace(id=42, type='private'), effective_message=message, callback_query=None)

        async def click(action):
            update.callback_query = SimpleNamespace(data='ui:'+action, answer=AsyncMock(), edit_message_text=AsyncMock())
            await ui.callback(update, None)

        await click('loans:new')
        for text in ('Joao <Silva>', '125,50', '25/12/2099'):
            update.callback_query = None
            message.text = text
            await ui.text(update, None)
        row = db.rows('SELECT * FROM loans')[0]
        assert row['person'] == 'Joao <Silva>' and row['amount'] == 12550
        assert not db.rows('SELECT * FROM products')
        assert '&lt;Silva&gt;' in message.reply_text.await_args.args[0]
        await click('loans:pay:1')
        assert ui.loans.loans.get(1)['paid_at'] is None
        update.effective_user.id = 99
        await click('loans:paid:1')
        assert ui.loans.loans.get(1)['paid_at'] is None
        update.effective_user.id = 42
        await click('loans:paid:1')
        assert ui.loans.loans.get(1)['paid_at'] is not None
        await click('loans:new')
        await click('home')
        assert ui.loans.pending is None
        db.conn.close()
    asyncio.run(run())


def test_menu_postponement_and_invalid_answer_preserve_pending_record():
    async def run():
        db = DB(':memory:')
        ui = BotMenu(SimpleNamespace(user=42, chat=42), db,
                     SimpleNamespace(running=False, refreshing=False, session=None), AsyncMock(), '')
        loans = ui.loans.loans
        lid = loans.add('Ana', 10000, '2099-12-24')
        message = SimpleNamespace(text='', reply_text=AsyncMock())
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_chat=SimpleNamespace(id=42, type='private'), effective_message=message, callback_query=None)
        await ui.loans.action(update, f'loans:postpone:{lid}')
        message.text = '31/02/2099'
        await ui.text(update, None)
        assert loans.get(lid)['due'] == '2099-12-24'
        assert ui.loans.pending['step'] == 'date'
        message.text = '25/12/2099'
        await ui.text(update, None)
        assert loans.get(lid)['due'] == '2099-12-25'
        assert loans.get(lid)['revision'] == 1
        await ui.loans.action(update, f'loans:unpaid:{lid}')
        assert loans.get(lid)['paid_at'] is None
        await ui.loans.listing(update, paid=True)
        assert not loans.get(lid)['paid_at']
        db.conn.close()
    asyncio.run(run())
