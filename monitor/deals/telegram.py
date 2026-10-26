"""Navegacao paginada e categorias livres; nenhuma selecao cria acompanhamento."""
import secrets
import time
import logging
from telegram.error import TelegramError
from dataclasses import dataclass, field
from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard
from ..selection import authorized
from ..telegram_text import send_text
from .adapters import ADAPTERS
from .catalog import CategoryCatalog, Category
from .models import DiscountFilter, parse_size
from .formatting import messages

PAGE_SIZE = 8
DISCOUNTS = (5, 10, *range(20, 81, 10))


@dataclass
class Session:
    nonce: str = field(default_factory=lambda: secrets.token_hex(4))
    created: float = field(default_factory=time.monotonic)
    stage: str = 'category'
    discount: DiscountFilter | None = None
    stores: set = field(default_factory=set)
    cep: str = ''
    category: Category | None = None
    group: str = ''
    groups: list[str] = field(default_factory=list)
    choices: list[Category] = field(default_factory=list)
    revision: int = 0
    size: str = ''
    path: tuple[str, ...] = ()
    branches: list[tuple[str, ...]] = field(default_factory=list)
    depth: str = 'expanded'
    validation: str = 'market'


class PromotionsTelegram:
    def __init__(self, config, deals, send, background):
        self.config, self.deals, self.send, self.background = config, deals, send, background
        self.catalog = getattr(deals, 'catalog', None) or CategoryCatalog()
        self.session = None
        self.running = False
        self.refreshing = False
        self.prompt_input = None

    @property
    def domains(self):
        return [d for d in ADAPTERS if d in self.config.domains]

    def new_session(self):
        self.session = Session(depth=getattr(self.config, 'promotions_depth', 'expanded'))
        return self.session

    @property
    def store_choices(self):
        category = self.session.category
        return self.catalog.stores_for(category, self.domains) if category else []

    async def command(self, update, context, name=None, args=None):
        if not authorized(update, self.config):
            return
        async def reply(text, **kwargs):
            await send_text(update.effective_message.reply_text, text, **kwargs)
        name = name or update.effective_message.text.split()[0].split('@')[0].lower()
        if self.running or self.refreshing:
            return await reply('Já há uma consulta ou atualização de categorias em andamento. Os demais comandos continuam disponíveis.')
        args = ' '.join(context.args if args is None else args).strip()
        if name in ('/promocoes', '/categorias', '/categoria'):
            self.new_session()
            if name == '/categorias' and args.lower() == 'atualizar':
                return await self.start_refresh(reply)
            if args:
                return await self.choose_text(args, reply)
            return await self.show_groups(reply)
        session = self.session
        if not session or time.monotonic() - session.created > 1800:
            return await reply('Inicie uma consulta com /promocoes. Esta seleção expira em 30 minutos.')
        try:
            if name == '/descontopromo' and session.stage == 'filter':
                session.discount = DiscountFilter.parse(args)
                if session.discount.inclusive or session.discount.less:
                    session.discount = None
                    raise ValueError('Escolha um botão de Maior que 5% a Maior que 80%.')
                return await self.after_discount(reply)
            if name == '/tamanhopromo' and session.stage in ('size', 'stores'):
                session.size = parse_size(args)
                session.stage = 'stores'
                return await self.show_stores(reply)
            if name == '/ceppromo':
                cep = args.replace(' ', '').replace('-', '')
                if len(cep) != 8 or not cep.isdigit():
                    raise ValueError('Use /ceppromo 01001000. O frete ainda não é cotado; os valores serão apresentados sem frete.')
                session.cep = cep
                await reply('📍 CEP registrado somente para esta pesquisa. Os adaptadores ainda não cotam o frete; os preços serão apresentados sem frete.')
                if session.stage == 'stores':
                    return await self.show_stores(reply)
                return
            return await reply('Escolha a etapa pelos botões. Em Promoções, os descontos vão de Maior que 20% a Maior que 80%.')
        except ValueError as exc:
            return await reply(str(exc))

    async def choose_text(self, text, reply):
        try:
            group = 'Computadores' if text.strip().casefold() in ('computador', 'computadores') else text.strip()
            if group in self.catalog.navigation_groups(self.domains):
                return await self.show_tree(reply, (group,))
            found = self.catalog.find(text, self.domains) if not text.startswith('https://') else []
            if found:
                self.session.stage = 'subcategory'
                self.session.group = 'Categorias encontradas'
                self.session.choices = found
                return await self.show_choices(reply)
            choice = self.catalog.request(text, self.deals.fetcher)
            return await self.select(choice, reply)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ValueError) else 'Link recusado. Use HTTPS e uma loja autorizada.'
            return await reply(message)

    def keyboard(self, buttons):
        session = self.session
        session.revision += 1
        rows=[[Button(label, callback_data=f'promo:{session.nonce}:{session.revision}:{action}')] for label, action in buttons]
        rows.append([Button('🏠 Menu principal',callback_data='ui:home')])
        return Keyboard(rows)

    async def show_groups(self, reply, page=0):
        session = self.session
        session.stage = 'category'
        session.groups = self.catalog.navigation_groups(self.domains)
        pages = max(1, (len(session.groups) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        start = page * PAGE_SIZE
        buttons = [(label, f'group{i}') for i, label in enumerate(session.groups[start:start+PAGE_SIZE], start)]
        if page:
            buttons.append(('⬅️ Anterior', f'groups{page-1}'))
        if page + 1 < pages:
            buttons.append(('Próxima ➡️', f'groups{page+1}'))
        buttons += [('✍️ Digitar categoria ou link', 'custom'), ('🔄 Atualizar categorias das lojas', 'refresh')]
        return await reply(f'🏷️ Busca pontual de promoções\n\nEscolha uma categoria — página {page+1}/{pages}.\nTambém pode digitar /categoria notebooks, /categoria pets ou /categoria https://link-da-categoria.\nO catálogo contém links observados nas lojas; acesso e preços serão conferidos na pesquisa.', reply_markup=self.keyboard(buttons))

    async def show_choices(self, reply, page=0):
        session = self.session
        pages = max(1, (len(session.choices) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        start = page * PAGE_SIZE
        buttons = [(' > '.join(c.path[1:]) if session.group != 'Categorias encontradas' else c.title, f'pick{i}') for i, c in enumerate(session.choices[start:start+PAGE_SIZE], start)]
        if page:
            buttons.append(('⬅️ Anterior', f'choices{page-1}'))
        if page + 1 < pages:
            buttons.append(('Próxima ➡️', f'choices{page+1}'))
        buttons.append(('↩️ Todas as categorias', 'home'))
        return await reply(f'{session.group} · escolha a subcategoria\nPágina {page+1}/{pages}. Para outro tema: /categoria nome.', reply_markup=self.keyboard(buttons))

    async def show_tree(self, reply, path, page=0):
        session = self.session
        session.stage, session.path = 'tree', path
        session.branches = self.catalog.branches(path, self.domains)
        pages = max(1, (len(session.branches) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        start = page * PAGE_SIZE
        buttons = [('Tudo nesta categoria', 'scopeall')]
        buttons += [(branch[-1], f'node{i}') for i, branch in enumerate(session.branches[start:start + PAGE_SIZE], start)]
        if page:
            buttons.append(('⬅️ Anterior', f'treepage{page-1}'))
        if page + 1 < pages:
            buttons.append(('Próxima ➡️', f'treepage{page+1}'))
        buttons.append(('↩️ Voltar', 'treeback'))
        return await reply('🗂️ ' + ' > '.join(path) + f'\n\nEscolha a subcategoria ou Tudo nesta categoria.\nPágina {page+1}/{pages}.\nAs páginas usadas são as categorias reais de cada loja.', reply_markup=self.keyboard(buttons))

    async def select(self, category, reply):
        session = self.session
        session.size = ''
        session.category, session.stage = category, 'filter'
        session.stores.intersection_update(self.store_choices)
        return await reply(f'🏷️ {category.title}\n\nEscolha a economia mínima.\nComparo o mesmo modelo e condições em pelo menos duas outras lojas. Sem isso, só aceito queda registrada no histórico do robô. O “de/por” do anúncio não basta.\n“Maior que 5%” exclui exatamente 5%. Depois escolha as lojas para pesquisar e comparar.', reply_markup=self.keyboard([(f'Maior que {value}%', f'gt{value}') for value in DISCOUNTS]))

    async def after_discount(self, reply):
        if self.store_choices == ['lacoste.com']:
            return await self.show_sizes(reply)
        self.session.stage = 'stores'
        return await self.show_stores(reply)

    async def show_sizes(self, reply):
        self.session.stage = 'size'
        buttons = [('Ignorar tamanho (todos)', 'sizeall')]
        buttons += [(size, 'size'+size) for size in ('PP', 'P', 'M', 'G', 'GG', 'XG', 'TU', '2', '3', '4', '5', '6')]
        buttons += [('Outro tamanho / calçado', 'sizecustom')]
        return await reply('Escolha o tamanho exatamente como aparece na loja. Não converto M em número Lacoste. Para um tamanho específico, só entram itens com estoque confirmado nesse tamanho.\nTambém aceita /tamanhopromo 42 ou /tamanhopromo todos.', reply_markup=self.keyboard(buttons))

    async def show_stores(self, reply):
        available = self.store_choices
        self.session.stores.intersection_update(available)
        buttons = [(('✅ ' if d in self.session.stores else '⬜ ') + ADAPTERS[d].store, 'store'+str(i)) for i, d in enumerate(available)]
        if 'lacoste.com' in self.session.stores:
            buttons.append(('Tamanho: ' + (self.session.size or 'todos') + ' — alterar', 'sizes'))
        buttons += [('TODAS', 'all'), ('Limpar seleção', 'none'), ('🔎 Pesquisar agora', 'run'), ('↩️ Trocar desconto', 'filterback'), ('↩️ Trocar categoria', 'home')]
        buttons.insert(-3, ('Busca: ' + ('Ampliada (48 produtos/loja)' if self.session.depth == 'expanded' else 'Rápida (12 produtos/loja)'), 'depth'))
        title = self.session.category.title if self.session.category else 'Categoria não selecionada'
        return await reply(f'🏷️ {title}\n\nSelecione as lojas e toque em Pesquisar agora.\nSelecionadas: {len(self.session.stores)} de {len(available)}.\nTODAS marca somente as lojas com categoria mapeada para esta escolha.\nNenhuma loja é marcada automaticamente.', reply_markup=self.keyboard(buttons))

    async def start_refresh(self, reply):
        if self.refreshing or self.running:
            return await reply('Já existe uma consulta ou atualização em andamento. Aguarde a conclusão.')
        self.refreshing = True
        session = self.session
        self.background(self.refresh(session, reply))
        await reply('🔄 Consultando os menus públicos das lojas. O catálogo anterior será preservado em caso de bloqueio. A descoberta é parcial e pode levar alguns minutos.')

    async def refresh(self, session, reply):
        try:
            notices = await self.catalog.refresh(self.deals.fetcher, self.domains)
            await reply('✅ Catálogo atualizado\n' + '\n'.join(notices))
            if self.session is session:
                await self.show_groups(reply)
        except Exception:
            await reply('Não foi possível atualizar os menus. As categorias anteriores continuam disponíveis.')
        finally:
            self.refreshing = False

    async def callback(self, update, context):
        if not authorized(update, self.config):
            return
        query, session = update.callback_query, self.session
        parts = (query.data or '').split(':')
        valid = len(parts) == 4 and session and parts[2] == str(session.revision)
        if (not valid or not session or parts[1] != session.nonce or time.monotonic()-session.created > 1800 or self.running or self.refreshing):
            return await query.answer('Esta seleção expirou ou já há uma pesquisa em andamento. Inicie outra com /promocoes.', show_alert=True)
        await query.answer()
        action = parts[-1]
        async def reply(text, **kwargs):
            await send_text(query.message.reply_text, text, **kwargs)
        if action == 'home':
            return await self.show_groups(reply)
        if action.startswith('treepage') and action[8:].isdigit() and session.stage == 'tree':
            return await self.show_tree(reply, session.path, int(action[8:]))
        if action == 'treeback' and session.stage == 'tree':
            if len(session.path) > 1:
                return await self.show_tree(reply, session.path[:-1])
            return await self.show_groups(reply)
        if action == 'scopeall' and session.stage == 'tree':
            return await self.select(self.catalog.scope(session.path, self.domains), reply)
        if action.startswith('node') and action[4:].isdigit() and session.stage == 'tree':
            index = int(action[4:])
            if index < len(session.branches):
                path = session.branches[index]
                if self.catalog.branches(path, self.domains):
                    return await self.show_tree(reply, path)
                return await self.select(self.catalog.scope(path, self.domains), reply)
        if action == 'custom':
            if self.prompt_input:
                return await self.prompt_input(update,'category')
            return await reply('✍️ Digite /categoria seguido do tema ou de um link de categoria.\nExemplos de uso\n/categoria monitores\n/categoria casa e lazer\n/categoria brinquedos\n/categoria https://www.pichau.com.br/pets\nSe não houver categoria mapeada, a pesquisa será por termo e ficará identificada como parcial.')
        if action == 'discount' and session.stage == 'filter':
            if self.prompt_input:
                return await self.prompt_input(update,'discount')
            return await reply('Use /descontopromo >30, >=30, <30 ou <=30.')
        if action == 'sizecustom' and session.stage == 'size':
            if self.prompt_input:
                return await self.prompt_input(update, 'size')
            return await reply('Use /tamanhopromo M, /tamanhopromo 4 ou /tamanhopromo 42. Para ignorar: /tamanhopromo todos.')
        if action.startswith('size') and session.stage == 'size' and action != 'sizecustom':
            session.size = parse_size('todos' if action == 'sizeall' else action[4:])
            session.stage = 'stores'
            return await self.show_stores(reply)
        if action == 'sizes' and session.stage == 'stores':
            return await self.show_sizes(reply)
        if action == 'cep' and session.stage == 'stores':
            if self.prompt_input:
                return await self.prompt_input(update,'cep')
            return await reply('Use /ceppromo 01001000. Frete ainda não cotado.')
        if action == 'refresh':
            return await self.start_refresh(reply)
        for prefix, method in (('groups', self.show_groups), ('choices', self.show_choices)):
            if action.startswith(prefix) and action[len(prefix):].isdigit():
                return await method(reply, int(action[len(prefix):]))
        if action.startswith('group') and action[5:].isdigit() and session.stage == 'category':
            index = int(action[5:])
            if index < len(session.groups):
                return await self.show_tree(reply, (session.groups[index],))
        if action.startswith('pick') and action[4:].isdigit() and session.stage == 'subcategory':
            index = int(action[4:])
            if index < len(session.choices):
                return await self.select(session.choices[index], reply)
        if action in {f'gt{value}' for value in DISCOUNTS} and session.stage == 'filter':
            session.discount = DiscountFilter.parse('>' + action[2:])
            return await self.after_discount(reply)
        if session.stage != 'stores':
            return await reply('Este botão pertence a uma etapa anterior. Use a seleção mais recente.')
        if action == 'all':
            session.stores = set(self.store_choices)
            return await self.show_stores(reply)
        if action == 'depth':
            session.depth = 'quick' if session.depth == 'expanded' else 'expanded'
            return await self.show_stores(reply)
        if action == 'none':
            session.stores.clear()
            return await self.show_stores(reply)
        if action == 'filterback':
            return await self.select(session.category, reply)
        if action.startswith('store') and action[5:].isdigit():
            index = int(action[5:])
            if index < len(self.store_choices):
                session.stores.symmetric_difference_update({self.store_choices[index]})
                return await self.show_stores(reply)
        if action == 'run':
            if not session.stores:
                return await reply('Selecione pelo menos uma loja para continuar.')
            if not session.category:
                return await reply('Escolha a categoria com /promocoes antes de pesquisar.')
            if not session.discount:
                return await reply('Escolha o desconto antes de pesquisar.')
            self.running, session.stage = True, 'running'
            self.background(self.execute(session))
            await reply(
                f'🔎 Pesquisando promoções…\n\n'
                f'🏷️ {session.category.title}\n'
                f'📉 Economia mínima: {session.discount}\n'
                f'🏪 Lojas selecionadas: {len(session.stores)}\n\n'
                '⏳ Vou ler e comparar preços. A busca ampliada pode levar alguns minutos. Avisarei quando terminar.'
            )

    async def execute(self, session):
        try:
            try:
                kwargs = {'depth': session.depth, 'validation': session.validation}
                if session.size:
                    kwargs['size'] = session.size
                report = await self.deals.run(session.category, session.discount, sorted(session.stores), session.cep, **kwargs)
                output = list(messages(report))
            except Exception as exc:
                logging.getLogger(__name__).critical('promo_search_failed type=%s', type(exc).__name__)
                await self.send('🏁 Pesquisa finalizada\n\nUma falha impediu a consulta. Tente novamente mais tarde.')
                return
            failed = 0
            for text in output:
                try:
                    await self.send(text)
                except TelegramError as exc:
                    failed += 1
                    logging.getLogger(__name__).critical('promo_delivery_failed type=%s', type(exc).__name__)
            if failed:
                try:
                    await self.send('🏁 Pesquisa finalizada\n\nO envio de algumas mensagens não foi confirmado. Pesquise novamente para receber os resultados completos.')
                except TelegramError:
                    pass
        finally:
            self.running, self.session = False, None
