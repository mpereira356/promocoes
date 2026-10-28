"""Separate parsed snapshots from prices actually recorded for monitoring."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from .discovery import REASONS


def amount(value):
    return ('R$ ' + f'{value // 100:,}'.replace(',', '.') + f',{value % 100:02d}') if type(value) is int and value > 0 else 'preço não lido'


def history_text(db, pid):
    rows = db.rows('SELECT * FROM products WHERE id=?', (pid,))
    if not rows:
        return 'Monitoramento não encontrado.'
    series = db.rows('SELECT s.* FROM series s JOIN candidates c ON c.id=s.candidate WHERE c.product=? ORDER BY s.id', (pid,))
    lines = [f'📊 Histórico do monitoramento {pid}']
    lines.append('Modalidade: ' + ('preço publicado por anúncio; condição ausente não é presumida como novo.'
        if rows[0]['monitor_policy'] == 'listing_price' else 'comparações com condição e pagamento declarados.'))
    if not series:
        lines.append('Ainda não há preço inicial registrado em uma série de acompanhamento. Leituras recebidas não significam alertas prontos.')
    for s in series:
        condition = {'NewCondition':'Novo','UsedCondition':'Usado',
                     'RefurbishedCondition':'Recondicionado','DamagedCondition':'Danificado'}.get(s['condition'], s['condition'] or 'não declarada')
        lines.append(f"\nOferta {s['candidate']} · {s['seller']}\n"
                     f"Pagamento: {s['payment'] or 'não confirmado'} · Condição: {condition}\n"
                     f"Último preço: {amount(s['last'])} · Menor registrado: {amount(s['lowest'])}")
    checks = db.rows('SELECT h.at,h.status,h.detail,c.id AS cid,c.store FROM checks h JOIN candidates c ON c.id=h.candidate '
                    'WHERE c.product=? ORDER BY h.id DESC LIMIT 8', (pid,))
    if checks:
        lines.append('\nÚltimas consultas:')
    for check in checks:
        stamp = datetime.fromtimestamp(check['at'], ZoneInfo('America/Sao_Paulo')).strftime('%d/%m às %H:%M')
        if check['status'] != 'ok':
            lines.append(f"{stamp} · {check['store']} · Oferta {check['cid']}: "
                         + REASONS.get(check['status'], 'leitura não confirmada') + '.')
            continue
        try:
            data = json.loads(check['detail'])
        except (ValueError, TypeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        recorded = db.rows('SELECT p.id FROM prices p JOIN series s ON s.id=p.series WHERE s.candidate=? AND p.at=? AND p.price=?',
                           (check['cid'], check['at'], data.get('price') if type(data.get('price')) is int else None))
        state = ('registrado no acompanhamento' if recorded else
                 'apenas leitura; não entrou em uma série de preços nessa consulta')
        missing = '' if data.get('condition') else ' · condição não declarada'
        lines.append(f"{stamp} · {check['store']} · Oferta {check['cid']}: {amount(data.get('price'))} · {state}{missing}.")
    return '\n'.join(lines)
