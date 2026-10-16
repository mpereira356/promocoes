"""HTML restrito gerado a partir de texto simples, com conteudo dinamico escapado."""
from html import escape

HEADINGS = {
    'BUSCAS', 'MONITORAMENTO', 'Exemplo de filtros', 'Exemplos de uso',
    'Observações', 'Preços em outras lojas',
    'Cobertura parcial — não representa o site inteiro:',
}
PREFIXES = (
    '🛍️ Bot de ofertas', 'ℹ️ Status do bot', '🏆 ', '🥇 ', '🥈 ', '🥉 ',
    '🔔 Monitoramento ', '✅ Monitoramento ', '✅ Oferta ', '✅ Modelo confirmado',
    '✅ Pesquisa concluída', '✅ Busca pontual concluída', '⚠️ Pesquisa encerrada',
    '⚠️ Avisos da pesquisa', '🏷️ Busca pontual de promoções', '🏷️ Oferta ',
    '📉 QUEDA DE PREÇO', '📈 AUMENTO DE PREÇO', '📊 Oferta ',
    'Hardware · escolha a subcategoria:',
    '🔎 ', '🆔 ID do anúncio:', '🆔 Anúncio:', '📦 Produto ',
)


def render(text, bold_lines=()):
    titles = set(bold_lines)
    lines = []
    for line in text.split('\n'):
        safe = escape(line)
        if line and (line in HEADINGS or line in titles or line.startswith(PREFIXES)):
            safe = '<b>' + safe + '</b>'
        lines.append(safe)
    return '\n'.join(lines)


def parts(text, limit=3800):
    """Limita texto visivel em UTF-16; entidades e tags so sao criadas depois."""
    buffer, size = '', 0
    for line in text.splitlines(keepends=True):
        units = len(line.encode('utf-16-le')) // 2
        if size + units > limit and buffer:
            yield buffer
            buffer, size = '', 0
        for char in line:
            units = len(char.encode('utf-16-le')) // 2
            if size + units > limit:
                yield buffer
                buffer, size = '', 0
            buffer += char
            size += units
    if buffer:
        yield buffer


async def send_text(send, text, bold_lines=(), **kwargs):
    for part in parts(text):
        await send(render(part, bold_lines), parse_mode='HTML', **kwargs)
