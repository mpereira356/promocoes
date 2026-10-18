"""Mensagens de oferta com foto e rotulos claros, sem inferir dados ausentes."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .models import normalize
from .telegram_text import render, send_text

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def rank_offers(offers):
    """Ranking visual da busca, sem alterar series ou regras de alerta."""
    groups, unranked = {}, []
    seen = set()
    for reading, url, store in offers:
        key = (reading.currency, normalize(reading.payment), reading.condition)
        identity = (url,) + key
        if identity in seen:
            continue
        seen.add(identity)
        if (
            not isinstance(reading.price, int)
            or isinstance(reading.price, bool)
            or reading.price <= 0
            or reading.currency != "BRL"
            or not reading.payment
            or reading.stock != "in_stock"
        ):
            unranked.append((reading, url, store, None, False))
        else:
            groups.setdefault(key, []).append((reading, url, store))
    result = []
    for items in groups.values():
        items.sort(key=lambda item: item[0].price)
        levels = {
            price: i + 1
            for i, price in enumerate(sorted({item[0].price for item in items}))
        }
        for reading, url, store in items:
            result.append(
                (
                    reading,
                    url,
                    store,
                    levels[reading.price],
                    not bool(reading.condition),
                )
            )
    return result + unranked


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
    if rank in MEDALS:
        parts.insert(0, f"{MEDALS[rank]} {rank}º menor preço desta busca")
        parts.insert(1, '⚠️ Ranking provisório; confira modelo e condição.' if provisional else
                     'Ranking da busca; confira o modelo.')
    if store:
        parts.append('🏪 ' + store[:80])
    payment = ' · ' + reading.payment[:80] if reading.payment else ''
    parts.append(f'💰 {price}{payment}')
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
    if reading.image:
        fits_caption = len(text.encode('utf-16-le')) // 2 <= 1024
        try:
            await bot.send_photo(
                chat, photo=reading.image,
                caption=render(text, (reading.title[:350],)) if fits_caption else render(reading.title[:200] + '\n📋 Os detalhes da oferta serão enviados na próxima mensagem.', (reading.title[:200],)),
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception:
            pass
        else:
            if fits_caption:
                return
    await send_text(lambda t, **kw: bot.send_message(chat, t, **kw), text + "\n" + url, bold_lines=(reading.title[:350],), reply_markup=keyboard)
