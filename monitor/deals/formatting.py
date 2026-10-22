from .adapters import CATEGORIES
from ..message_style import short_reason
from ..models import normalize


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
    title = report.category_title or ' > '.join(CATEGORIES.get(report.category, (report.category,)))
    failed = any(c.failed_pages for c in report.coverage)
    unread = not report.results and not any(c.priced for c in report.coverage)
    heading = ('Consulta encerrada sem ofertas verificadas' if unread else
               'Busca pontual concluída com limitações' if failed else 'Busca pontual concluída')
    prefix = '\u26a0\ufe0f ' if unread or failed else '\u2705 '
    label = ('Maior que ' + str(report.filter.value) + '%' if not report.filter.inclusive and not report.filter.less else str(report.filter))
    text = prefix + heading + ' \u2014 ' + title + '\nFiltro: ' + label + '\n'
    text += f'Ofertas válidas apresentadas: {len(report.results)}\n'
    if report.size or 'lacoste' in report.category:
        text += 'Tamanho: ' + (report.size or 'todos (sem filtro)') + '\n'
    if not report.results:
        text += ('Não foi possível confirmar preços nesta consulta.\n' if unread else
                 'Nenhuma oferta lida atendeu ao desconto, estoque e tamanho escolhidos.\n')
    text += '\nLojas consultadas (cobertura parcial):\n'
    for cov in report.coverage:
        text += (f'\u2022 {cov.store}: {cov.priced} oferta(s) com preço, {cov.qualifying} no filtro'
                 + (f', {cov.failed_pages} falha(s)' if cov.failed_pages else '') + '.\n')
        if cov.missing_reference:
            text += f'  Sem preço anterior verificável: {cov.missing_reference}.\n'
        if cov.unavailable:
            text += f'  Sem estoque confirmado: {cov.unavailable}.\n'
    text += '\nConsulta manual, sem acompanhamento automático. Frete não incluído.'
    yield text
    # One consolidated notice avoids a long burst of individual store messages.
    warnings = []
    for cov in report.coverage:
        ordered = sorted(cov.notices, key=lambda n: not any(word in normalize(n) for word in
                         ('bloque', 'captcha', 'falha', 'indisponivel', 'nao permite', 'sem links')))
        notices = list(dict.fromkeys(short_reason(n.removeprefix('\u26a0\ufe0f').strip()) for n in ordered))
        if notices:
            warnings.append(cov.store + ': ' + '; '.join(notices[:2]) + '.')
    if warnings:
        yield '\u26a0\ufe0f Avisos da pesquisa\n\n' + '\n\n'.join(warnings)
