from .adapters import CATEGORIES


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
    title = ' > '.join(title.split(' > ')[-2:])
    result_domains = {result.offer.domain for result in report.results}
    checked = [c.store for c in report.coverage if c.priced or c.domain in result_domains]
    unavailable = [c.store for c in report.coverage if not c.priced and c.domain not in result_domains]
    partial = [c.store for c in report.coverage if c.store in checked and c.failed_pages]
    text = '🏁 Pesquisa finalizada\n\n' + title + '\n'
    label = ('Maior que ' + str(report.filter.value) + '%' if not report.filter.inclusive and not report.filter.less else str(report.filter))
    text += 'Desconto: ' + label + '\n'
    if report.size or 'lacoste' in report.category:
        text += 'Tamanho: ' + (report.size or 'todos (sem filtro)') + '\n'
    if report.results:
        text += f'\nPromoções encontradas: {len(report.results)}.\n'
    elif checked:
        threshold = ('mais de ' + str(report.filter.value) + '%' if not report.filter.inclusive and not report.filter.less else str(report.filter))
        text += '\nNão encontrei promoções com ' + threshold + ' de desconto'
        text += (' no tamanho ' + report.size if report.size else '') + ' nas ofertas verificadas.\n'
    else:
        text += '\nNão consegui verificar ofertas nesta tentativa.\n'
    if checked:
        text += '\nPreços verificados em: ' + ', '.join(checked) + '.\n'
    if unavailable:
        text += '\nNão consegui verificar: ' + ', '.join(unavailable) + '.\n'
    if partial:
        text += 'Consulta incompleta em: ' + ', '.join(partial) + '.\n'
    if unavailable or partial:
        text += 'Pode haver promoções nas lojas que não consegui consultar por completo.\n'
    text += '\n' + ('Tente um desconto menor ou pesquise novamente.' if checked and not report.results else
                    'Tente novamente mais tarde.' if not checked and not report.results else
                    'Os resultados são das ofertas verificadas nesta consulta.')
    yield text
