"""One authorized Telegram command configures a persistent exact-model watch."""
from decimal import Decimal, InvalidOperation
from .selection import authorized
from .search_scope import search_domains
from .adapters import adapter
from .telegram_text import send_text


async def configure_watch(update, config, db, args, on_check):
    if not authorized(update, config):
        return
    reply = update.effective_message.reply_text
    try:
        if len(args) not in (1, 2) or not args[0].isascii() or not args[0].isdigit() or int(args[0]) <= 0:
            raise ValueError()
        pid = int(args[0])
        minutes = Decimal(args[1].replace(',', '.')) if len(args) == 2 else Decimal(30)
        if not minutes.is_finite() or not 15 <= minutes <= 1440:
            raise ValueError()
    except (ValueError, InvalidOperation):
        return await send_text(reply, 'Use /vigiar ID MINUTOS, de 15 a 1440 minutos. Exemplo: /vigiar 10 15. Sem minutos, usa 30.')
    rows = db.rows('SELECT * FROM products WHERE id=?', (pid,))
    if not rows:
        return await send_text(reply, 'Monitoramento não encontrado. Confira o ID em /lista.')
    ad = db.get_ad(rows[0]['seed_ad']) if rows[0]['seed_ad'] else None
    if not ad:
        return await send_text(reply, 'Falta o anúncio de origem para identificar o modelo exato. Busque e selecione o anúncio correto antes de usar /vigiar.')
    domains = search_domains(ad['title'], getattr(config, 'domains', ()))
    if not domains:
        return await send_text(reply, 'Nenhuma loja compatível está habilitada. A configuração do monitoramento não foi alterada.')
    status, target = db.configure_watch(pid, minutes)
    if status == 'existing':
        return await send_text(reply, f'Já existe o monitoramento {target} para esse anúncio em outras lojas. '
                               f'O monitoramento {pid} não foi alterado. Para configurar o existente: /vigiar {target} {minutes:g}.')
    if status != 'configured':
        return await send_text(reply, 'Não foi possível configurar este monitoramento. Consulte /lista; o modelo precisa de um anúncio de origem válido.')
    names = ', '.join(adapter(domain).name for domain in domains)
    await send_text(reply, f'✅ Vigilância configurada · Monitoramento {pid}\n\n'
        + ad['title'][:450] + '\n\n'
        + f'🟢 Ativo, sem data para encerrar.\n🌐 Mesmo modelo em: {names}.\n'
        + f'⏱️ Próxima consulta agendada agora; depois, {minutes:g} minutos após cada consulta, sujeito à fila e aos limites das lojas.\n'
        + '🔔 Avisos de aumentos e quedas do preço publicado em cada anúncio confirmado.\n'
        + 'Se a condição não for declarada, ela permanecerá desconhecida: os avisos não comprovam produto novo nem promoção sobre o mercado.\n'
        + 'ID, histórico e filtros preservados. Preferências mantidas após reiniciar.\n'
        + f'Consulte /historico {pid}. Novas ofertas ambíguas aguardam sua escolha em /opcoes {pid}.\n'
        + 'Bloqueios e dados insuficientes podem impedir leituras; consulte o histórico. Não é detecção em tempo real.')
    on_check(pid)
