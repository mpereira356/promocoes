import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from monitor.adapters.base import ReadError
from monitor.network import Fetcher
from monitor.search_results import deliver_search


def test_successful_search_sends_offers_before_completion(monkeypatch):
    async def run():
        send = AsyncMock()
        url = 'https://www.pichau.com.br/product'
        reading = SimpleNamespace(title='B550')
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=[url])), read=AsyncMock(return_value=[reading]))
        fetcher = SimpleNamespace(canonical=lambda u: (u, 'pichau.com.br'))
        db = SimpleNamespace(save_ad=lambda *a: {'id': 7})
        async def offer(*args):
            await send('Oferta 7')
        monkeypatch.setattr('monitor.search_results.send_offer', offer)
        monkeypatch.setattr('monitor.search_results.rank_offers', lambda offers: [(reading, url, 'Pichau', 1, False)])
        await deliver_search(monitor, fetcher, db, None, 1, 'b550', send)
        assert send.await_args_list[0].args[0] == 'Oferta 7'
        assert 'Ofertas enviadas: 1\nLinks com falha de leitura: 0' in send.await_args_list[-1].args[0]
    asyncio.run(run())


@pytest.mark.parametrize('failure', [None, ReadError('blocked_no_bypass'), RuntimeError('private detail')])
def test_search_always_finishes_and_does_not_expose_internal_errors(failure):
    async def run():
        send = AsyncMock()
        monitor = SimpleNamespace(
            search=SimpleNamespace(links=AsyncMock(return_value=['https://www.pichau.com.br/product'])),
            read=AsyncMock(side_effect=failure, return_value=[]),
        )
        await deliver_search(monitor, None, None, None, 1, 'b550', send)
        messages = [c.args[0] for c in send.await_args_list]
        assert messages[-1].startswith('⚠️ Pesquisa concluída com limitações')
        assert 'Links com falha de leitura: 1' in messages[-1]
        assert all('private detail' not in m for m in messages)
        assert all('Pesquisa: b550' in m for m in messages)
        assert monitor.read.await_count == 1
    asyncio.run(run())


def test_discovery_failure_finishes_with_honest_status():
    async def run():
        send = AsyncMock()
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(side_effect=ReadError('search_unavailable'))))
        await deliver_search(monitor, None, None, None, 1, 'b550', send)
        assert send.await_args_list[-1].args[0].startswith('⚠️ Pesquisa encerrada com falha')
    asyncio.run(run())


@pytest.mark.parametrize('reason,retries', [('browser_navigation_failed_TimeoutError', 3), ('browser_connection_failed', 3), ('captcha_no_bypass', 1), ('blocked_no_bypass', 1)])
def test_transient_browser_errors_retry_but_blocks_do_not(reason, retries, monkeypatch):
    async def run():
        f = Fetcher(SimpleNamespace(browser=True, domains=('pichau.com.br',), delay=0))
        f.public = AsyncMock()
        transport = SimpleNamespace(get=AsyncMock(side_effect=ReadError(reason)), close=AsyncMock())
        f.browser_transport = transport
        monkeypatch.setattr('monitor.network.asyncio.sleep', AsyncMock())
        try:
            with pytest.raises(ReadError):
                await f.request('https://www.pichau.com.br/product')
            assert transport.get.await_count == retries
        finally:
            await f.close()
    asyncio.run(run())


@pytest.mark.parametrize('recovers', [True, False])
def test_dns_retries_are_bounded_and_private_addresses_stay_blocked(monkeypatch, recovers):
    async def run():
        f = Fetcher(SimpleNamespace(domains=('pichau.com.br',), browser=False))
        public = [(None, None, None, None, ('8.8.8.8', 443))]
        dns = AsyncMock(side_effect=[OSError('private detail'), OSError('private detail'), public if recovers else OSError('private detail')])
        monkeypatch.setattr(asyncio.get_running_loop(), 'getaddrinfo', dns)
        sleep = AsyncMock()
        monkeypatch.setattr('monitor.network.asyncio.sleep', sleep)
        try:
            if recovers:
                await f.public('https://www.pichau.com.br/product')
            else:
                with pytest.raises(ReadError, match='network_dns_failure'):
                    await f.public('https://www.pichau.com.br/product')
            assert dns.await_count == 3 and sleep.await_count == 2
            dns.side_effect = None
            dns.return_value = [(None, None, None, None, ('127.0.0.1', 443))]
            with pytest.raises(ReadError, match='non_public_address'):
                await f.public('https://www.pichau.com.br/product')
        finally:
            await f.close()
    asyncio.run(run())


