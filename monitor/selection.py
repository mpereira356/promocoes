"""Cartoes e confirmacao de ofertas no Telegram, testaveis sem rede."""

import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def identity(candidate):
    value = f"{candidate['product']}\n{candidate['url']}\n{candidate['title']}"
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def authorized(update, config):
    return bool(
        update.effective_user
        and update.effective_chat
        and update.effective_user.id == config.user
        and update.effective_chat.id == config.chat
    )


async def send_card(bot, chat, candidate):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Monitorar esta oferta",
                    callback_data=f"choose:{candidate['id']}:{identity(candidate)}",
                )
            ],
            [InlineKeyboardButton("Abrir na loja", url=candidate["url"])],
        ]
    )
    text = (
        f"🆔 ID do anúncio: {candidate['ad_id'] if 'ad_id' in candidate.keys() and candidate['ad_id'] else 'não atribuído'}\n\n"
        f"Qual destas ofertas corresponde ao produto que você procura?\n\n"
        f"📦 Produto {candidate['product']} · Oferta {candidate['id']}\n"
        f"{candidate['title'][:500]}\n🏪 Loja: {candidate['store'][:100]}\n\n"
        f"Confira o modelo, o Wi-Fi e a versão antes de escolher.\n"
        f"A foto é ilustrativa da página; não comprova o modelo nem o estoque.\n"
        f"Você pode escolher mais de uma oferta.\n\n"
        f"Alternativa: /confirmar {candidate['id']}"
    )
    if candidate["image"]:
        try:
            await bot.send_photo(
                chat, photo=candidate["image"], caption=text, reply_markup=keyboard
            )
            return
        except Exception:
            # Imagem bloqueada, invalida ou grande: manter a escolha por texto.
            pass
    await bot.send_message(chat, text + "\n📷 Foto indisponível; você ainda pode escolher pelos botões acima.", reply_markup=keyboard)


async def handle_choice(update, config, db, send, on_confirm=None):
    query = update.callback_query
    if not query:
        return
    if not authorized(update, config):
        await query.answer(
            'Somente o usuário autorizado pode fazer essa escolha.', show_alert=True
        )
        return
    parts = (query.data or "").split(":")
    if len(parts) != 3 or parts[0] != "choose" or not parts[1].isdigit():
        await query.answer("Essa escolha não é válida. Atualize as opções com /opcoes PRODUTO_ID.", show_alert=True)
        return
    candidate = db.confirm_candidate(int(parts[1]), parts[2])
    if candidate is None:
        await query.answer(
            'Esta oferta foi removida ou alterada. Use /opcoes PRODUTO_ID para ver as opções atuais.', show_alert=True
        )
        return
    if candidate["confirmed"]:
        await query.answer('Esta oferta já foi selecionada.')
        return
    await query.answer('✅ Oferta selecionada.')
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await send(
        f"✅ Oferta {candidate['id']} selecionada\n{candidate['title']}\n\n"
        f"Produto {candidate['product']}. Somente ofertas confirmadas entram nas comparações.\n"
        f"Consultando a oferta para registrar o preço inicial, se houver dados suficientes."
    )
    if on_confirm:
        on_confirm(candidate["product"])
