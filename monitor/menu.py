"""Interface por botoes, com entradas guiadas e confirmacoes em memoria."""
import secrets
import time
import hashlib
import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard, ReplyKeyboardMarkup, ForceReply, ReplyParameters
from .selection import authorized
from .telegram_text import render, send_text

SHORTCUTS = {'🏠 Menu': 'home', '🔎 Buscar': 'search', '🏷️ Promoções': 'promos', '🔔 Monitoramentos': 'list'}
SHORTCUTS['💸 Empréstimos'] = 'loans'


def keyboard(rows):
    return Keyboard([[Button(label, callback_data='ui:'+action) for label, action in row] for row in rows])


def navigation():
    return keyboard([[('🏠 Menu principal', 'home'), ('🔔 Monitoramentos', 'list:0')]])


def fingerprint(row):
    return hashlib.sha256(f"{row['id']}:{row['query']}:{row['seed_ad']}:{row['scope']}".encode()).hexdigest()[:16]


@dataclass
class Input:
    kind: str
    token: str = field(default_factory=lambda: secrets.token_hex(6))
    at: float = field(default_factory=time.monotonic)
    card: str = ''
    step: int = 0
    values: list[str] = field(default_factory=list)
    defaults: list[str] = field(default_factory=list)


class BotMenu:
    def __init__(self, config, db, promotions, dispatch, configure_help):
        self.config, self.db, self.promotions, self.dispatch = config, db, promotions, dispatch
        self.configure_help = configure_help
        self.pending = None
        self.cards = {}
        self.last_user_message_id = None
        from .loans import Loans, LoansMenu
        self.loans = LoansMenu(self, Loans(db))

    def clear(self):
        self.pending = None
        self.loans.pending = None

    def forget(self,pid):
        self.cards={token:value for token,value in self.cards.items() if value[0]!=pid}

    def remember(self,update):
        if not update.callback_query:
            message_id=getattr(update.effective_message,'message_id',None)
            if isinstance(message_id,int):self.last_user_message_id=message_id

    async def group_reply(self,update,label):
        chat_type=getattr(update.effective_chat,'type',None)
        if chat_type not in ('group','supergroup') and not (chat_type is None and self.config.chat<0):return
        kwargs={'reply_markup':ForceReply(selective=self.last_user_message_id is not None,input_field_placeholder=label[:64])}
        if self.last_user_message_id is not None:
            kwargs['reply_parameters']=ReplyParameters(self.last_user_message_id,allow_sending_without_reply=True)
        await update.effective_message.reply_text('✍️ '+label+'\nResponda a esta mensagem para continuar. Para sair, use /cancelar.',**kwargs)

    async def output(self, update, text, markup=None, titles=()):
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(render(text,titles), parse_mode='HTML', reply_markup=markup)
                return
            except Exception:
                pass  # Mensagem antiga, com foto ou ja editada: enviar a nova tela.
        await send_text(update.effective_message.reply_text,text,bold_lines=titles,reply_markup=markup)

    async def home(self, update, context=None):
        if not authorized(update,self.config):
            return
        self.remember(update)
        self.clear()
        if not self.promotions.running and not self.promotions.refreshing:
            self.promotions.session = None
        message_text=(getattr(update.effective_message,'text','') or '').split()
        if message_text and message_text[0].split('@')[0] == '/start':
            await update.effective_message.reply_text('⌨️ Atalhos ativados. Use 🏠 Menu para voltar quando quiser.',
                reply_markup=ReplyKeyboardMarkup([['🔎 Buscar','🏷️ Promoções'],['🔔 Monitoramentos','💸 Empréstimos'],['🏠 Menu']],
                    resize_keyboard=True,is_persistent=True,selective=True))
        counts=self.db.rows('SELECT COUNT(*) AS total, SUM(active) AS active FROM products')[0]
        active=counts['active'] or 0
        text=f'🛍️ Central de ofertas\n\nO que você quer fazer?\n\n🔔 {active} monitoramento(s) ativo(s) · {counts["total"]-active} pausado(s)\nBuscas são pontuais; acompanhar um produto exige sua escolha.'
        if self.promotions.running:
            text+='\n\n🔄 Uma pesquisa de promoções está em andamento. Os resultados serão enviados aqui.'
        elif self.promotions.refreshing:
            text+='\n\n🔄 O catálogo de categorias está sendo atualizado.'
        rows=[
            [('🔎 Buscar produto','search'),('🏷️ Promoções','promos')],
            [('🔔 Meus monitoramentos','list:0')],
            [('💸 Dinheiro emprestado','loans')],
            [('➕ Monitorar produto','monitor'),('🛒 Mercado Livre','ml')],
            [('🗂️ Categorias','categories'),('💡 Exemplos de filtros','examples')],
            [('❓ Ajuda','help'),('ℹ️ Status','status')],
        ]
        from .search_scope import GROCERY_DOMAINS
        if set(getattr(self.config, 'domains', ())) & set(GROCERY_DOMAINS):
            rows.insert(1, [('📍 Supermercados: localização e entrega', 'markets')])
        markup=keyboard(rows)
        await self.output(update,text,markup)

    async def prompt(self, update, kind, card=''):
        self.clear()
        self.pending=Input(kind,card=card)
        prompts={
            'search': ('🔎 Buscar produto','Digite o nome ou link na próxima mensagem.\nExemplo: SSD Kingston NV3 1TB\nVou pesquisar agora, sem ativar acompanhamento.'),
            'ml': ('🛒 Buscar no Mercado Livre','Digite o nome do produto.\nExemplo: notebook Lenovo IdeaPad\nLinks sem preço ou dados verificados serão identificados.'),
            'monitor': ('➕ Escolher produto para acompanhar','Digite o nome, link ou ID do anúncio encontrado.\nExemplo: SSD Kingston NV3 1TB ou 36\nVocê ainda escolherá a oferta e onde acompanhar.'),
            'category': ('🗂️ Escolher categoria','Digite um tema ou link de categoria.\nExemplos: monitores, pets, casa e lazer\nSem página mapeada, a busca será por termo e parcial.'),
            'discount': ('📣 Escolher desconto','No menu Promoções, escolha Maior que 20% até Maior que 80%.\nAlternativa por texto: >30. Exatamente 30% não entra.'),
            'size': ('Escolher tamanho', 'Digite M, G, 4 ou 42, como na loja. Digite todos para ignorar tamanho.'),
            'cep': ('📍 Informar CEP','Digite os 8 números do CEP. Exemplo: 01001000.\nO frete ainda não é cotado; os preços continuarão sem frete.'),
            'grocerycep': ('📍 Localização dos supermercados', 'Digite os oito números do CEP de referência. A localização ficará salva para suas próximas buscas e após reiniciar.'),
        }
        title,body=prompts[kind]
        await self.output(update,title+'\n\n'+body,keyboard([[('✖️ Cancelar entrada','cancel'),('🏠 Menu','home')]]),titles=(title,))
        await self.group_reply(update,'Digite sua resposta')

    async def prompt_promotion(self, update, kind):
        if authorized(update,self.config):
            await self.prompt(update,kind)

    async def require_grocery_region(self, update, query, command='/buscar'):
        from .search_scope import GROCERY_DOMAINS, is_meat_query
        from urllib.parse import urlsplit
        if not authorized(update, self.config) or getattr(self.config, 'grocery_postal_code', ''):
            return False
        domains = set(getattr(self.config, 'domains', ())) & set(GROCERY_DOMAINS)
        host = (urlsplit(query).hostname or '').removeprefix('www.') if query.startswith('https://') else ''
        if not domains or not (is_meat_query(query) or host in domains):
            return False
        await self.prompt(update, 'grocerycep')
        self.pending.values = [command, query]
        await send_text(update.effective_message.reply_text,
            'Sua busca foi guardada. Envie o CEP na próxima mensagem; vou salvar a localização e retomar a pesquisa automaticamente.')
        return True

    async def listing(self, update, page=0):
        self.clear()
        count=self.db.rows('SELECT COUNT(*) AS n FROM products')[0]['n']
        pages=max(1,(count+5)//6)
        page=max(0,min(page,pages-1))
        rows=self.db.rows('SELECT * FROM products ORDER BY id DESC LIMIT 6 OFFSET ?',(page*6,))
        buttons=[]
        for row in rows:
            token=self.card_token(row)
            buttons.append([(f'{"🟢" if row["active"] else "⏸️"} {row["id"]} · {self.title(row)[:44]}','card:'+token+':view')])
        pager=[]
        if page:pager.append(('⬅️ Anterior','list:'+str(page-1)))
        if page+1<pages:pager.append(('Próxima ➡️','list:'+str(page+1)))
        if pager:buttons.append(pager)
        buttons.extend([[('➕ Adicionar produto','monitor')],[('🏠 Menu principal','home')]])
        text=f'🔔 Meus monitoramentos\n\n{count} produto(s) · página {page+1}/{pages}\nToque em um produto para consultar ou controlar o acompanhamento.' if count else '🔔 Meus monitoramentos\n\nSua lista está vazia. Toque em Adicionar produto para começar.'
        await self.output(update,text,keyboard(buttons))

    def title(self,row):
        if row['seed_ad']:
            ad=self.db.get_ad(row['seed_ad'])
            if ad:return ad['title']
        return row['query']

    def card_token(self,row):
        now=time.monotonic()
        self.cards={k:v for k,v in self.cards.items() if now-v[2]<1800}
        if len(self.cards)>=128:self.cards.pop(next(iter(self.cards)))
        token=secrets.token_hex(6)
        self.cards[token]=(row['id'],fingerprint(row),now)
        return token

    def product(self,token):
        value=self.cards.get(token)
        if not value or time.monotonic()-value[2]>=1800:return None
        rows=self.db.rows('SELECT * FROM products WHERE id=?',(value[0],))
        return rows[0] if rows and fingerprint(rows[0])==value[1] else None

    async def detail(self,update,token):
        row=self.product(token)
        if row is None:return await self.expired(update)
        self.clear()
        title=self.title(row)
        due=('Pausado' if not row['active'] else datetime.fromtimestamp(row['next_due'],ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M') if row['next_due'] else 'Aguardando a próxima consulta')
        scope={'site':'só esta oferta','all':'mesmo modelo nas lojas autorizadas'}.get(row['scope'],'cadastro legado; ofertas confirmadas')
        text=f'🔔 Monitoramento {row["id"]}\n\n{title}\n\n{"🟢 Ativo" if row["active"] else "⏸️ Pausado"} · {scope}\nAlertas: {"aumentos e quedas" if row["alert_mode"]=="all" else "quedas filtradas"}\nPróxima consulta: {due}'
        seconds = row['interval_seconds'] or getattr(self.config, 'interval', 18000)
        frequency = f'{seconds / 3600:g} horas' if seconds >= 3600 else f'{seconds / 60:g} minutos'
        text += '\nFrequência: ' + frequency + ' (sujeita à fila e às lojas).'
        baselines = self.db.rows('SELECT COUNT(DISTINCT CASE WHEN p.id IS NOT NULL THEN s.candidate END) AS total, MAX(p.at) AS latest FROM series s '
            'JOIN candidates c ON c.id=s.candidate LEFT JOIN prices p ON p.series=s.id WHERE c.product=?', (row['id'],))[0]
        text += f'\nOfertas com histórico de preço: {baselines["total"]}.'
        if not baselines['total']:
            text += '\nAinda sem preço inicial comparável; os alertas de preço aguardam uma leitura válida.'
        elif baselines['latest']:
            text += '\nÚltimo preço registrado: ' + datetime.fromtimestamp(baselines['latest'],ZoneInfo('America/Sao_Paulo')).strftime('%d/%m às %H:%M') + '.'
        if row['scope'] == 'all':
            from .search_scope import search_domains
            from .adapters import adapter
            names = [adapter(d).name for d in search_domains(title, getattr(self.config, 'domains', ()))]
            text += '\nLojas habilitadas para busca: ' + ', '.join(names) + '.\nEssa lista não comprova leitura em todas; confira /verificar ' + str(row['id']) + '.'
        candidates=self.db.rows('SELECT * FROM candidates WHERE product=? ORDER BY id',(row['id'],))
        pending=sum(not c['confirmed'] for c in candidates)
        text+=f'\n\n{len(candidates)-pending} oferta(s) confirmada(s) · {pending} pendente(s)'
        if pending:
            text+='\nUse “Ofertas para escolher” para confirmar.'
        action='pause' if row['active'] else 'resume'
        label='⏸️ Pausar' if row['active'] else '▶️ Retomar'
        def card(action):return 'card:'+token+':'+action
        rows=[
            [('🔎 Verificar agora',card('check')),('📊 Histórico',card('history'))],
            [(label,card(action)),('⚙️ Alertas e filtros',card('settings'))],
            [('🖼️ Ofertas para escolher',card('options'))],
            [('🗑️ Remover',card('delete'))],
            [('⬅️ Meus monitoramentos','list:0'),('🏠 Menu','home')],
        ]
        if row['scope'] != 'all':
            rows.insert(0, [('🌐 Outras lojas também', card('expand'))])
        await self.output(update,text,keyboard(rows),titles=(title,))

    async def expired(self,update):
        self.clear()
        await self.output(update,'Esta seleção expirou ou o produto foi removido. Abra a lista novamente.',navigation())

    async def settings(self,update,token):
        row=self.product(token)
        if row is None:return await self.expired(update)
        self.clear()
        money=lambda n:f'R$ {n/100:.2f}'.replace('.',',')
        text=f'⚙️ Alertas e filtros\n\nMonitoramento {row["id"]}: {self.title(row)}\n\nModo atual: {"todos os aumentos e quedas" if row["alert_mode"]=="all" else "somente quedas filtradas"}\nQueda mínima: {money(row["minimum"])} e {row["percent"]}%\nPreço-alvo: {money(row["target"]) if row["target"] is not None else "sem alvo"}\n\nOs filtros só se aplicam no modo de quedas. Valor, percentual e alvo precisam ser atendidos juntos.'
        await self.output(update,text,keyboard([
            [('🔔 Avisar aumentos e quedas','card:'+token+':all')],
            [('📉 Somente quedas com filtros','card:'+token+':drops')],
            [('🛠️ Configurar passo a passo','card:'+token+':wizard')],
            [('💡 Ver exemplo explicado','examples')],
            [('⬅️ Voltar ao produto','card:'+token+':view'),('🏠 Menu','home')],
        ]))

    async def wizard(self,update,token):
        row=self.product(token)
        if row is None:return await self.expired(update)
        self.pending=Input('filters',card=token,defaults=[str(Decimal(row['minimum'])/100),row['percent'],str(Decimal(row['target'])/100) if row['target'] is not None else '-'])
        await self.wizard_step(update)

    async def wizard_step(self,update):
        state=self.pending
        texts=[
            'Qual é a queda mínima em reais?\nDigite 50 para exigir queda de pelo menos R$ 50,00.\nDigite 0 para não exigir um valor mínimo.',
            'Qual é a queda mínima em porcentagem?\nDigite 5 para exigir pelo menos 5%.\nDigite 0 para não exigir um percentual mínimo.',
            'Qual é o preço-alvo?\nDigite 1500 para avisar apenas em uma queda que termine em até R$ 1.500,00.\nToque em Sem alvo para não limitar o preço final.',
        ]
        rows=[[('Manter atual: '+state.defaults[state.step],'form:'+state.token+':keep')]]
        if state.step==2:rows.append([('Sem alvo','form:'+state.token+':none')])
        rows.append([('✖️ Cancelar','cancel')])
        await self.output(update,f'⚙️ Configurar filtros · passo {state.step+1}/3\n\n'+texts[state.step]+'\nAceita vírgula ou ponto para decimais, sem separador de milhar.',keyboard(rows))
        await self.group_reply(update,('Queda mínima em reais','Queda mínima percentual','Preço-alvo ou - para remover o alvo')[state.step])

    async def filter_value(self,update,text):
        state=self.pending
        if self.product(state.card) is None:return await self.expired(update)
        try:
            if state.step==2 and text=='-':value='-'
            else:
                pattern=r'\d+(?:[.,]\d{1,4})?' if state.step==1 else r'\d+(?:[.,]\d{1,2})?'
                if not re.fullmatch(pattern,text.strip()):raise ValueError()
                number=Decimal(text.strip().replace(',','.'))
                if not number.is_finite() or number<0 or number>Decimal('1000000000') or (state.step==1 and number>100):raise ValueError()
                if state.step!=1 and number!=number.quantize(Decimal('.01')):raise ValueError()
                if state.step==1 and number!=number.quantize(Decimal('.0001')):raise ValueError()
                if number==0:number=Decimal('0')
                elif state.step==1:number=number.quantize(Decimal('.0001')).normalize()
                else:number=number.quantize(Decimal('.01'))
                value=format(number,'f')
        except (ValueError,InvalidOperation):
            return await send_text(update.effective_message.reply_text,'Digite um número válido e não negativo. Use 50,90 ou 1500 (sem ponto de milhar). O percentual deve estar entre 0 e 100.',reply_markup=keyboard([[('✖️ Cancelar','cancel')]]))
        state.values.append(value)
        state.step+=1
        state.at=time.monotonic()
        if state.step<3:return await self.wizard_step(update)
        state.kind='apply'
        minimum,percent,target=state.values
        display_money=lambda value:'R$ '+format(Decimal(value),'.2f').replace('.',',')
        text=f'✅ Conferir filtros\n\nQueda mínima: {display_money(minimum)} e {percent.replace(".",",")}%\nPreço-alvo: {"sem alvo" if target=="-" else display_money(target)}\n\nAo aplicar, o modo será somente quedas. Todas as condições devem ser atendidas juntas, na mesma oferta e modalidade. Estar abaixo do alvo, sem uma queda, não gera alerta.'
        await self.output(update,text,keyboard([[('✅ Aplicar filtros','apply:'+state.token)],[('✖️ Cancelar','cancel')]]))

    async def text(self,update,context):
        if not authorized(update,self.config):return
        self.remember(update)
        text=(update.effective_message.text or '').strip()
        if text in SHORTCUTS:return await self.action(update,context,SHORTCUTS[text])
        if text.lower() in ('cancelar','voltar','menu'):return await self.home(update,context)
        if self.loans.pending:
            return await self.loans.text(update,text)
        state=self.pending
        if not state:
            if getattr(update.effective_chat,'type','private')=='private':return await self.home(update,context)
            return
        if time.monotonic()-state.at>900:return await self.expired(update)
        if state.kind=='filters':return await self.filter_value(update,text)
        if state.kind in ('apply','remove'):
            return await send_text(update.effective_message.reply_text,'Use os botões de confirmação ou toque em Cancelar.',reply_markup=keyboard([[('✖️ Cancelar','cancel')]]))
        if not text or len(text)>600:
            return await send_text(update.effective_message.reply_text,'Digite um texto com até 600 caracteres.')
        try:
            if state.kind=='discount':
                from .deals.models import DiscountFilter
                DiscountFilter.parse(text)
            if state.kind=='size':
                from .deals.models import parse_size
                parse_size(text)
            if state.kind=='cep' and (len(text.replace('-','').replace(' ',''))!=8 or not text.replace('-','').replace(' ','').isdigit()):
                raise ValueError('Digite um CEP com 8 números, como 01001000.')
            if state.kind=='grocerycep':
                from .grocery_profile import postal_code
                text = postal_code(text.replace(' ', ''))
        except ValueError as exc:
            return await send_text(update.effective_message.reply_text,str(exc),reply_markup=keyboard([[('✖️ Cancelar','cancel')]]))
        command={'search':'/buscar','ml':'/buscarml','monitor':'/monitorar','category':'/categoria','discount':'/descontopromo','cep':'/ceppromo','grocerycep':'/cep','size':'/tamanhopromo'}[state.kind]
        self.clear()
        if state.kind == 'grocerycep' and len(state.values) == 2:
            await self.dispatch(update,context,name='/cep',args=text.split())
            return await self.dispatch(update,context,name=state.values[0],args=state.values[1].split())
        if state.kind in ('category','discount','cep','size'):
            await self.promotions.command(update,context,name=command,args=text.split())
        else:await self.dispatch(update,context,name=command,args=text.split())

    async def action(self,update,context,action):
        if action.startswith('loans'):
            self.clear()
            return await self.loans.action(update, action)
        if action in ('home','cancel'):return await self.home(update,context)
        if action=='list':return await self.listing(update)
        if action=='markets':
            self.clear()
            return await self.dispatch(update,context,name='/mercados',args=[])
        if action in ('search','ml','monitor'):return await self.prompt(update,action)
        if action in ('promos','categories'):
            self.clear()
            return await self.promotions.command(update,context,name='/promocoes',args=[])
        if action=='examples':
            self.clear()
            return await self.output(update,self.configure_help,navigation())
        if action in ('help','status'):
            self.clear()
            return await self.dispatch(update,context,name='/ajuda' if action=='help' else '/status',args=[])

    async def callback(self,update,context):
        if not authorized(update,self.config):
            return await update.callback_query.answer('Somente o usuário autorizado pode usar este menu.',show_alert=True)
        await update.callback_query.answer()
        parts=(update.callback_query.data or '').split(':')
        if len(parts)<2 or parts[0]!='ui':return
        if parts[1]=='loans':
            self.clear()
            return await self.loans.action(update, ':'.join(parts[1:]))
        if len(parts)==2:return await self.action(update,context,parts[1])
        if parts[1]=='list' and len(parts)==3 and parts[2].isdigit():return await self.listing(update,int(parts[2]))
        state=self.pending
        if parts[1] in ('form','apply','remove'):
            if not state or time.monotonic()-state.at>900 or parts[2]!=state.token:return await self.expired(update)
            if parts[1]=='form' and len(parts)==4 and state.kind=='filters':
                if parts[3]=='keep':return await self.filter_value(update,state.defaults[state.step])
                if parts[3]=='none' and state.step==2:return await self.filter_value(update,'-')
            if parts[1]=='apply' and len(parts)==3 and state.kind=='apply':
                row=self.product(state.card)
                if row is None:return await self.expired(update)
                self.clear()
                await self.dispatch(update,context,name='/configurar',args=[str(row['id'])]+state.values)
                return await self.detail(update,state.card)
            if parts[1]=='remove' and len(parts)==3 and state.kind=='remove':
                row=self.product(state.card)
                if row is None:return await self.expired(update)
                self.clear()
                await self.dispatch(update,context,name='/remover',args=[str(row['id'])])
                self.forget(row['id'])
                return await self.listing(update)
            return
        if parts[1]!='card' or len(parts)!=4:return
        token,action=parts[2:]
        row=self.product(token)
        if row is None:return await self.expired(update)
        if action=='view':return await self.detail(update,token)
        if action=='settings':return await self.settings(update,token)
        if action=='wizard':return await self.wizard(update,token)
        if action=='delete':
            self.pending=Input('remove',card=token)
            return await self.output(update,f'🗑️ Remover monitoramento {row["id"]}?\n\n{self.title(row)}\n\nIsso exclui o histórico e os alertas associados. Confirme abaixo.',keyboard([[('🗑️ Confirmar remoção','remove:'+self.pending.token)],[('Manter produto','card:'+token+':view')]]))
        commands={'pause':('/pausar',[]),'resume':('/retomar',[]),'check':('/verificar',[]),
            'history':('/historico',[]),'options':('/opcoes',[]),'all':('/alertas',['todas']),'drops':('/alertas',['quedas']),
            'expand':('/abrangencia',['todas'])}
        if action in commands:
            self.clear()
            name,args=commands[action]
            await self.dispatch(update,context,name=name,args=[str(row['id'])]+args)
            if action in ('all','drops'):await self.settings(update,token)
            elif action in ('pause','resume'):await self.detail(update,token)
            elif action == 'expand':
                fresh = self.db.rows('SELECT * FROM products WHERE id=?', (row['id'],))
                if fresh:
                    await self.detail(update,self.card_token(fresh[0]))
