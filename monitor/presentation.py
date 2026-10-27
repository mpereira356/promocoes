"""Mensagens de oferta com foto e rotulos claros, sem inferir dados ausentes."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .models import normalize
from .telegram_text import render, send_text
import json

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def rank_offers(offers):
    """Ranking visual da busca, sem alterar series ou regras de alerta."""
    from urllib.parse import urlsplit, parse_qs
    import re
    selected = {}
    def valid(reading):
        return (type(reading.price) is int and reading.price > 0 and reading.currency == 'BRL'
                and bool(reading.payment) and reading.stock == 'in_stock')
    def priority(reading):
        return (valid(reading), type(reading.price) is int and reading.price > 0,
                reading.stock == 'in_stock', -(reading.price or 0), reading.payment == 'Pix')
    for reading, url, store in offers:
        path = urlsplit(url)
        host = (path.hostname or '').removeprefix('www.')
        asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', path.path) if host == 'amazon.com.br' else None
        merchant = tuple((key, tuple(values)) for key, values in sorted(parse_qs(path.query).items()) if key in ('smid', 'm', 'seller'))
        product = (host, asin[1], merchant) if asin else url
        identity = (product, reading.seller, reading.condition, reading.currency,
                    json.dumps(reading.identifiers, sort_keys=True))
        previous = selected.get(identity)
        # Select a real payment reading; never invent a combined payment method.
        if previous is None or priority(reading) > priority(previous[0]):
            selected[identity] = (reading, url, store)
    ranked = sorted((item for item in selected.values() if valid(item[0])), key=lambda item: item[0].price)
    result = [(reading, url, store, index, not bool(reading.condition))
              for index, (reading, url, store) in enumerate(ranked, 1)]
    return result + [(r, url, store, None, False) for r, url, store in selected.values() if not valid(r)]


def offer_text(reading, store="", rank=None, provisional=False, ad_id=None):
    price = (
        'R$ ' + f'{reading.price // 100:,}'.replace(',', '.') + f',{reading.price % 100:02d}'
        if reading.price is not None else 'não lido'
    )
    stock = {
        "in_stock": "✅ Disponível segundo a página",
        "out_of_stock": "❌ INDISPONÍVEL",
        "unknown": "❓ Não confirmado pela página",
    }.get(reading.stock, "❓ Não confirmado pela página")
    condition = {
        "NewCondition": "🆕 Novo",
        "UsedCondition": "⚠️ USADO",
        "RefurbishedCondition": "⚠️ RECONDICIONADO",
        "DamagedCondition": "⚠️ DANIFICADO",
    }.get(reading.condition, "❓ Não declarada pela página")
    parts = [reading.title[:350], '']
    if reading.public_unit_price:
        condition = reading.condition
    if rank in MEDALS:
        parts.insert(0, f"{MEDALS[rank]} {rank}º na lista por preço")
        parts.insert(1, '⚠️ Condição não informada; confira na loja.' if provisional else
                     'Confira pagamento e condição antes de comprar.')
    if store:
        parts.append('🏪 ' + store[:80])
    payment = ' · ' + reading.payment[:80] if reading.payment else ''
    parts.append(f'💰 {price}{payment}')
    if reading.identifiers.get('price_basis') == 'regional_public_unit':
        parts += ['Preço público por kg; o total da peça depende da pesagem.',
                  'Pagamento não confirmado. Alertas acompanham esse preço público, sem comprovar promoção.']
    if reading.seller and normalize(reading.seller) != normalize(store):
        parts.append('Vendedor: ' + reading.seller[:100])
    if reading.condition:
        parts.append('📦 ' + condition)
    parts.append(stock)
    if reading.identifiers.get('generation'):
        parts.append('Modelo: ' + reading.identifiers['generation'])
    parts.append('🚚 Frete não incluído.')
    if reading.starting_price is not None and reading.price is None:
        amount = 'R$ ' + f'{reading.starting_price // 100:,}'.replace(',', '.') + f',{reading.starting_price % 100:02d}'
        parts += ['Outras ofertas a partir de: ' + amount,
                  'Referência: vendedor, pagamento e estoque não confirmados; sem alertas.',
                  reading.starting_price_url]
    if not reading.comparable:
        missing = []
        if not reading.condition: missing.append('condição')
        if not reading.payment: missing.append('pagamento')
        if not reading.seller: missing.append('vendedor')
        if reading.price is None: missing.append('preço')
        if reading.currency != 'BRL': missing.append('moeda BRL')
        parts.append('\n⏸️ Alertas suspensos: dados pendentes — ' + ', '.join(missing) + '.')
    if ad_id is not None:
        parts.append(f'\n🆔 Anúncio {ad_id} · /monitorar {ad_id}')
    return "\n".join(parts)


async def send_offer(
    bot, chat, reading, url, store="", rank=None, provisional=False, ad_id=None
):
    text = offer_text(reading, store, rank, provisional, ad_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Abrir oferta", url=url)]])
    if ad_id is not None:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"🔔 Monitorar anúncio {ad_id}", callback_data=f"watch:{ad_id}"
                    )
                ],
                [InlineKeyboardButton("🔗 Abrir oferta", url=url)],
            ]
        )
    keyboard = InlineKeyboardMarkup(list(keyboard.inline_keyboard) + [[InlineKeyboardButton('🏠 Menu principal',callback_data='ui:home')]])
    if reading.image and len(text.encode('utf-16-le')) // 2 <= 1024:
        from telegram.error import BadRequest, RetryAfter
        import asyncio
        from datetime import timedelta
        try:
            for attempt in range(3):
                try:
                    await bot.send_photo(chat, photo=reading.image,
                                         caption=render(text, (reading.title[:350],)),
                                         parse_mode='HTML', reply_markup=keyboard)
                    break
                except RetryAfter as exc:
                    delay = exc.retry_after.total_seconds() if isinstance(exc.retry_after, timedelta) else exc.retry_after
                    if attempt == 2 or delay > 60:
                        raise
                    await asyncio.sleep(delay + 0.2)
        except BadRequest:
            # The server explicitly rejected the photo: one text fallback is safe.
            pass
        else:
            return
    # A timeout is ambiguous and propagates instead of sending a duplicate card.
    await send_text(lambda t, **kw: bot.send_message(chat, t, **kw), text + "\n" + url, bold_lines=(reading.title[:350],), reply_markup=keyboard)