def test_exact_offer_diagnostic_does_not_echo_rejected_credentials():
    import json
    from scripts.diagnose_offers import diagnose
    async def run():
        config = SimpleNamespace(domains=('pichau.com.br',), browser=False)
        report = await diagnose(config, ['https://name:private-secret@www.pichau.com.br/product'])
        assert 'private-secret' not in json.dumps(report)
        assert report['offers'][0]['price_verified'] is False
    asyncio.run(run())


def test_store_refusal_pauses_only_that_store_and_expires(monkeypatch):
    import httpx
    async def run():
        config = SimpleNamespace(domains=('pichau.com.br', 'kabum.com.br'), browser=False, delay=0)
        f = Fetcher(config)
        f.public = AsyncMock()
        pichau = 'https://www.pichau.com.br/product'
        kabum = 'https://www.kabum.com.br/produto/123/product'
        get = AsyncMock(side_effect=[
            httpx.Response(403, text='Access denied', request=httpx.Request('GET', pichau)),
            httpx.Response(200, text='Other store', request=httpx.Request('GET', kabum)),
            httpx.Response(200, text='Recovered', request=httpx.Request('GET', pichau)),
        ])
        monkeypatch.setattr(f.client, 'get', get)
        monkeypatch.setattr('monitor.network.asyncio.sleep', AsyncMock())
        try:
            with pytest.raises(ReadError, match='blocked_no_bypass'):
                await f.request(pichau)
            with pytest.raises(ReadError, match='domain_access_cooldown'):
                await f.request(pichau + '-another')
            assert get.await_count == 1
            assert (await f.request(kabum))[0] == 'Other store'
            f.access_paused['pichau.com.br'] = -1
            assert (await f.request(pichau))[0] == 'Recovered'
            assert get.await_count == 3
        finally:
            await f.close()
    asyncio.run(run())


def test_catalogs_are_grouped_and_never_reported_as_verified_offers():
    from monitor.discovery import SearchLinks, LinkCandidate
    async def run():
        urls = [f'https://www.mercadolivre.com.br/logitech/p/MLB{i}' for i in range(6)]
        links = SearchLinks(urls, candidates={u: LinkCandidate(u, f'Logitech {i}', 'Tavily Search') for i, u in enumerate(urls)})
        read, send = AsyncMock(), AsyncMock()
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=links)), read=read)
        f = SimpleNamespace(canonical=lambda u: (u, 'mercadolivre.com.br'))
        await deliver_search(monitor, f, None, None, 1, 'Logitech', send)
        read.assert_not_awaited()
        assert send.await_count == 2
        text = send.await_args_list[0].args[0]
        assert 'links sem preço confirmado' in text
        assert all(u in text for u in urls)
        summary = send.await_args_list[-1].args[0]
        assert summary.startswith('⚠️ Pesquisa concluída com limitações')
        assert 'Ofertas enviadas: 0' in summary and 'Links para conferência: 6' in summary
    asyncio.run(run())


def test_redirected_wrong_brand_is_discarded_without_save_or_read_error():
    async def run():
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=['https://www.terabyteshop.com.br/produto/1/keyboard'])),
            read=AsyncMock(return_value=[SimpleNamespace(title='Teclado Mecânico Corsair K65 Pro Mini RGB')]))
        send = AsyncMock()
        await deliver_search(monitor, None, None, None, 1, 'Teclado Mecanico Logitech G PRO RGB', send)
        assert send.await_count == 1
        summary = send.await_args.args[0]
        assert 'Ofertas enviadas: 0' in summary
        assert 'Links com falha de leitura: 0' in summary
        assert 'Candidatos descartados por incompatibilidade: 1' in summary
    asyncio.run(run())


