"""Assistente efemero de consulta; nenhum job ou registro de monitoramento."""
import secrets
import time
from dataclasses import dataclass, field
from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard
from ..selection import authorized
from .adapters import ADAPTERS
from .models import DiscountFilter
from .formatting import messages


@dataclass
class Session:
    nonce: str = field(default_factory=lambda: secrets.token_hex(4))
    created: float = field(default_factory=time.monotonic)
    stage: str = 'category'
    discount: DiscountFilter | None = None
    stores: set = field(default_factory=set)
    cep: str = ''


class PromotionsTelegram:
    def __init__(self, config, deals, send, background):
        self.config, self.deals, self.send, self.background = config, deals, send, background
        self.session = None
        self.running = False

    @property
    def domains(self):
        return [d for d in ADAPTERS if d in self.config.domains]

    async def command(self, update, context):
        if not authorized(update, self.config):
            return
        reply = update.effective_message.reply_text
        name = update.effective_message.text.split()[0].split('@')[0].lower()
        if self.running:
            return await reply('Já existe uma pesquisa de promoções em andamento; os demais comandos continuam disponíveis.')
        if name == '/promocoes':
            self.session = Session(stores=set(self.domains))
            return await reply('🏷️ Busca pontual de promoções. Escolha a categoria:', reply_markup=self.keyboard([('Hardware', 'hardware')]))
        session = self.session
        if not session or time.monotonic() - session.created > 1800:
            return await reply('Inicie com /promocoes. A seleção expira em 30 minutos.')
        try:
            if name == '/descontopromo' and session.stage == 'filter':
                session.discount = DiscountFilter.parse(' '.join(context.args))
                session.stage = 'stores'
                return await self.show_stores(reply)
            if name == '/ceppromo':
                cep = ''.join(context.args).replace('-', '')
                if len(cep) != 8 or not cep.isdigit():
                    raise ValueError('Use /ceppromo 01001000. Frete só será incluído se houver cotação verificável; por enquanto será informado como não consultado.')
                session.cep = cep
                return await reply('CEP registrado apenas nesta pesquisa. Frete ainda não é cotado pelos adaptadores; preços serão apresentados sem frete.')
            return await reply('Escolha a etapa pelos botões. Percentual personalizado: /descontopromo >=25,5 na etapa de desconto.')
        except ValueError as exc:
            return await reply(str(exc))

    def keyboard(self, buttons):
        return Keyboard([[Button(label, callback_data=f'promo:{self.session.nonce}:{action}')] for label, action in buttons])

    async def show_stores(self, reply):
        choices = [('✅ ' if d in self.session.stores else '⬜ ') + ADAPTERS[d].store for d in self.domains]
        buttons = [(label, 'store' + str(i)) for i, label in enumerate(choices)]
        buttons += [('Todas as lojas habilitadas', 'all'), ('🔎 Pesquisar agora', 'run')]
        return await reply('Selecione as lojas. Toque para marcar/desmarcar e depois em Pesquisar agora. Opcional: /ceppromo 01001000. A consulta é limitada e não ativa alertas.', reply_markup=self.keyboard(buttons))

    async def callback(self, update, context):
        if not authorized(update, self.config):
            return
        query = update.callback_query
        session = self.session
        parts = (query.data or '').split(':')
        if (len(parts) != 3 or not session or session.nonce != parts[1]
                or time.monotonic() - session.created > 1800 or self.running):
            return await query.answer('Seleção expirada ou pesquisa em andamento.', show_alert=True)
        await query.answer()
        action = parts[2]
        reply = query.message.reply_text
        if action == 'hardware' and session.stage == 'category':
            session.stage = 'subcategory'
            return await reply('Hardware > escolha a subcategoria:', reply_markup=self.keyboard([('Placas-mãe', 'motherboards')]))
        if action == 'motherboards' and session.stage == 'subcategory':
            session.stage = 'filter'
            return await reply('Escolha o desconto anunciado ou use /descontopromo >25,5. >30 exclui 30%; >=30 inclui 30%.', reply_markup=self.keyboard([('Maior que 30%', 'gt30'), ('Maior ou igual a 30%', 'ge30')]))
        if action in ('gt30', 'ge30') and session.stage == 'filter':
            session.discount = DiscountFilter.parse('>30' if action == 'gt30' else '>=30')
            session.stage = 'stores'
            return await self.show_stores(reply)
        if session.stage != 'stores':
            return await reply('Este botão pertence a uma etapa anterior. Use a seleção mais recente.')
        if action == 'all':
            session.stores = set(self.domains)
            return await self.show_stores(reply)
        if action.startswith('store') and action[5:].isdigit():
            index = int(action[5:])
            if index < len(self.domains):
                domain = self.domains[index]
                session.stores.symmetric_difference_update({domain})
                return await self.show_stores(reply)
        if action == 'run':
            if not session.stores:
                return await reply('Selecione pelo menos uma loja.')
            self.running = True  # Antes do primeiro await: callbacks duplicados nao iniciam outro job.
            session.stage = 'running'
            self.background(self.execute(session))
            await reply('🔎 Pesquisa pontual iniciada. Até 2 páginas de categoria e 12 produtos por loja; comparações complementares limitadas. Pode levar alguns minutos. Nenhum monitoramento será criado.')

    async def execute(self, session):
        try:
            report = await self.deals.run('hardware/placas-mae', session.discount, sorted(session.stores), session.cep)
            for text in messages(report):
                await self.send(text)
        except Exception:
            await self.send('Pesquisa de promoções encerrada com falha inesperada. Nenhum acompanhamento foi criado; tente novamente com menos lojas.')
        finally:
            self.running = False
            self.session = None
