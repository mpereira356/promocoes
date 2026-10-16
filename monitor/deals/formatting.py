from datetime import datetime
from zoneinfo import ZoneInfo
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
        if offer.model:
            text += f'Modelo declarado: {offer.model}\n'
        if r.identifiers:
            text += 'Identificadores:\n' + '\n'.join(f'{k.upper()}: {v}' for k, v in r.identifiers.items()) + '\n'
        text += f'Referência: {offer.reference_source or "preço anterior explícito da oferta"}.\n\n'
        if result.lowest:
            text += f'Menor preço comparável: {result.lowest.store}, {reais(result.lowest.reading.price)}.\n'
        text += 'Preços em outras lojas\n'
        if len(result.options) == 1:
            text += 'Ainda não há correspondências confirmadas nas mesmas condições.\n'
        else:
            text += '\n' + '\n'.join(f'{o.store}: {reais(o.reading.price)} ({o.reading.payment}); {o.url}' for o in result.options[1:]) + '\n'
        text += '\nCupom: ' + (offer.coupon or 'nenhum requisito confirmado; nenhum desconto adicional foi aplicado.') + '\n'
        text += 'Assinatura: ' + (offer.members or 'nenhum requisito identificado; confira as condições da loja.') + '\n'
        text += '🚚 Frete não incluído; ' + (f'não consultado para o CEP {report.cep}.' if report.cep else 'CEP não informado.') + '\n'
        if offer.suspicious:
            text += '⚠️ Preço de referência suspeito: desconto anunciado de 70% ou mais. Confira o valor diretamente na loja.\n'
        if offer.notes:
            text += '\n'.join(offer.notes) + '\n'
        text += f'\n🔗 Link: {offer.url}'
        yield text
    title = report.category_title or ' > '.join(CATEGORIES[report.category])
    text = f'✅ Busca pontual concluída — {title}\nFiltro: {report.filter}\nOfertas válidas apresentadas: {len(report.results)}\n\n'
    text += 'O desconto anunciado é calculado sobre a referência da própria loja; isso não comprova uma queda histórica. As comparações consideram o preço do produto, sem frete.\n\n'
    text += f'Consulta: {datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")}\n\nCobertura parcial — não representa o site inteiro:\n'
    for cov in report.coverage:
        text += (f'• {cov.store}: {cov.category_pages} página(s) de categoria tentada(s), '
                 f'{cov.product_pages} oferta(s) tentada(s), {cov.comparison_pages} oferta(s) complementares; '
                 f'{cov.discovery_pages} documento(s) de descoberta ({cov.discovery_loaded} lidos); '
                 f'{cov.discovered} links descobertos, {cov.excluded} produtos sem oferta apta.\n')
        if cov.notices:
            text += f'  ⚠️ {len(set(cov.notices))} aviso(s); detalhes nas mensagens por loja.\n'
    text += '\nA contagem considera páginas lógicas; não soma robots.txt, recursos do navegador, redirecionamentos ou novas tentativas. A descoberta pode usar cache ou índice externo; os preços são lidos na página da oferta. As comparações complementares são limitadas e não cobrem todos os anúncios.\n\n⏸️ Esta consulta não cadastra monitoramento nem alertas futuros.'
    yield text
    # Cada loja recebe seu bloco; send_text preserva as linhas ao dividir mensagens.
    for cov in report.coverage:
        notices = list(dict.fromkeys(n.removeprefix('⚠️').strip() for n in cov.notices))
        if notices:
            yield f'⚠️ Avisos da pesquisa — {cov.store}\n\n' + '\n\n'.join('⚠️ ' + n for n in notices)