def test_refusal_skips_remaining_store_links_but_keeps_other_store(monkeypatch):
    async def run():
        urls = [f'https://www.pichau.com.br/keyboard-{i}' for i in range(6)] + ['https://www.kabum.com.br/produto/1/keyboard']
        reading = SimpleNamespace(title='Teclado Logitech G PRO RGB', price=10000)
        read = AsyncMock(side_effect=[ReadError('blocked_no_bypass'), [reading]])
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=urls)), read=read)
        f = SimpleNamespace(canonical=lambda u: (u, 'kabum.com.br'))
        db = SimpleNamespace(save_ad=lambda *a: {'id': 1})
        monkeypatch.setattr('monitor.search_results.rank_offers', lambda values: [(r,u,s,None,False) for r,u,s in values])
        monkeypatch.setattr('monitor.search_results.send_offer', AsyncMock())
        send = AsyncMock()
        await deliver_search(monitor, f, db, None, 0, 'Teclado Logitech G PRO RGB', send)
        assert read.await_count == 2
        text = '\n'.join(c.args[0] for c in send.await_args_list)
        assert text.count('acesso suspenso') == 1
        assert 'Outros links não consultados nesta busca: 5' in text
        assert 'Ofertas enviadas: 1' in text
    asyncio.run(run())


def test_shared_external_quota_has_one_notice_for_affected_stores():
    from monitor.discovery import SearchLinks
    async def run():
        notices = [f'{store}: O limite da busca externa sem chave foi atingido. Aguarde antes de tentar novamente.' for store in ('Terabyte', 'Mercado Livre', 'Amazon Brasil')]
        notices += ['Mercado Livre: a descoberta falhou nesta consulta. Isso não prova que o produto não exista.']
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=SearchLinks([], notices))))
        send = AsyncMock()
        await deliver_search(monitor, None, None, None, 0, 'Logitech', send)
        text = '\n'.join(c.args[0] for c in send.await_args_list)
        assert text.count('Índice externo temporariamente limitado') == 1
        assert 'Terabyte, Mercado Livre, Amazon Brasil' in text
        assert 'a descoberta falhou' not in text
    asyncio.run(run())


def test_quota_reuses_saved_matching_link_but_reads_price_again(monkeypatch):
    from monitor.discovery import SearchLinks
    async def run():
        url = 'https://www.terabyteshop.com.br/produto/123/teclado-logitech-g-pro'
        rows = [dict(url=url, title='Teclado Logitech G PRO RGB', store='Terabyte'),
            dict(url=url+'-mouse', title='Mouse Logitech G PRO RGB', store='Terabyte')]
        db = SimpleNamespace(rows=lambda sql: rows, save_ad=lambda *args: {'id': 5})
        reading = SimpleNamespace(title='Teclado Logitech G PRO RGB', price=12345)
        notice = 'Terabyte: O limite da busca externa sem chave foi atingido.'
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=SearchLinks([], [notice]))), read=AsyncMock(return_value=[reading]))
        monkeypatch.setattr('monitor.search_results.rank_offers', lambda values: [(r,u,s,None,False) for r,u,s in values])
        offer = AsyncMock()
        monkeypatch.setattr('monitor.search_results.send_offer', offer)
        send = AsyncMock()
        await deliver_search(monitor, SimpleNamespace(canonical=lambda u:(u,'terabyteshop.com.br')), db, None, 0, 'Teclado Logitech G PRO RGB', send)
        monitor.read.assert_awaited_once_with(url)
        assert offer.await_args.args[2].price == 12345
        assert 'SQLite' in '\n'.join(c.args[0] for c in send.await_args_list)
    asyncio.run(run())


