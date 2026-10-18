"""Escolha de abrangencia persistente para anuncios encontrados."""

import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .selection import authorized
from .telegram_text import send_text


def ad_fingerprint(ad):
    return hashlib.sha256(
        f"{ad['id']}\n{ad['url']}\n{ad['title']}\n{ad['title_key']}".encode()
    ).hexdigest()[:20]


async def ask_scope(bot, chat, db, ad_id):
    ad = db.get_ad(ad_id)
    if ad is None:
        await send_text(
            lambda text, **kwargs: bot.send_message(chat, text, **kwargs),
            'Não encontramos esse anúncio. Execute /buscar nome e use o ID exibido no resultado.',
        )
        return
    token = db.request_scope(ad_id)
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    'Só esta oferta neste site', callback_data=f"scope:{token}:site"
                )
            ],
            [
                InlineKeyboardButton(
                    'Outras lojas também', callback_data=f"scope:{token}:all"
                )
            ],
            [InlineKeyboardButton('🏠 Menu principal',callback_data='ui:home')],
        ]
    )
    await send_text(
        lambda text, **kwargs: bot.send_message(chat, text, **kwargs),
        f"🆔 ID do anúncio: {ad_id}\n{ad['title'][:500]}\n{ad['url']}\n"
        "Onde deseja acompanhar este produto?\n\n"
        "🔎 Verificarei o preço a cada 5 horas, sem data para encerrar. Avisarei quando houver uma mudança comparável.\n"
        "• Em outras lojas, a comparação considera somente o mesmo modelo; resultados ambíguos exigem confirmação.\n"
        "• Bloqueios das lojas ou dados insuficientes podem impedir comparações.",
        reply_markup=markup, bold_lines=(ad['title'][:500],),
    )


async def handle_subscription(update, config, db, bot, send, on_confirm):
    query = update.callback_query
    if not query:
        return
    if not authorized(update, config):
        await query.answer(
            'Somente o usuário autorizado pode fazer essa escolha.', show_alert=True
        )
        return
    parts = (query.data or "").split(":")
    if len(parts) == 2 and parts[0] == "watch" and parts[1].isdigit():
        await query.answer()
        await ask_scope(bot, config.chat, db, int(parts[1]))
        return
    if len(parts) != 3 or parts[0] != "scope" or parts[2] not in ("site", "all"):
        await query.answer("Essa escolha não é válida. Inicie novamente com /monitorar ID_DO_ANUNCIO.", show_alert=True)
        return
    result = db.subscribe(parts[1], parts[2], config)
    if result is None or result[0] is None:
        await query.answer(
            'Esta escolha expirou ou o monitoramento foi removido. Use /monitorar ID_DO_ANUNCIO para começar novamente.',
            show_alert=True,
        )
        return
    pid, created = result
    await query.answer(
        '✅ Monitoramento ativado!' if created else 'Este monitoramento já existe.'
    )
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    if not created:
        await send(
            f"O monitoramento {pid} já está cadastrado. Use /lista para consultar o status ou /retomar {pid} se estiver pausado."
        )
        return
    scope = (
        "somente esta oferta"
        if parts[2] == "site"
        else "mesmo modelo nas lojas autorizadas que permitirem acesso"
    )
    await send(
        f"✅ Monitoramento {pid} ativado\nAbrangência: {scope}.\n\n"
        "🚨 Alertas de aumentos e quedas. Consultas a cada 5 horas, sem data de encerramento.\n"
        f"Controle: /pausar {pid} · /retomar {pid} · /historico {pid}\n\n"
        "Registrando o preço inicial. Se os dados forem insuficientes, os alertas ficam suspensos; nenhum valor será inventado."
    )
    on_confirm(pid)
