from .adapters import CATEGORIES
from ..message_style import short_reason


def reais(cents):
    return 'R$ ' + f'{cents / 100:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def messages(report):
    for result in report.results:
        offer, r = result.offer, result.offer.reading
        condition = {'NewCondition': 'Novo', 'UsedCondition': 'Usado',
                     'RefurbishedCondition': 'Recondicionado', 'DamagedCondition': 'Danificado'}.get(r.condition, 'não declarada')
        comparison = result.comparison
        if comparison.casefold().startswith('comparação '):
            comparison = comparison[len('Comparação '):]
        text = (f'🏆 {r.title}\n\n🏪 Loja: {offer.store}\n'
                f'De: {reais(offer.previous)}\nPor: {reais(r.price)}\n'
                f'📣 Desconto anunciado: {offer.percent:.2f}%\n'
                f'💳 Pagamento: {r.payment or "não declarado para este preço"}\n'
                f'👤 Vendedor: {r.seller or "não declarado"}\n'
                f'📦 Condição: {condition}\n'
                f'📊 Estoque: disponível segundo a página\n🔎 Comparação: {comparison}.\n\n')
        if result.lowest:
            text += f'Menor preço comparável: {result.lowest.store}, {reais(result.lowest.reading.price)}.\n'
        if len(result.options) > 1:
            text += 'Preços em outras lojas\n' + '\n'.join(f'{o.store}: {reais(o.reading.price)} ({o.reading.payment})\n{o.url}' for o in result.options[1:]) + '\n'
        if offer.coupon: text += '\nCupom: ' + offer.coupon + '\n'
        if offer.members: text += 'Assinatura necessária: ' + offer.members + '\n'
        text += '🚚 Frete não incluído.' + (f' CEP {report.cep} não cotado.' if report.cep else '') + '\n'
        if offer.suspicious:
            text += '⚠️ Preço de referência suspeito: desconto anunciado de 70% ou mais. Confira o valor diretamente na loja.\n'
        if offer.notes:
            text += '\n'.join(offer.notes) + '\n'
        text += f'\nDesconto da loja; queda histórica não comprovada.\n🔗 {offer.url}'
        yield text
    title = report.category_title or ' > '.join(CATEGORIES[report.category])
    text = f'✅ Busca pontual concluída — {title}\nFiltro: {report.filter}\nOfertas válidas apresentadas: {len(report.results)}\n\n'
    text += 'Cobertura parcial — não representa o site inteiro:\n'
    for cov in report.coverage:
        text += (f'• {cov.store}: {cov.category_pages} página(s) de categoria tentada(s), '
                 f'{cov.product_pages + cov.comparison_pages} oferta(s) tentada(s), '
                 f'{cov.discovery_loaded} documento(s) de descoberta lido(s).\n')
        if cov.notices:
            text += '  ⚠️ Consulta com limitações.\n'
    text += '\nConsulta manual, sem acompanhamento automático.'
    yield text
    # Cada loja recebe seu bloco; send_text preserva as linhas ao dividir mensagens.
    for cov in report.coverage:
        notices = list(dict.fromkeys(short_reason(n.removeprefix('⚠️').strip()) for n in cov.notices))
        if notices:
            yield f'⚠️ Avisos da pesquisa — {cov.store}\n\n' + '\n\n'.join('⚠️ ' + n for n in notices)
