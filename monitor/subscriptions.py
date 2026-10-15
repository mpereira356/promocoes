"""Escolha de abrangencia persistente para anuncios encontrados."""

import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .selection import authorized


def ad_fingerprint(ad):
    return hashlib.sha256(
        f"{ad['id']}\n{ad['url']}\n{ad['title']}\n{ad['title_key']}".encode()
    ).hexdigest()[:20]


async def ask_scope(bot, chat, db, ad_id):
    ad = db.get_ad(ad_id)
    if ad is None:
        await bot.send_message(
            chat,
            "Anuncio nao encontrado. Execute /buscar nome e use o ID exibido no resultado.",
        )
        return
    token = db.request_scope(ad_id)
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "So esta oferta neste site", callback_data=f"scope:{token}:site"
                )
            ],
            [
                InlineKeyboardButton(
                    "Outras lojas tambem", callback_data=f"scope:{token}:all"
                )
            ],
        ]
    )
    await bot.send_message(
        chat,
        f"Anuncio ID: {ad_id}\n{ad['title'][:500]}\n{ad['url']}\n"
        "Onde deseja acompanhar este produto?\n"
        "Avisarei aumentos e quedas, a cada 5 horas, sem prazo para encerrar.\n"
        "Outras lojas: somente o mesmo modelo; resultados ambiguos exigem confirmacao.\n"
        "Bloqueios das lojas e dados insuficientes podem impedir comparacoes.",
        reply_markup=markup,
    )


async def handle_subscription(update, config, db, bot, send, on_confirm):
    query = update.callback_query
    if not query:
        return
    if not authorized(update, config):
        await query.answer(
            "Somente o usuario autorizado pode escolher.", show_alert=True
        )
        return
    parts = (query.data or "").split(":")
    if len(parts) == 2 and parts[0] == "watch" and parts[1].isdigit():
        await query.answer()
        await ask_scope(bot, config.chat, db, int(parts[1]))
        return
    if len(parts) != 3 or parts[0] != "scope" or parts[2] not in ("site", "all"):
        await query.answer("Escolha invalida.", show_alert=True)
        return
    result = db.subscribe(parts[1], parts[2], config)
    if result is None or result[0] is None:
        await query.answer(
            "Escolha antiga ou monitoramento removido. Use /monitorar ID_DO_ANUNCIO.",
            show_alert=True,
        )
        return
    pid, created = result
    await query.answer(
        "Monitoramento ativado!" if created else "Este monitoramento ja existe."
    )
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    if not created:
        await send(
            f"Monitoramento {pid} ja cadastrado. Use /lista para consultar o status ou /retomar {pid} se estiver pausado."
        )
        return
    scope = (
        "somente esta oferta"
        if parts[2] == "site"
        else "mesmo modelo nas lojas autorizadas que permitirem acesso"
    )
    await send(
        f"✅ Monitoramento {pid} ativado: {scope}.\n"
        "🚨 Alertas de aumentos e quedas; verificacao a cada 5 horas, sem data de encerramento.\n"
        f"Controle com /pausar {pid}, /retomar {pid} e /historico {pid}.\n"
        "Registrando o preco inicial. Dados insuficientes suspendem os alertas, sem inventar valores."
    )
    on_confirm(pid)
