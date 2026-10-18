"""Cartoes e confirmacao de ofertas no Telegram, testaveis sem rede."""

import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .telegram_text import render, send_text


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
                    "✅ Confirmar e acompanhar",
                    callback_data=f"choose:{candidate['id']}:{identity(candidate)}",
                )
            ],
            [InlineKeyboardButton("Abrir na loja", url=candidate["url"])],
            [InlineKeyboardButton('🏠 Menu principal', callback_data='ui:home')],
        ]
    )
    candidate = dict(candidate)
    requested = candidate.get('notification_context') == 'requested'
    heading = '📋 Oferta aguardando confirmação' if requested else '🔎 Nova oferta no seu monitoramento'
    reason = ('Você solicitou as ofertas pendentes.' if requested else
              'Encontrada durante a verificação do seu monitoramento.')
    query = candidate.get('monitor_query', '')
    context = f"Você acompanha: {query[:120]}\n" if query else ''
    title = candidate['title'][:500]
    from .models import normalize
    box = normalize(candidate['title'])
    condition = '\n⚠️ Open Box: confira a condição na loja.\n' if 'open box' in box or 'openbox' in box else ''
    text = (
        f"{heading}\n\n{reason}\n"
        f"Aguarda confirmação; sem mudança de preço confirmada.\n\n"
        f"🔔 Monitoramento {candidate['product']}\n{context}\n"
        f"{title}\n🏪 Loja: {candidate['store'][:60]}\n"
        f"🆔 Anúncio: {candidate.get('ad_id') or 'não atribuído'} · Oferta: {candidate['id']}\n"
        f"{condition}\nÉ o modelo e a condição que você deseja?\n"
        f"Confirme para acompanhar ou ignore a sugestão.\n\n"
        f"✅ Confirmar: /confirmar {candidate['id']}"
    )
    photo_failed = not candidate['image']
    if candidate["image"] and len(text.encode('utf-16-le')) // 2 <= 1024:
        try:
            await bot.send_photo(
                chat, photo=candidate["image"], caption=render(text, (heading,title)), reply_markup=keyboard, parse_mode='HTML'
            )
            return
        except Exception:
            # Imagem bloqueada, invalida ou grande: manter a escolha por texto.
            photo_failed = True
    note = "\n📷 Foto indisponível." if photo_failed else ''
    await send_text(lambda t, **kw: bot.send_message(chat, t, **kw), text + note, bold_lines=(heading,title), reply_markup=keyboard)


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
