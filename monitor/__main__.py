import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import BotCommand, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from .config import Config
from .db import DB
from .network import Fetcher
from .search import Search, search_error_message
from .adapters.base import ReadError
from .service import Monitor
from .instance import InstanceLock
from .selection import authorized, send_card, handle_choice
from .search_results import deliver_search
from .adapters import adapter
from .subscriptions import ask_scope, handle_subscription
from .version import VERSION
from .deals.service import Deals
from .deals.telegram import PromotionsTelegram
from .telegram_text import send_text
from .menu import BotMenu, navigation
from .work_queue import WorkQueue, queued_handler

CONFIGURE_HELP = """Exemplo de filtros
/configurar 1 50 5 1500
• 1: ID do monitoramento mostrado em /lista.
• 50: queda de pelo menos R$ 50,00 desde o último preço válido.
• 5: queda de pelo menos 5% desde o último preço válido.
• 1500: preço atual de até R$ 1.500,00.
O alerta exige TODAS essas condições juntas, na mesma oferta e modalidade.
Se o preço cair de R$ 1.600,00 para R$ 1.480,00, a queda será de R$ 120,00 (7,5%) e o alerta será enviado, se os dados forem comparáveis.
De R$ 1.600,00 para R$ 1.520,00, não haverá alerta: o preço ainda supera o alvo.

Exemplos de uso
/configurar 1 50 5 - — mantém as quedas mínimas, sem preço-alvo.
/configurar 1 0 0 1500 — sem queda mínima, mas só alerta em uma queda que termine em até R$ 1.500,00. Não avisa apenas por já estar abaixo do alvo.
/alertas 1 todas — volta a avisar aumentos e quedas, sem aplicar esses filtros.
/alertas 1 quedas — volta a aplicar os filtros às quedas.
/promocoes — economia comparada, de Maior que 5% até Maior que 80%.
/descontopromo >30 — alternativa aos botões; exatamente 30% não entra.
/tamanhopromo M — tamanho exato na busca Lacoste; use todos para ignorar.
Use ponto para centavos em /configurar: 50.90 significa R$ 50,90. Informe todos os valores, sem R$ ou separador de milhar.
"""

HELP = """🛍️ Ajuda

Use /menu para acessar os botões.

BUSCAS
/buscar nome — pesquisar preços.
/buscarml nome — pesquisar no Mercado Livre.
/promocoes — filtrar promoções por categoria e desconto.
/categorias — escolher uma categoria.
/categoria nome ou link — outra categoria.

MONITORAMENTO
/monitorar ID, nome ou link — iniciar acompanhamento.
/lista — ver seus monitoramentos.
/verificar ID — consultar agora.
/abrangencia ID todas — ampliar o mesmo monitoramento para outras lojas.
/intervalo ID MINUTOS — frequência deste monitoramento, de 15 a 1440 minutos.
/opcoes ID — escolher ofertas do monitoramento.
/confirmar OFERTA_ID — aprovar uma oferta.
/historico ID — ver preços registrados.
/pausar ID · /retomar ID · /remover ID
/alertas ID todas|quedas — escolher avisos.

Exemplo de filtros
/configurar 1 50 5 1500
Monitoramento 1: queda mínima de R$ 50 e 5%, até R$ 1.500.
Os três filtros precisam ser atendidos. Use - para retirar o preço-alvo.

/emprestimos — dinheiro emprestado e lembretes.
/status — versão e diagnóstico.
/lojas — acesso atual de cada loja e pausas por bloqueio.
/cep oito números — salvar CEP dos supermercados, inclusive após reiniciar.
/mercados — escolher localização e consultar sem exigir entrega ou somente com entrega.
/cancelar — sair da entrada atual.

Anúncio, oferta e monitoramento têm IDs diferentes. Use o ID solicitado.
Frete não incluído. Horários de Brasília."""


