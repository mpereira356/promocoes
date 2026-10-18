"""HTML restrito gerado a partir de texto simples, com conteudo dinamico escapado."""
from html import escape
import asyncio
from datetime import timedelta
from telegram.error import RetryAfter

HEADINGS = {
    'BUSCAS', 'MONITORAMENTO', 'Exemplo de filtros', 'Exemplos de uso',
    'Observações', 'Preços em outras lojas',
    'Cobertura parcial — não representa o site inteiro:',
}
PREFIXES = (
    '⏳ Seu pedido entrou na fila',
    '💸 ', '✅ Empréstimos pagos',
    '🛍️ Bot de ofertas', 'ℹ️ Status do bot', '🏆 ', '🥇 ', '🥈 ', '🥉 ',
    '🔔 Monitoramento ', '✅ Monitoramento ', '✅ Oferta ', '✅ Modelo confirmado',
    '✅ Pesquisa concluída', '✅ Busca pontual concluída', '⚠️ Pesquisa encerrada',
    '⚠️ Pesquisa concluída',
    '⚠️ Avisos da pesquisa', '🏷️ Busca pontual de promoções', '🏷️ Oferta ',
    '📉 QUEDA DE PREÇO', '📈 AUMENTO DE PREÇO', '📊 Oferta ',
    'Hardware · escolha a subcategoria:', '🏷️ ', '✅ Catálogo atualizado',
    '🔎 ', '🆔 ID do anúncio:', '🆔 Anúncio ', '🆔 Anúncio:', '📦 Produto ', '🛍️ Central de ofertas',
    '🔔 Meus monitoramentos', '⚙️ ', '✅ Conferir filtros', '🗑️ Remover monitoramento',
)


def render(text, bold_lines=()):
    titles = set(bold_lines)
    lines = []
    for line in text.split('\n'):
        safe = escape(line)
        if line and (line in HEADINGS or line in titles or line.startswith(PREFIXES) or ' · escolha a subcategoria' in line):
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
        for attempt in range(3):
            try:
                await send(render(part, bold_lines), parse_mode='HTML', **kwargs)
                break
            except RetryAfter as exc:
                delay = exc.retry_after
                delay = delay.total_seconds() if isinstance(delay, timedelta) else delay
                if attempt == 2 or delay > 60:
                    raise
                # Reenvia apenas o trecho recusado, nunca resultados já entregues.
                await asyncio.sleep(delay + 0.2)
