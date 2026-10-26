"""Regression for the user's MSI X870 Tomahawk results and duplicate cards."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from telegram.error import BadRequest, TimedOut, NetworkError, RetryAfter
from monitor.discovery import relevance
from monitor.identity import same_product, monitoring_search_terms
from monitor.models import Reading
from monitor.presentation import rank_offers, send_offer
from monitor.search_results import deliver_search
from monitor.network import Fetcher

QUERY = 'Placa-Mãe MSI MAG X870 Tomahawk WiFi'
CORRECT = 'Placa-Mãe MSI MAG X870 Tomahawk WiFi, AMD, AM5, DDR5, ATX'
WRONG = [
    'Placa-Mãe MSI PRO X870-P WiFi, AMD, AM5, DDR5, ATX',
    'Placa-Mãe MSI X870 GAMING PLUS WIFI, AMD, AM5, ATX, DDR5',
    'Processador AMD Ryzen 7 7800X3D + Placa-Mãe MSI MAG X870 Tomahawk WiFi',
    'Kit Upgrade, AMD Ryzen 9 9900X3D + Placa Mãe MSI X870 Gaming PLUS WIFI + Memória DDR5 16GB',
]


@pytest.mark.parametrize('title', WRONG)
def test_exact_requested_board_excludes_other_models_and_bundles(title):
    assert relevance(QUERY, title) == 0
    seed = Reading(CORRECT, '', '', '', None, identifiers={'mpn': 'same', 'brand': 'msi'})
    other = replace(seed, title=title)
    assert same_product(seed, other) is False


@pytest.mark.parametrize('title', [CORRECT, 'Placa Mãe MSI MAG X870 Tomahawk Wi-Fi, AM5, DDR5 | Terabyte',
                                  'MSI MAGX870TOMAHAWKWIFI AM5 DDR5'])
def test_exact_board_accepts_real_title_variations_and_part_number(title):
    assert relevance(QUERY, title)
    assert relevance('MSI MAGX870TOMAHAWKWIFI', title)


def test_monitoring_query_preserves_requested_model_family():
    assert monitoring_search_terms(CORRECT) == 'msi mag x870 tomahawk wifi'
    assert not relevance(QUERY, CORRECT.replace('X870', 'X870E'))
    assert relevance('placa mãe MSI X870', WRONG[0])  # An explicitly broad query may show different models.


def reading(title=CORRECT, **changes):
    return replace(Reading(title, 'Loja', 'NewCondition', 'Pix', 200000, 'in_stock'), **changes)


def test_pix_boleto_and_amazon_aliases_are_one_card_per_actual_offer():
    r = reading()
    rows = rank_offers([
        (replace(r, payment='Boleto'), 'https://www.amazon.com.br/item/dp/B012345678?ref=a', 'Amazon'),
        (r, 'https://www.amazon.com.br/dp/B012345678?tag=partner', 'Amazon'),
        (r, 'https://www.amazon.com.br/gp/product/B012345678', 'Amazon'),
    ])
    assert len(rows) == 1 and rows[0][0].payment == 'Pix'
    assert r.payment == 'Pix'  # Display deduplication does not mutate payment readings.


def test_different_sellers_or_variants_remain_separate():
    url = 'https://www.amazon.com.br/dp/B012345678'
    r = reading()
    assert len(rank_offers([(r, url, 'Amazon'), (replace(r, seller='Outra loja'), url, 'Amazon')])) == 2
    assert len(rank_offers([(r, url, 'Amazon'), (replace(r, identifiers={'mpn': 'another'}), url, 'Amazon')])) == 2


@pytest.mark.parametrize('error', [TimedOut(), NetworkError('connection lost')])
def test_ambiguous_photo_delivery_never_sends_a_duplicate_text(error):
    async def run():
        bot = SimpleNamespace(send_photo=AsyncMock(side_effect=error), send_message=AsyncMock())
        with pytest.raises(type(error)):
            await send_offer(bot, 1, reading(image='https://example.org/photo.jpg'), 'https://example.org/item')
        bot.send_photo.assert_awaited_once()
        bot.send_message.assert_not_awaited()
    asyncio.run(run())


def test_rejected_photo_falls_back_once_and_long_card_uses_only_text():
    async def run():
        bot = SimpleNamespace(send_photo=AsyncMock(side_effect=BadRequest('photo rejected')), send_message=AsyncMock())
        await send_offer(bot, 1, reading(image='https://example.org/photo.jpg'), 'https://example.org/item')
        bot.send_message.assert_awaited_once()
        bot.send_photo.reset_mock()
        bot.send_message.reset_mock()
        long_reading = reading(title='T' * 350, seller='S' * 100, payment='P' * 80,
                               identifiers={'generation': 'G' * 600}, image='https://example.org/photo.jpg')
        await send_offer(bot, 1, long_reading, 'https://example.org/item')
        bot.send_photo.assert_not_awaited()
        bot.send_message.assert_awaited_once()
    asyncio.run(run())


def test_photo_rate_limit_retries_only_explicitly_rejected_photo(monkeypatch):
    async def run():
        bot = SimpleNamespace(send_photo=AsyncMock(side_effect=[RetryAfter(1), None]), send_message=AsyncMock())
        sleep = AsyncMock()
        monkeypatch.setattr('asyncio.sleep', sleep)
        await send_offer(bot, 1, reading(image='https://example.org/photo.jpg'), 'https://example.org/item')
        assert bot.send_photo.await_count == 2
        sleep.assert_awaited_once()
        bot.send_message.assert_not_awaited()
    asyncio.run(run())


def test_search_delivery_rejects_wrong_products_before_saving_and_uses_one_ranking(monkeypatch):
    async def run():
        config = SimpleNamespace(domains=('kabum.com.br',), browser=False)
        fetcher = Fetcher(config)
        urls = [f'https://www.kabum.com.br/produto/{i}' for i in range(1, 7)]
        data = {url: [reading(title=title)] for url, title in zip(urls, WRONG + [CORRECT, CORRECT])}
        data[urls[-1]] += [reading(payment='Boleto')]
        data[urls[-2]] = [reading(condition='', price=190000)]
        monitor = SimpleNamespace(search=SimpleNamespace(links=AsyncMock(return_value=urls)),
                                  read=AsyncMock(side_effect=lambda url: data[url]))
        db = SimpleNamespace(save_ad=Mock(side_effect=lambda *args: {'id': 1}))
        delivered = AsyncMock()
        monkeypatch.setattr('monitor.search_results.send_offer', delivered)
        sent = AsyncMock()
        try:
            await deliver_search(monitor, fetcher, db, None, 1, QUERY, sent)
            assert db.save_ad.call_count == delivered.await_count == 2
            assert all(call.args[2].title == CORRECT for call in delivered.await_args_list)
            assert [call.args[5] for call in delivered.await_args_list] == [1, 2]
            assert sent.await_args_list[-1].args[0].startswith('🏁 Pesquisa finalizada')
            assert 'Candidatos descartados por incompatibilidade: 4' in sent.await_args_list[-1].args[0]
        finally:
            await fetcher.close()
    asyncio.run(run())
