"""Delivery region persists locally, never in source control or public fixtures."""
import re


def postal_code(value):
    value = value.strip().replace('-', '')
    if not re.fullmatch(r'[0-9]{8}', value):
        raise ValueError('Informe oito números: /cep 01001000.')
    return value


def load_profile(db, config):
    rows = db.rows("SELECT value FROM preferences WHERE key='grocery_postal_code'")
    if rows:
        config.grocery_postal_code = postal_code(rows[0]['value'])
    rows = db.rows("SELECT value FROM preferences WHERE key='grocery_mode'")
    if rows and rows[0]['value'] in ('visit', 'delivery'):
        config.grocery_mode = rows[0]['value']


def save_profile(db, config, value):
    value = postal_code(value)
    db.run("INSERT INTO preferences(key,value) VALUES ('grocery_postal_code',?) "
           "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (value,))
    config.grocery_postal_code = value
    return value[:5] + '-' + value[5:]


def save_mode(db, config, mode):
    if mode not in ('visit', 'delivery'):
        raise ValueError('Escolha Posso ir à loja ou Preciso de entrega em /mercados.')
    db.run("INSERT INTO preferences(key,value) VALUES ('grocery_mode',?) "
           "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (mode,))
    config.grocery_mode = mode


async def preferences(update, config, db, mode=None):
    from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard
    from .selection import authorized
    from .telegram_text import send_text
    query = getattr(update, 'callback_query', None)
    if not authorized(update, config):
        if query:
            await query.answer('Somente o usuário autorizado pode alterar esta opção.', show_alert=True)
        return
    if query and (query.data or '').startswith('grocery:'):
        await query.answer()
        mode = (query.data or '').removeprefix('grocery:')
    reply = update.effective_message.reply_text
    if mode == 'cep':
        return await send_text(reply, '📍 Para mudar a localização, envie /cep seguido dos oito números do CEP desejado.')
    if mode:
        try:
            save_mode(db, config, mode)
        except ValueError as exc:
            return await send_text(reply, str(exc))
    current = getattr(config, 'grocery_mode', 'visit')
    cep = getattr(config, 'grocery_postal_code', '')
    label = cep[:5] + '-' + cep[5:] if cep else 'não informado; configure /cep'
    text = ('🏪 Preferências dos supermercados\n\nLocalização de referência: ' + label + '\n'
            + ('Modo: Posso ir à loja — não exige entrega.\n'
               'Mostra e acompanha preços publicados para a loja e região consultadas. '
               'O preço do site pode ser diferente no balcão; confirme a oferta e o estoque antes de ir.'
               if current == 'visit' else
               'Modo: Preciso de entrega — exige validação regional de estoque e entrega.\n'
               'A disponibilidade final depende da confirmação da loja.')
            + '\n\nA opção fica salva após reiniciar. Use /buscar Picanha Maturatta para pesquisar.')
    keyboard = Keyboard([
        [Button(('✅ ' if current == 'visit' else '') + 'Posso ir à loja', callback_data='grocery:visit')],
        [Button(('✅ ' if current == 'delivery' else '') + 'Preciso de entrega', callback_data='grocery:delivery')],
        [Button('📍 Alterar localização (CEP)', callback_data='grocery:cep')],
        [Button('🏠 Menu', callback_data='ui:home')]])
    return await send_text(reply, text, reply_markup=keyboard)
