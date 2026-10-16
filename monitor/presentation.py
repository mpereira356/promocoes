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
        parts.insert(
            0,
            f"{MEDALS[rank]} {rank}º menor preço desta busca — {reading.payment[:100]}",
        )
        parts.insert(
            1,
            (
                "⚠️ Ranking provisório: condição não declarada."
                if provisional
                else "Ranking entre ofertas com a mesma condição e forma de pagamento."
            ),
        )
        parts.insert(
            2, "🔎 Os modelos desta busca podem ser diferentes. Confira se a oferta corresponde ao produto desejado.\n"
        )
    if store:
        parts.append("🏪 Loja: " + store[:80])
    if reading.identifiers.get('generation'):
        parts.append('📌 Geração na ficha técnica: ' + reading.identifiers['generation'])
    parts += [
        ('💰 Preço da oferta principal: não divulgado' if reading.price is None and reading.starting_price is not None else f"💰 Preço: {price}"),
        f'💳 Pagamento: {reading.payment[:100] or "❓ Não declarado para este preço"}',
        f'👤 Vendedor: {reading.seller[:100] or "❓ Não declarado pela página"}',
        f"📦 Condição: {condition}",
        f"📊 Estoque: {stock}",
        "🚚 Frete não incluído.",
        '',
    ]
    if reading.starting_price is not None and reading.price is None:
        amount = 'R$ ' + f'{reading.starting_price // 100:,}'.replace(',', '.') + f',{reading.starting_price % 100:02d}'
        parts += [
            '\U0001f4b0 Outras ofertas a partir de: ' + amount,
            'Valor publicado na p\u00e1gina para outras ofertas; vendedor, pagamento e estoque dessa op\u00e7\u00e3o n\u00e3o confirmados.',
            'O vendedor acima, quando exibido, pertence \u00e0 oferta principal, cujo pre\u00e7o n\u00e3o foi divulgado.',
            'Essa refer\u00eancia n\u00e3o entra no ranking, no hist\u00f3rico de pre\u00e7os v\u00e1lidos ou nos alertas.',
            '\U0001f517 Consultar outras ofertas: ' + reading.starting_price_url, '',
        ]
    if not reading.comparable:
        missing = []
        if not reading.condition:
            missing.append("condição")
        if not reading.payment:
            missing.append("pagamento")
        if not reading.seller:
            missing.append("vendedor")
        if reading.price is None:
            missing.append("preço")
        if reading.currency != "BRL":
            missing.append("moeda BRL")
        parts.append(
            "⏸️ Alertas de preço suspensos: faltam dados confirmados — " + ", ".join(missing) + "."
        )
    parts.append("🔎 Confira o modelo exato antes de monitorar.")
    if ad_id is not None:
        parts.append(f"\n🆔 ID do anúncio: {ad_id}")
        parts.append(f"🔔 Monitorar: /monitorar {ad_id}")
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
