from monitor.deals.formatting import messages
from monitor.deals.models import Coverage, DealReport, DiscountFilter
from monitor.telegram_text import render


def test_users_am5_example_is_one_clear_final_message():
    report = DealReport([], [
        Coverage('amazon.com.br', 'Amazon Brasil', notices=['Página sem links reconhecidos']),
        Coverage('kabum.com.br', 'KaBuM', priced=1),
        Coverage('mercadolivre.com.br', 'Mercado Livre', failed_pages=1),
        Coverage('pichau.com.br', 'Pichau', failed_pages=1),
        Coverage('terabyteshop.com.br', 'Terabyte', priced=23, missing_reference=1,
                 notices=['Leitura limitada a 12 de 152 produtos encontrados']),
    ], DiscountFilter.parse('>40'), 'hardware/placas-mae/am5-amd-ryzen',
        category_title='Hardware > Placas Mae > AM5 - AMD Ryzen')
    output = list(messages(report))
    assert len(output) == 1
    text = output[0]
    assert text.startswith('🏁 Pesquisa finalizada\n')
    assert 'Maior que 40%' in text
    assert 'Não encontrei promoções' in text
    assert 'Preços verificados em: KaBuM, Terabyte.' in text
    assert 'Não consegui verificar: Amazon Brasil, Mercado Livre, Pichau.' in text
    assert 'Pode haver promoções' in text
    assert 'Tente um desconto menor' in text
    assert len(text) < 650
    assert all(term not in text for term in ('152', '23', 'sitemap', 'categoria geral', 'Avisos da pesquisa', 'preço anterior verificável'))
    assert render(text).startswith('<b>🏁 Pesquisa finalizada</b>')


def test_no_access_does_not_mean_no_discounts_exist():
    report = DealReport([], [Coverage('pichau.com.br', 'Pichau', failed_pages=1)],
                        DiscountFilter.parse('>40'), 'hardware/placas-mae')
    text = list(messages(report))[0]
    assert 'Pesquisa finalizada' in text
    assert 'Não consegui verificar ofertas' in text
    assert 'Não encontrei promoções' not in text
    assert 'desconto menor' not in text


def test_partially_read_store_is_clearly_distinguished():
    report = DealReport([], [Coverage('kabum.com.br', 'KaBuM', priced=1, failed_pages=1)],
                        DiscountFilter.parse('>40'), 'hardware/placas-mae')
    text = list(messages(report))[0]
    assert 'Preços verificados em: KaBuM.' in text
    assert 'Consulta incompleta em: KaBuM.' in text
    assert 'Não consegui verificar: KaBuM' not in text