def main():
    config = Config.load()
    instance = InstanceLock(config.db)
    # Bibliotecas HTTP podem registrar URL do Telegram contendo token.
    logging.basicConfig(level=logging.CRITICAL)
    db = DB(config.db)
    from .grocery_profile import load_profile
    load_profile(db, config)
    fetcher = Fetcher(config)
    tasks = set()
    work = WorkQueue()

    async def send(text):
        await send_text(lambda t, **kw: app.bot.send_message(config.chat, t, **kw), text, reply_markup=navigation())

    async def send_candidate(candidate):
        await send_card(app.bot, config.chat, candidate)

    monitor = Monitor(
        db, config, fetcher, Search(config, fetcher), send, send_candidate
    )
    search_configuration_error = monitor.search.configuration_error()
    if search_configuration_error:
        print(search_error_message(search_configuration_error), flush=True)

    async def start(app):
        work.start()
        app.bot_data["scheduler"] = asyncio.create_task(monitor.scheduler(work.run))
        app.bot_data['loans_scheduler'] = asyncio.create_task(ui.loans.loans.scheduler(send, work.run))
        try:
            await app.bot.set_my_commands([
                BotCommand('menu','Abrir menu de botões'), BotCommand('promocoes','Promoções por categoria'),
                BotCommand('buscar','Buscar produto'), BotCommand('lista','Meus monitoramentos'),
                BotCommand('mercados','Localização e entrega dos supermercados'),
                BotCommand('emprestimos','Dinheiro emprestado e lembretes'),
                BotCommand('ajuda','Comandos e exemplos'), BotCommand('cancelar','Sair da entrada atual'),
            ],scope=BotCommandScopeChat(config.chat))
        except Exception:
            pass  # O menu inline continua funcionando sem o atalho nativo.

    async def stop(app):
        running = list(tasks) + [app.bot_data["scheduler"], app.bot_data['loans_scheduler']]
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)
        await work.close()
        snapshots = list(monitor.snapshot_inflight.values())
        for task in snapshots:
            task.cancel()
        await asyncio.gather(*snapshots, return_exceptions=True)
        await fetcher.close()
        db.conn.close()

    app = (
        Application.builder()
        .token(config.token)
        .concurrent_updates(16)
        .post_init(start)
        .post_stop(stop)
        .build()
    )

    def background(coro):
        task = work.submit(lambda: coro, cleanup=coro.close)
        tasks.add(task)

        def done(completed):
            tasks.discard(completed)
            if not completed.cancelled():
                completed.exception()  # Consumir falhas sem imprimir objetos que podem conter tokens.

        task.add_done_callback(done)

    async def send_promotion(text):
        await send(text)

    promotions = PromotionsTelegram(config, Deals(monitor), send_promotion, background)

    async def check_send(pid):
        try:
            await send(await monitor.check(pid))
        except Exception:
            await send('⚠️ Não foi possível concluir a verificação. Os dados válidos anteriores foram preservados.')

    async def command(update, context, name=None, args=None):
        if not authorized(update, config):
            return
        ui.remember(update)
        ui.clear()

        async def reply(text):
            await send_text(update.effective_message.reply_text, text, reply_markup=navigation())

        name = name or update.effective_message.text.split()[0].split("@")[0].lower()
        args = context.args if args is None else args
        try:
            if name in ('/start','/menu','/cancelar'):
                return await ui.home(update,context)
            if name == '/emprestimos':
                return await ui.loans.listing(update)
            if name == '/ajuda':
                error = monitor.search.configuration_error()
                return await reply(
                    f"Versão: {VERSION}\n"
                    + HELP
                    + ("\n\n" + search_error_message(error) if error else "")
                )
            if name == "/status":
                cep = getattr(config, 'grocery_postal_code', '')
                grocery_status = ('Supermercados: CEP ' + cep[:5] + '-' + cep[5:] + '.' if cep else
                                  'Supermercados: CEP não configurado; a busca pedirá a localização antes de consultar preços.')
                return await reply(
                    f'ℹ️ Status do bot\n\nVersão: {VERSION}\nBusca: {config.provider}\nChromium: {"ativado" if config.browser else "desativado"}\nPromoções: preços comparados e histórico observado.\nBusca padrão: {config.promotions_depth}.\nUse /lojas para conferir o acesso de cada loja.\nCAPTCHA e robots.txt continuam sendo respeitados.'
                    + '\n' + grocery_status
                )
            if name == '/lojas':
                from .store_status import store_status
                return await reply(store_status(fetcher, config.domains))
            if name == '/cep':
                from .grocery_profile import save_profile
                if not args:
                    value = getattr(config, 'grocery_postal_code', '')
                    return await reply('CEP dos supermercados: ' + (value or 'não configurado')
                                       + '. Para salvar: /cep oito números.')
                value = save_profile(db, config, ''.join(args))
                return await reply(f'📍 CEP {value} salvo. Será mantido após reiniciar.\n'
                                   'As próximas consultas usarão essa localização de referência. '
                                   'Use /mercados para escolher Posso ir à loja ou Preciso de entrega.')
            if name == '/mercados':
                from .grocery_profile import preferences
                return await preferences(update, config, db, ''.join(args) or None)
            if name == "/lista":
                return await ui.listing(update)
            if name in ("/monitorar", "/buscar", "/buscarml"):
                query = " ".join(args).strip()
                if not query or len(query) > 600:
                    return await reply('Informe um nome ou link com até 600 caracteres.')
                if name == "/monitorar" and query.isdigit():
                    return await ask_scope(app.bot, config.chat, db, int(query), config.interval)
                if "://" in query:
                    query, _ = fetcher.canonical(query)
                else:
                    error = monitor.search.configuration_error() if name != '/buscarml' else None
                    if error:
                        return await reply(
                            search_error_message(error)
                            + "\nNenhum novo cadastro foi criado."
                        )

                if name != '/buscarml' and await ui.require_grocery_region(update, query, name):
                    return

                async def search_send():
                    await deliver_search(
                        monitor, fetcher, db, app.bot, config.chat, query, send,
                        marketplace_only=name == '/buscarml'
                    )

                await reply('🔎 Pesquisando links do Mercado Livre...' if name == '/buscarml' else '🔎 Consultando as páginas das ofertas...')
                background(search_send())
                return
            if not args:
                return await reply('Informe um ID. Consulte os comandos disponíveis em /ajuda.')
            pid = int(args[0])
            if name == "/confirmar":
                candidate = db.confirm_candidate(pid)
                if candidate is None:
                    return await reply(
                        'Oferta não encontrada ou ainda sem título lido. Execute /verificar PRODUTO_ID e tente novamente.'
                    )
                await reply(
                    "✅ Modelo confirmado\n"
                    + candidate["title"]
                    + "\n\nA próxima leitura válida registrará o preço inicial."
                )
                background(check_send(candidate["product"]))
                return
            products = db.rows("SELECT * FROM products WHERE id=?", (pid,))
            if not products:
                return await reply('Produto não encontrado. Confira o ID e tente novamente.')
            if name == "/opcoes":
                if not await monitor.options(pid):
                    await reply(
                        'Não há ofertas pendentes de escolha. Use /verificar ID para buscar novamente.'
                    )
            elif name == "/verificar":
                await reply(f'🔎 Verificação do monitoramento {pid} iniciada. Avisarei quando a consulta terminar.')
                background(check_send(pid))
            elif name == '/abrangencia':
                if len(args) != 2 or args[1].lower() != 'todas':
                    return await reply('Use /abrangencia ID todas. O mesmo modelo será procurado nas lojas habilitadas.')
                status, target = db.expand_monitor(pid)
                if status == 'existing':
                    return await reply(f'O monitoramento {target} já acompanha esse anúncio em outras lojas. Nenhum histórico foi alterado. Consulte /lista.')
                if status == 'seed_missing':
                    return await reply('Falta o anúncio de origem para preservar o modelo exato. Busque o produto e escolha Outras lojas também no anúncio correto.')
                await reply(f'🔔 Monitoramento {pid}: mesmo modelo nas lojas habilitadas.\n'
                            'ID, histórico, ofertas confirmadas e filtros preservados.\n'
                            'Novas ofertas só entram nas comparações quando a identidade for confirmada. '
                            'Bloqueios ou dados insuficientes serão informados; não há garantia de acesso a toda loja.')
                if products[0]['active']:
                    background(check_send(pid))
            elif name == '/intervalo':
                if len(args) != 2:
                    return await reply('Use /intervalo ID MINUTOS. Exemplo: /intervalo 10 30.')
                minutes = float(args[1].replace(',', '.'))
                if not 15 <= minutes <= 1440:
                    return await reply('Escolha entre 15 e 1440 minutos. A consulta também depende da fila e dos limites das lojas.')
                from time import time
                next_limit = time() + minutes * 60
                db.run('UPDATE products SET interval_seconds=?,next_due=CASE WHEN active=1 AND next_due>? THEN ? ELSE next_due END WHERE id=?',
                       (minutes * 60, next_limit, next_limit, pid))
                await reply(f'Consultas do monitoramento {pid} configuradas a cada {minutes:g} minutos.\n'
                            'O aviso ocorre após uma consulta confirmar mudança comparável; não é detecção em tempo real.')
            elif name == "/pausar":
                db.run("UPDATE products SET active=0 WHERE id=?", (pid,))
                await reply(
                    '⏸️ Monitoramento pausado. Uma leitura já iniciada ainda pode terminar; os alertas ficam suspensos.'
                )
            elif name == "/retomar":
                db.run("UPDATE products SET active=1,next_due=0 WHERE id=?", (pid,))
                await reply('▶️ Monitoramento retomado. Uma consulta foi agendada.')
            elif name == "/remover":
                ui.forget(pid)
                db.run("DELETE FROM products WHERE id=?", (pid,))
                await reply('🗑️ Produto, histórico e alertas associados foram removidos.')
            elif name == "/alertas":
                if len(args) != 2 or args[1].lower() not in ("todas", "quedas"):
                    return await reply('Use: /alertas ID todas ou /alertas ID quedas.')
                mode = "all" if args[1].lower() == "todas" else "drops"
                db.run("UPDATE products SET alert_mode=? WHERE id=?", (mode, pid))
                await reply(
                    '🔔 Alertas de aumentos e quedas ativados.'
                    if mode == "all"
                    else '📉 Alertas somente para quedas ativados, respeitando os filtros configurados.'
                )
            elif name == "/configurar":
                from decimal import Decimal

                if len(args) != 4:
                    return await reply(
                        'Use: /configurar ID reais porcentagem alvo (ou - para remover o alvo).\n\n' + CONFIGURE_HELP
                    )
                minimum, percent = Decimal(args[1]), Decimal(args[2])
                target = None if args[3] == "-" else Decimal(args[3])
                values = [minimum, percent] + ([] if target is None else [target])
                if any(not v.is_finite() or v < 0 for v in values):
                    raise ValueError()
                db.run(
                    "UPDATE products SET minimum=?,percent=?,target=?,alert_mode='drops' WHERE id=?",
                    (
                        int(minimum * 100),
                        str(percent),
                        None if target is None else int(target * 100),
                        pid,
                    ),
                )
                await reply(
                    '✅ Filtros atualizados. O modo de alertas está definido como somente quedas. Para receber avisos de qualquer alteração, use /alertas ID todas.'
                )
            elif name == "/historico":
                rows = db.rows(
                    """SELECT h.at,h.status,h.detail,c.id AS cid FROM checks h JOIN candidates c ON c.id=h.candidate
                    WHERE c.product=? ORDER BY h.id DESC LIMIT 30""",
                    (pid,),
                )
                import json

                lines = []
                for r in rows:
                    when = datetime.fromtimestamp(
                        r["at"], ZoneInfo("America/Sao_Paulo")
                    ).isoformat(timespec="seconds")
                    detail = json.loads(r["detail"]) if r["detail"] else {}
                    lines.append(
                        f"🕒 {when}\nOferta {r['cid']} · Status: {r['status']}\nDetalhes: {detail}\n"
                    )
                for s in db.rows(
                    "SELECT s.* FROM series s JOIN candidates c ON c.id=s.candidate WHERE c.product=?",
                    (pid,),
                ):
                    lines.append(
                        f"📊 Oferta {s['candidate']}\nVendedor: {s['seller']} · Condição: {s['condition']}\nPagamento: {s['payment']}\nÚltimo preço: R$ {s['last']/100:.2f} · Menor registrado: R$ {s['lowest']/100:.2f}\n"
                    )
                await reply("\n".join(lines) or 'Ainda não há histórico para este produto.')
        except Exception:
            await reply(
                '⚠️ Comando ou configuração inválida. Consulte /ajuda. Uma falha de leitura nunca é tratada como preço zero.'
            )

    ui = BotMenu(config, db, promotions, command, CONFIGURE_HELP)
    promotions.prompt_input = ui.prompt_promotion

    async def promotion_command(update, context):
        if not authorized(update,config):
            return
        ui.remember(update)
        ui.clear()
        await promotions.command(update,context)

    async def promotion_callback(update, context):
        if authorized(update,config):
            ui.clear()
        await promotions.callback(update,context)

    for name in ('promocoes', 'categoria', 'categorias', 'descontopromo', 'ceppromo', 'tamanhopromo'):
        app.add_handler(CommandHandler(name, queued_handler(work,promotion_command,config)))
    app.add_handler(CallbackQueryHandler(queued_handler(work,promotion_callback,config), pattern=r'^promo:'))
    app.add_handler(CallbackQueryHandler(queued_handler(work,ui.callback,config), pattern=r'^ui:'))
    async def grocery_callback(update, context):
        from .grocery_profile import preferences
        if authorized(update, config):
            if (update.callback_query.data or '') == 'grocery:cep':
                await update.callback_query.answer()
                return await ui.prompt(update, 'grocerycep')
            ui.clear()
        await preferences(update, config, db)
    app.add_handler(CallbackQueryHandler(queued_handler(work,grocery_callback,config), pattern=r'^grocery:'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,queued_handler(work,ui.text,config)))

    for name in (
        "start",
        "menu",
        "emprestimos",
        "cancelar",
        "ajuda",
        "status",
        "lojas",
        "cep",
        "mercados",
        "buscar",
        "buscarml",
        "monitorar",
        "lista",
        "opcoes",
        "historico",
        "pausar",
        "retomar",
        "remover",
        "verificar",
        "abrangencia",
        "intervalo",
        "confirmar",
        "configurar",
        "alertas",
    ):
        app.add_handler(CommandHandler(name, queued_handler(work,command,config)))

    async def choose(update, context):
        await handle_choice(
            update, config, db, send, lambda pid: background(check_send(pid))
        )

    app.add_handler(CallbackQueryHandler(queued_handler(work,choose,config), pattern=r"^choose:"))

    async def subscription(update, context):
        await handle_subscription(
            update, config, db, app.bot, send, lambda pid: background(check_send(pid))
        )

    app.add_handler(CallbackQueryHandler(queued_handler(work,subscription,config), pattern=r"^(?:watch|scope):"))

    async def error_handler(update, context):
        # Excecoes omitidas intencionalmente para nao expor credenciais.
        pass

    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=False)
    instance.close()


if __name__ == "__main__":
    main()
