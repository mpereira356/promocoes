import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from monitor.work_queue import WorkQueue, queued_handler


def test_jobs_are_fifo_and_never_overlap():
    async def run():
        queue = WorkQueue()
        started, release = asyncio.Event(), asyncio.Event()
        events = []

        async def first():
            events.append('first-start')
            started.set()
            await release.wait()
            events.append('first-end')

        async def job(name): events.append(name)
        try:
            one = queue.submit(first)
            await started.wait()
            two = queue.submit(lambda: job('second'))
            three = queue.submit(lambda: job('third'))
            assert queue.busy and len(queue.items) == 2
            assert events == ['first-start']
            release.set()
            await asyncio.gather(one, two, three)
            assert events == ['first-start', 'first-end', 'second', 'third']
        finally: await queue.close()
    asyncio.run(run())


def test_command_background_results_finish_before_next_command():
    async def run():
        queue = WorkQueue()
        started, release = asyncio.Event(), asyncio.Event()
        events = []

        async def child(): events.append('results')
        async def second_child(): events.append('results-2')

        async def command():
            started.set()
            await release.wait()
            events.append('acknowledgment')
            queue.submit(child)
            queue.submit(second_child)

        async def next_command(): events.append('next-command')
        try:
            first = queue.submit(command)
            await started.wait()
            next_job = queue.submit(next_command)
            release.set()
            await asyncio.gather(first, next_job)
            assert events == ['acknowledgment', 'results', 'results-2', 'next-command']
        finally: await queue.close()
    asyncio.run(run())


def test_exception_does_not_stop_queue_and_nested_run_does_not_deadlock():
    async def run():
        queue = WorkQueue()

        async def bad(): raise ValueError('private')
        async def result(): return 42
        async def parent(): return await queue.run(result)
        try:
            bad_job = queue.submit(bad)
            good_job = queue.submit(parent)
            with pytest.raises(ValueError): await bad_job
            assert await asyncio.wait_for(good_job, 1) == 42
        finally: await queue.close()
    asyncio.run(run())


def test_close_cancels_active_job_and_closes_unstarted_coroutines():
    async def run():
        queue = WorkQueue()
        started = asyncio.Event()
        async def active():
            started.set()
            await asyncio.Event().wait()
        async def pending(): return 1
        one = queue.submit(active)
        await started.wait()
        coro = pending()
        two = queue.submit(lambda: coro, cleanup=coro.close)
        await queue.close()
        assert one.cancelled() and two.cancelled()
        assert coro.cr_frame is None
        with pytest.raises(RuntimeError): queue.submit(pending)
    asyncio.run(run())


def update(text='/buscar Cadeira A08', user=42):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    return SimpleNamespace(effective_user=SimpleNamespace(id=user),
                           effective_chat=SimpleNamespace(id=42), effective_message=message,
                           callback_query=None)


def test_handler_receives_and_acknowledges_more_than_16_requests_while_busy():
    async def run():
        queue = WorkQueue()
        started, release = asyncio.Event(), asyncio.Event()
        seen = []
        async def active():
            started.set()
            await release.wait()
        async def callback(u, c): seen.append(u.effective_message.text)
        config = SimpleNamespace(user=42, chat=42)
        handler = queued_handler(queue, callback, config)
        try:
            first = queue.submit(active)
            await started.wait()
            updates = [update('/buscar Produto '+str(i)) for i in range(20)]
            # Os handlers retornam ao receber, sem ocupar slots do PTB ate o fim da busca.
            for u in updates: await asyncio.wait_for(handler(u, None), 1)
            assert not seen and len(queue.items) == 20
            assert all('entrou na fila' in u.effective_message.reply_text.await_args.args[0] for u in updates)
            release.set()
            await first
            await queue.run(lambda: asyncio.sleep(0))
            assert seen == ['/buscar Produto '+str(i) for i in range(20)]
        finally: await queue.close()
    asyncio.run(run())


