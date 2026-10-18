"""Emprestimos pessoais e lembretes persistentes, sem contato com devedores."""
import asyncio
import re
import time
from datetime import datetime, time as daytime
from zoneinfo import ZoneInfo

from .display_money import display_money

TZ = ZoneInfo('America/Sao_Paulo')


def reais(cents):
    return 'R$ ' + f'{cents / 100:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def parse_amount(text):
    text = text.strip().removeprefix('R$').strip()
    if re.fullmatch(r'\d+', text):
        text += ',00'
    value = display_money(text)
    if value is None or value > 100_000_000_00:
        raise ValueError('Informe um valor positivo. Exemplo: 150 ou 1.250,50.')
    return value


def parse_date(text, today=None):
    try:
        value = datetime.strptime(text.strip(), '%d/%m/%Y').date()
    except ValueError:
        raise ValueError('Use dia/mês/ano. Exemplo: 25/12/2026.') from None
    if value < (today or datetime.now(TZ).date()):
        raise ValueError('Escolha hoje ou uma data futura.')
    return value.isoformat()


class Loans:
    def __init__(self, db):
        self.db = db
        self.lock = asyncio.Lock()
        db.conn.executescript('''
          CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, person TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK(amount > 0), due TEXT NOT NULL,
            paid_at REAL, created_at REAL NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS loan_reminders (
            loan INTEGER NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL, slot INTEGER NOT NULL, sent_at REAL NOT NULL,
            PRIMARY KEY(loan,revision,slot));
        ''')

    def add(self, person, amount, due):
        return self.db.run('INSERT INTO loans(person,amount,due,created_at) VALUES(?,?,?,?)',
                           (person, amount, due, time.time()))

    def get(self, lid):
        rows = self.db.rows('SELECT * FROM loans WHERE id=?', (lid,))
        return rows[0] if rows else None

    def pay(self, lid):
        self.db.run('UPDATE loans SET paid_at=? WHERE id=? AND paid_at IS NULL', (time.time(), lid))

    def postpone(self, lid, due):
        self.db.run('UPDATE loans SET due=?,revision=revision+1 WHERE id=? AND paid_at IS NULL', (due, lid))

    async def tick(self, send, now=None):
        now = time.time() if now is None else now
        async with self.lock:
            for row in self.db.rows('SELECT * FROM loans WHERE paid_at IS NULL ORDER BY due,id'):
                sent = self.db.rows('SELECT slot,sent_at FROM loan_reminders WHERE loan=? AND revision=?',
                                    (row['id'], row['revision']))
                slots = {r['slot'] for r in sent}
                # Retomada apos indisponibilidade: nao enviar os dois avisos juntos.
                if sent and now - max(r['sent_at'] for r in sent) < 3600:
                    continue
                due = datetime.fromisoformat(row['due']).date()
                for slot, hour in enumerate((9, 18)):
                    if slot in slots or now < datetime.combine(due, daytime(hour), TZ).timestamp():
                        continue
                    text = (f'💸 Lembrete de cobrança · {slot + 1}/2\n\n'
                            f'{row["person"]}\nValor: {reais(row["amount"])}\n'
                            f'Data combinada: {due:%d/%m/%Y}\n\n'
                            'Abra 💸 Dinheiro emprestado no menu para marcar como pago ou prorrogar.')
                    try:
                        await send(text)
                    except Exception:
                        break  # Falha nao marca envio; nova tentativa no proximo ciclo.
                    self.db.run('INSERT OR IGNORE INTO loan_reminders VALUES(?,?,?,?)',
                                (row['id'], row['revision'], slot, now))
                    break

    async def scheduler(self, send, runner=None):
        while True:
            try:
                if runner:
                    await runner(lambda: self.tick(send))
                else:
                    await self.tick(send)
            except Exception:
                pass  # Uma falha nao encerra os proximos lembretes.
            await asyncio.sleep(30)


