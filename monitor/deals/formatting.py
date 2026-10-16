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
        text = (f'🏆 {r.title}\nLoja: {offer.store}\n'
                f'De: {reais(offer.previous)}\nPor: {reais(r.price)}\n'
                f'Desconto anunciado: {offer.percent:.2f}%\n'
                f'Pagamento: {r.payment or "não declarado para este preço"}\n'
                f'Vendedor: {r.seller or "não declarado"}\n'
                f'Condição: {condition}\n'
                f'Estoque: disponível segundo a página\nComparação: {result.comparison}.\n')
        if offer.model:
            text += f'Modelo declarado: {offer.model}\n'
        if r.identifiers:
            text += 'Identificadores: ' + '; '.join(f'{k.upper()}: {v}' for k, v in r.identifiers.items()) + '\n'
        text += f'Referência: {offer.reference_source or "preço anterior explícito da oferta"}.\n'
        if result.lowest:
            text += f'Menor preço comparável: {result.lowest.store}, {reais(result.lowest.reading.price)}.\n'
        text += 'Preços em outras lojas: '
        if len(result.options) == 1:
            text += 'nenhuma correspondência confirmada nas mesmas condições.\n'
        else:
            text += '\n' + '\n'.join(f'{o.store}: {reais(o.reading.price)} ({o.reading.payment}); {o.url}' for o in result.options[1:]) + '\n'
        text += 'Cupom: ' + (offer.coupon or 'nenhum requisito confirmado; não foi aplicado desconto adicional') + '\n'
        text += 'Assinatura: ' + (offer.members or 'nenhum requisito identificado; confira condições da loja') + '\n'
        text += 'Frete: não incluído; ' + (f'não consultado para o CEP {report.cep}.' if report.cep else 'CEP não informado.') + '\n'
        if offer.suspicious:
            text += '⚠️ Preço de referência suspeito: desconto de 70% ou mais; confira na loja.\n'
        if offer.notes:
            text += '\n'.join(offer.notes) + '\n'
        text += f'Link: {offer.url}'
        yield text
    title = ' > '.join(CATEGORIES[report.category])
    text = f'✅ Pesquisa concluída — {title}; filtro {report.filter}. Ofertas válidas apresentadas: {len(report.results)}.\n'
    text += 'Desconto anunciado calculado sobre a referência da própria loja; não comprova queda histórica. Comparações usam o preço do produto, sem frete.\n'
    text += f'Consulta: {datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")}\nCobertura parcial (não é o site inteiro):\n'
    for cov in report.coverage:
        text += (f'• {cov.store}: {cov.category_pages} página(s) de categoria tentada(s), '
                 f'{cov.product_pages} oferta(s) tentada(s), {cov.comparison_pages} oferta(s) complementares; '
                 f'{cov.discovery_pages} documento(s) de descoberta complementar ({cov.discovery_loaded} lidos); '
                 f'{cov.discovered} links descobertos, {cov.excluded} produtos sem oferta apta.\n')
        if cov.notices:
            text += '\n'.join('  ⚠️ ' + n for n in dict.fromkeys(cov.notices)) + '\n'
    text += 'Contagem por página lógica, sem somar robots.txt, recursos do navegador, redirecionamentos ou retentativas. Descoberta pode usar cache ou índice externo; preços são lidos na oferta. Comparação complementar limitada; não cobre todos os anúncios. Nenhum acompanhamento ou alerta futuro foi cadastrado.'
    yield text