def test_queued_button_is_acknowledged_immediately_and_does_not_reuse_expired_callback():
    async def run():
        queue = WorkQueue()
        started, release = asyncio.Event(), asyncio.Event()
        async def active():
            started.set()
            await release.wait()
        u = update()
        u.callback_query = SimpleNamespace(data='ui:list:0', answer=AsyncMock(), message=u.effective_message,
                                           edit_message_text=AsyncMock())
        async def callback(deferred, context):
            await deferred.callback_query.answer('Opção processada.', show_alert=True)
            await deferred.callback_query.edit_message_text('Resultado')
        try:
            queue.submit(active)
            await started.wait()
            await queued_handler(queue, callback, SimpleNamespace(user=42, chat=42))(u, None)
            u.callback_query.answer.assert_awaited_once_with('Pedido colocado na fila.')
            u.callback_query.edit_message_text.assert_not_awaited()
            release.set()
            await queue.run(lambda: asyncio.sleep(0))
            u.callback_query.answer.assert_awaited_once()
            u.callback_query.edit_message_text.assert_awaited_once_with('Resultado')
            assert u.effective_message.reply_text.await_args.args[0] == 'Opção processada.'
        finally: await queue.close()
    asyncio.run(run())


def test_failed_queue_notice_does_not_discard_request():
    async def run():
        queue = WorkQueue()
        started, release = asyncio.Event(), asyncio.Event()
        async def active():
            started.set()
            await release.wait()
        callback = AsyncMock()
        u = update()
        u.effective_message.reply_text.side_effect = RuntimeError('network')
        try:
            queue.submit(active)
            await started.wait()
            await queued_handler(queue, callback, SimpleNamespace(user=42, chat=42))(u, None)
            release.set()
            await queue.run(lambda: asyncio.sleep(0))
            callback.assert_awaited_once_with(u, None)
        finally: await queue.close()
    asyncio.run(run())


def test_scheduler_rechecks_pause_after_waiting_for_queue(monkeypatch):
    from monitor.db import DB
    from monitor.service import Monitor
    async def run():
        db = DB(':memory:')
        config = SimpleNamespace(minimum=0, percent=0, target=None)
        pid = db.add('Produto', config)
        monitor = Monitor(db, config, None, None, AsyncMock())
        monitor.deliver = AsyncMock()
        monitor.check = AsyncMock()
        calls = 0
        async def runner(factory):
            nonlocal calls
            calls += 1
            if calls == 2: db.run('UPDATE products SET active=0 WHERE id=?', (pid,))
            return await factory()
        monkeypatch.setattr('monitor.service.asyncio.sleep', AsyncMock(side_effect=asyncio.CancelledError))
        try:
            with pytest.raises(asyncio.CancelledError): await monitor.scheduler(runner)
            assert calls == 2
            monitor.check.assert_not_awaited()
        finally: db.conn.close()
    asyncio.run(run())


@pytest.mark.parametrize('change', ['pay', 'postpone'])
def test_loan_scheduler_rechecks_state_after_waiting_in_queue(monkeypatch, change):
    from monitor.db import DB
    from monitor.loans import Loans
    async def run():
        db = DB(':memory:')
        loans = Loans(db)
        lid = loans.add('Pessoa', 10000, '2020-01-01')
        queue = WorkQueue()
        started, release, scheduled = asyncio.Event(), asyncio.Event(), asyncio.Event()
        send = AsyncMock()

        async def active():
            started.set()
            await release.wait()

        async def update_loan():
            if change == 'pay': loans.pay(lid)
            else: loans.postpone(lid, '2099-01-01')

        async def runner(factory):
            future = queue.submit(factory)
            scheduled.set()
            return await future

        monkeypatch.setattr('monitor.loans.asyncio.sleep', AsyncMock(side_effect=asyncio.CancelledError))
        try:
            queue.submit(active)
            await started.wait()
            queue.submit(update_loan)
            task = asyncio.create_task(loans.scheduler(send, runner))
            await scheduled.wait()
            release.set()
            with pytest.raises(asyncio.CancelledError): await task
            send.assert_not_awaited()
            assert not db.rows('SELECT * FROM loan_reminders')
        finally:
            await queue.close()
            db.conn.close()
    asyncio.run(run())
