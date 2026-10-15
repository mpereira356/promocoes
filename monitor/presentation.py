"""Mensagens de oferta com foto e rotulos claros, sem inferir dados ausentes."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .models import normalize

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
    price = f"R$ {reading.price/100:.2f}" if reading.price is not None else "nao lido"
    stock = {
        "in_stock": "Disponivel segundo a pagina",
        "out_of_stock": "Indisponivel",
        "unknown": "Nao confirmado pela pagina",
    }.get(reading.stock, "Nao confirmado pela pagina")
    condition = {
        "NewCondition": "Novo",
        "UsedCondition": "Usado",
        "RefurbishedCondition": "Recondicionado",
        "DamagedCondition": "Danificado",
    }.get(reading.condition, "Nao declarada pela pagina")
    parts = [reading.title[:350]]
    if rank in MEDALS:
        parts.insert(
            0,
            f"{MEDALS[rank]} {rank}º menor valor desta busca — {reading.payment[:100]}",
        )
        parts.insert(
            1,
            (
                "Ranking provisorio: condicao nao declarada."
                if provisional
                else "Ranking entre ofertas da mesma condicao e pagamento."
            ),
        )
        parts.insert(
            2, "Os modelos desta busca podem ser diferentes; confira o produto."
        )
    if store:
        parts.append("Loja: " + store[:80])
    parts += [
        f"Preco: {price}",
        f'Pagamento: {reading.payment[:100] or "Nao declarado para este preco"}',
        f'Vendedor: {reading.seller[:100] or "Nao declarado pela pagina"}',
        f"Condicao: {condition}",
        f"Estoque: {stock}",
        "Frete nao incluido.",
    ]
    if not reading.comparable:
        missing = []
        if not reading.condition:
            missing.append("condicao")
        if not reading.payment:
            missing.append("pagamento")
        if not reading.seller:
            missing.append("vendedor")
        if reading.price is None:
            missing.append("preco")
        if reading.currency != "BRL":
            missing.append("moeda BRL")
        parts.append(
            "Alertas de preco suspensos: falta confirmar " + ", ".join(missing) + "."
        )
    parts.append("Confira o modelo exato antes de monitorar.")
    if ad_id is not None:
        parts.insert(0, f"Anuncio ID: {ad_id}")
        parts.append(f"Monitorar: /monitorar {ad_id}")
    return "\n".join(parts)


async def send_offer(
    bot, chat, reading, url, store="", rank=None, provisional=False, ad_id=None
):
    text = offer_text(reading, store, rank, provisional, ad_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Abrir oferta", url=url)]])
    if ad_id is not None:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"Monitorar anuncio {ad_id}", callback_data=f"watch:{ad_id}"
                    )
                ],
                [InlineKeyboardButton("Abrir oferta", url=url)],
            ]
        )
    if reading.image:
        try:
            await bot.send_photo(
                chat, photo=reading.image, caption=text[:1024], reply_markup=keyboard
            )
            return
        except Exception:
            pass
    await bot.send_message(chat, text + "\n" + url, reply_markup=keyboard)