class LoansMenu:
    def __init__(self, menu, loans):
        self.menu, self.loans = menu, loans
        self.pending = None

    async def show(self, update, text, rows):
        from .menu import keyboard
        title = text.split('\n')[0]
        await self.menu.output(update, text, keyboard(rows + [[('🏠 Menu principal', 'home')]]), titles=(title,))

    async def listing(self, update, paid=False, page=0):
        self.pending = None
        condition = 'IS NOT NULL' if paid else 'IS NULL'
        all_rows = self.loans.db.rows(f'SELECT * FROM loans WHERE paid_at {condition} ORDER BY due,id')
        page = max(0, min(page, max(0, (len(all_rows)-1)//8)))
        rows = all_rows[page*8:page*8+8]
        total = sum(r['amount'] for r in all_rows)
        title = '✅ Empréstimos pagos' if paid else '💸 Dinheiro emprestado'
        text = f'{title}\n\n{len(all_rows)} registro(s) · Total: {reais(total)}\n'
        text += 'Lembretes às 09h e 18h (horário de Brasília).\n' if not paid else ''
        buttons = [[('➕ Emprestar', 'loans:new'), ('✅ Pagos' if not paid else '⏳ Pendentes', f'loans:list:{0 if paid else 1}:0')]]
        today = datetime.now(TZ).date().isoformat()
        for r in rows:
            icon = '✅' if paid else '🔴' if r['due'] < today else '⏳'
            date = datetime.fromisoformat(r['due']).strftime('%d/%m/%Y')
            text += f'\n{icon} #{r["id"]} · {r["person"]} · {reais(r["amount"])} · {date}'
            buttons.append([(f'{icon} #{r["id"]} · {r["person"][:30]}', f'loans:view:{r["id"]}')])
        pager = []
        if page: pager.append(('⬅️ Anterior', f'loans:list:{int(paid)}:{page-1}'))
        if (page+1)*8 < len(all_rows): pager.append(('Próxima ➡️', f'loans:list:{int(paid)}:{page+1}'))
        if pager: buttons.append(pager)
        await self.show(update, text, buttons)

    async def detail(self, update, lid):
        self.pending = None
        r = self.loans.get(lid)
        if not r: return await self.listing(update)
        date = datetime.fromisoformat(r['due']).strftime('%d/%m/%Y')
        text = f'💸 Empréstimo #{lid}\n\nPessoa: {r["person"]}\nValor: {reais(r["amount"])}\nCobrar em: {date}\nStatus: {"✅ Pago" if r["paid_at"] else "⏳ Falta pagar"}'
        rows = [] if r['paid_at'] else [[('✅ Marcar como pago', f'loans:pay:{lid}')], [('📅 Prorrogar', f'loans:postpone:{lid}'), ('⏳ Falta pagar', f'loans:unpaid:{lid}')]]
        await self.show(update, text, rows + [[('⬅️ Empréstimos', 'loans')]])

    async def prompt(self, update, state):
        self.pending = state
        state['at'] = time.monotonic()
        prompts = {'name': 'Qual é o nome da pessoa?\nExemplo: João Silva',
                   'amount': 'Qual valor você emprestou?\nExemplo: 150 ou 1.250,50',
                   'date': 'Em qual data deseja cobrar?\nExemplo: 25/12/2026\nUse dia/mês/ano. Lembretes às 09h e 18h, horário de Brasília.'}
        await self.show(update, '💸 Registrar empréstimo\n\n'+prompts[state['step']], [[('✖️ Cancelar', 'loans')]])
        await self.menu.group_reply(update, 'Digite sua resposta')

    async def action(self, update, action):
        parts = action.split(':')
        if len(parts) == 1: return await self.listing(update)
        if parts[1] == 'list' and len(parts) == 4:
            return await self.listing(update, parts[2] == '1', int(parts[3]))
        if parts[1] == 'new': return await self.prompt(update, {'step':'name'})
        if len(parts) != 3 or not parts[2].isdigit(): return
        lid = int(parts[2])
        row = self.loans.get(lid)
        if not row: return await self.listing(update)
        if parts[1] == 'pay' and not row['paid_at']:
            return await self.show(update, f'✅ Confirmar pagamento?\n\n{row["person"]} · {reais(row["amount"])}\nOs lembretes serão encerrados.', [[('✅ Confirmar pagamento', f'loans:paid:{lid}'), ('Voltar', f'loans:view:{lid}')]])
        if parts[1] == 'paid': self.loans.pay(lid)
        if parts[1] == 'postpone' and not row['paid_at']:
            return await self.prompt(update, {'step':'date','lid':lid})
        return await self.detail(update, lid)

    async def text(self, update, text):
        state = self.pending
        if time.monotonic() - state['at'] > 900:
            return await self.listing(update)
        try:
            if state['step'] == 'name':
                if not text or len(text) > 80 or any(ord(c) < 32 for c in text):
                    raise ValueError('Informe um nome com até 80 caracteres, em uma linha.')
                state['person'], state['step'] = text, 'amount'
            elif state['step'] == 'amount':
                state['amount'], state['step'] = parse_amount(text), 'date'
            else:
                due = parse_date(text)
                if 'lid' in state:
                    lid = state['lid']
                    self.loans.postpone(lid, due)
                else:
                    lid = self.loans.add(state['person'], state['amount'], due)
                return await self.detail(update, lid)
        except ValueError as exc:
            return await self.show(update, '⚠️ Confira sua resposta\n\n'+str(exc), [[('✖️ Cancelar', 'loans')]])
        await self.prompt(update, state)
