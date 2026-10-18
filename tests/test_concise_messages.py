from monitor.message_style import short_reason, summarize_notices
from monitor.models import Reading
from monitor.presentation import offer_text
from monitor.telegram_text import render


def test_short_card_keeps_purchase_and_alert_restrictions():
    reading = Reading('Teclado <modelo>', 'Loja parceira', '', 'Pix', 21999, 'out_of_stock')
    text = offer_text(reading, 'KaBuM', ad_id=18)
    assert len(text) < 400
    assert 'R$ 219,99 · Pix' in text
    assert 'Loja parceira' in text and 'INDISPONÍVEL' in text
    assert 'Alertas suspensos' in text and 'condição' in text
    assert 'Frete não incluído' in text and '/monitorar 18' in text
    formatted = render(text, (reading.title,))
    assert '<b>Teclado &lt;modelo&gt;</b>' in formatted
    assert '<b>🆔 Anúncio 18' in formatted


def test_unknown_price_and_stock_remain_unknown_in_short_card():
    text = offer_text(Reading('Produto', '', '', '', None), 'Loja')
    assert 'não lido' in text and 'Não confirmado pela página' in text
    assert 'R$ 0' not in text and 'Disponível segundo a página' not in text
    assert all(field in text for field in ('condição', 'pagamento', 'vendedor', 'preço'))


def test_grouped_notices_keep_affected_stores_and_distinguish_timeout():
    notices = summarize_notices([
        'Amazon Brasil: modelo solicitado não encontrado nesta pesquisa.',
        'Pichau: modelo solicitado não encontrado nesta pesquisa.',
        'Terabyte: O limite da busca externa sem chave foi atingido.',
        'Terabyte: O limite da busca externa sem chave foi atingido.',
    ])
    assert len(notices) == 2
    assert 'Amazon Brasil, Pichau' in notices[0]
    assert notices[1] == 'Busca limitada: Terabyte.'
    assert short_reason('A loja não respondeu no tempo limite após três tentativas') == 'a loja demorou para responder'
    assert short_reason('Erro temporário de servidor') == 'loja temporariamente indisponível'