@pytest.mark.parametrize('stage', ['save', 'send'])
@pytest.mark.parametrize('failure_kind', ['timeout', 'bad_request', 'internal'])
def test_failed_fourth_result_does_not_abort_remaining_or_resend_previous(monkeypatch,caplog,stage,failure_kind):
    from monitor.models import Reading
    from telegram.error import TimedOut,BadRequest
    async def run():
        urls=[f'https://www.amazon.com.br/dp/B0TEST000{i}' for i in range(5)]
        readings=[Reading(f'Aspirador portatil {i}','','','',10000+i) for i in range(5)]
        monitor=SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=urls)),read=AsyncMock(side_effect=[[r] for r in readings]))
        f=SimpleNamespace(canonical=lambda u:(u,'amazon.com.br'))
        failure={'timeout':TimedOut('SECRET-MARKER'),'bad_request':BadRequest('SECRET-MARKER'),'internal':RuntimeError('SECRET-MARKER')}[failure_kind]
        saved,attempted,delivered=[],[],[]
        def save(url,*args):
            saved.append(url)
            if stage=='save' and url==urls[3]:raise failure
            return {'id':urls.index(url)+1}
        async def offer(bot,chat,r,url,*args):
            attempted.append(url)
            if stage=='send' and url==urls[3]:raise failure
            delivered.append(url)
        monkeypatch.setattr('monitor.search_results.send_offer',offer)
        send=AsyncMock()
        await deliver_search(monitor,f,SimpleNamespace(save_ad=save),None,1,'Aspirador portatil',send)
        assert saved == urls
        assert delivered == urls[:3]+urls[4:]
        assert len(attempted) == (5 if stage=='send' else 4)
        summary=send.await_args_list[-1].args[0]
        assert 'Ofertas enviadas: 4' in summary
        assert 'Pre\u00e7os lidos nas ofertas enviadas: 4' in summary
        assert 'Pesquisa conclu\u00edda com limita\u00e7\u00f5es' in summary
        assert 'SECRET-MARKER' not in caplog.text
        assert 'stage='+('save_ad' if stage=='save' else 'send_offer') in caplog.text
        assert 'frames=' in caplog.text
        assert not any('interrompida' in c.args[0] for c in send.await_args_list)
    asyncio.run(run())


def test_failed_warning_does_not_suppress_summary_or_escape(caplog):
    from monitor.discovery import SearchLinks
    async def run():
        m=SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=SearchLinks([],['Aviso teste']))))
        send=AsyncMock(side_effect=[None,RuntimeError('SECRET-MARKER'),None])
        await deliver_search(m,None,None,None,1,'Aspirador',send)
        assert send.await_count==3
        assert 'Avisos com entrega n\u00e3o confirmada: 1' in send.await_args_list[-1].args[0]
        assert 'SECRET-MARKER' not in caplog.text
    asyncio.run(run())


def test_unavailable_telegram_summary_failure_is_logged_without_recursive_send(caplog):
    from monitor.discovery import SearchLinks
    async def run():
        m=SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=SearchLinks([]))))
        send=AsyncMock(side_effect=RuntimeError('SECRET-MARKER'))
        await deliver_search(m,None,None,None,1,'Aspirador',send)
        assert send.await_count==3
        assert 'SECRET-MARKER' not in caplog.text
        assert 'stage=report' in caplog.text
    asyncio.run(run())


def test_real_formatter_and_sqlite_continue_after_telegram_rejects_one_card(tmp_path):
    from monitor.db import DB
    from monitor.models import Reading
    from telegram.error import BadRequest
    async def run():
        urls=[f'https://www.amazon.com.br/dp/B0TEST000{i}' for i in range(5)]
        values=[Reading(f'Aspirador portatil {i}','','','',10000+i) for i in range(5)]
        monitor=SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=urls)),read=AsyncMock(side_effect=[[r] for r in values]))
        f=SimpleNamespace(canonical=lambda u:(u,'amazon.com.br'))
        attempted=[]
        async def telegram_send(chat,text,**kwargs):
            attempted.append(text)
            if 'Aspirador portatil 3' in text:raise BadRequest('simulated rejection')
        bot=SimpleNamespace(send_message=AsyncMock(side_effect=telegram_send))
        send=AsyncMock()
        db=DB(str(tmp_path/'delivery.sqlite'))
        try:
            await deliver_search(monitor,f,db,bot,1,'Aspirador portatil',send)
            assert len(db.rows('SELECT * FROM ads'))==5
            assert len(attempted)==5
            assert all(any(r.title in text for text in attempted) for r in values)
            assert 'Ofertas enviadas: 4' in send.await_args_list[-1].args[0]
            assert 'entrega incompleta ou n\u00e3o confirmada: 1' in send.await_args_list[-1].args[0]
        finally:db.conn.close()
    asyncio.run(run())
