import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
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

HELP = """/buscar nome - encontrar anuncios com ID, fotos e medalhas (sem ativar acompanhamento)
/monitorar ID_DO_ANUNCIO - escolher so esta oferta ou outras lojas
/monitorar nome ou https://link - procurar anuncios para escolher
/lista - produtos, status e ofertas pendentes
/opcoes PRODUTO_ID - reenviar candidatos com foto e botao de escolha
/confirmar OFERTA_ID - aprovar exatamente o titulo e link exibidos
/historico PRODUTO_ID - ultimas 30 leituras e menores precos por modalidade
/pausar ID - interromper acompanhamento
/retomar ID - reativar e agendar consulta imediata
/remover ID - excluir produto, historico e alertas
/verificar ID - consultar agora, mesmo pausado
/configurar ID reais porcentagem alvo - filtros por produto; use - para remover alvo
/alertas ID todas|quedas - avisar qualquer alteracao ou somente quedas filtradas
Ex.: /configurar 1 50 5 1500 (reais E percentual E alvo)
/ajuda - comandos
/status - versao instalada e modo de acesso das lojas
Busca padrao: diretamente nas lojas, sem chave de API.
Todos os horarios usam America/Sao_Paulo. Frete nao incluido.
Monitoramentos nao expiram. Avisos padrao para aumentos e quedas, com dados comparaveis.
IDs de anuncio, oferta e monitoramento sao diferentes; cada mensagem indica qual usar.
Confirme ofertas somente apos conferir modelo, variante e link."""


async def chunks(send, text):
    # Texto simples: nomes de lojas nao injetam Markdown/HTML.
    for start in range(0, len(text), 3800):
        await send(text[start : start + 3800])


def main():
    config = Config.load()
    instance = InstanceLock(config.db)
    # Bibliotecas HTTP podem registrar URL do Telegram contendo token.
    logging.basicConfig(level=logging.CRITICAL)
    db = DB(config.db)
    fetcher = Fetcher(config)
    tasks = set()

    async def send(text):
        await chunks(lambda t: app.bot.send_message(config.chat, t), text)

    async def send_candidate(candidate):
        await send_card(app.bot, config.chat, candidate)

    monitor = Monitor(
        db, config, fetcher, Search(config, fetcher), send, send_candidate
    )
    search_configuration_error = monitor.search.configuration_error()
    if search_configuration_error:
        print(search_error_message(search_configuration_error), flush=True)

    async def start(app):
        app.bot_data["scheduler"] = asyncio.create_task(monitor.scheduler())

    async def stop(app):
        running = list(tasks) + [app.bot_data["scheduler"]]
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)
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
        task = asyncio.create_task(coro)
        tasks.add(task)

        def done(completed):
            tasks.discard(completed)
            if not completed.cancelled():
                completed.exception()  # Consumir falhas sem imprimir objetos que podem conter tokens.

        task.add_done_callback(done)

    async def check_send(pid):
        try:
            await send(await monitor.check(pid))
        except Exception:
            await send("Falha na verificacao. Dados validos anteriores preservados.")

    async def command(update, context):
        if not authorized(update, config):
            return

        async def reply(text):
            await chunks(update.effective_message.reply_text, text)

        name = update.effective_message.text.split()[0].split("@")[0].lower()
        args = context.args
        try:
            if name in ("/ajuda", "/start"):
                error = monitor.search.configuration_error()
                return await reply(
                    f"Versao: {VERSION}\n"
                    + HELP
                    + ("\n\n" + search_error_message(error) if error else "")
                )
            if name == "/status":
                return await reply(
                    f'Versao: {VERSION}\nBusca: {config.provider}\nChromium: {"ativado" if config.browser else "desativado"}\nPichau/Terabyte: descoberta por sitemaps.\nPreco e estoque conferidos na oferta; CAPTCHA e robots.txt continuam respeitados.'
                )
            if name == "/lista":
                rows = db.rows("SELECT * FROM products ORDER BY id")
                lines = []
                for p in rows:
                    lines.append(
                        f"Monitoramento {p['id']} | Anuncio {p['seed_ad'] or 'legado'}: {p['query']} | {'ativo' if p['active'] else 'pausado'} | abrangencia: {p['scope']} | alertas: {p['alert_mode']} | sem vencimento | proxima: {datetime.fromtimestamp(p['next_due'],ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}"
                    )
                    for c in db.rows(
                        "SELECT * FROM candidates WHERE product=?", (p["id"],)
                    ):
                        last = db.rows(
                            "SELECT status FROM checks WHERE candidate=? ORDER BY id DESC LIMIT 1",
                            (c["id"],),
                        )
                        lines.append(
                            f"  Anuncio {c['ad_id'] or 'pendente'} | Oferta {c['id']}: {'confirmada' if c['confirmed'] else 'aguarda confirmacao'} | {c['title']} | ultima leitura: {last[0]['status'] if last else 'pendente'}\n{c['url']}"
                        )
                return await reply("\n".join(lines) or "Nenhum produto.")
            if name in ("/monitorar", "/buscar"):
                query = " ".join(args).strip()
                if not query or len(query) > 600:
                    return await reply("Informe um nome ou link (ate 600 caracteres).")
                if name == "/monitorar" and query.isdigit():
                    return await ask_scope(app.bot, config.chat, db, int(query))
                if "://" in query:
                    query, _ = fetcher.canonical(query)
                else:
                    error = monitor.search.configuration_error()
                    if error:
                        return await reply(
                            search_error_message(error)
                            + "\nNenhum novo cadastro foi criado."
                        )

                async def search_send():
                    await deliver_search(
                        monitor, fetcher, db, app.bot, config.chat, query, send
                    )

                await reply("Consultando paginas das ofertas...")
                background(search_send())
                return
            if not args:
                return await reply("Informe um ID. Veja /ajuda.")
            pid = int(args[0])
            if name == "/confirmar":
                candidate = db.confirm_candidate(pid)
                if candidate is None:
                    return await reply(
                        "Oferta inexistente ou sem titulo lido. Execute /verificar PRODUTO_ID."
                    )
                await reply(
                    "Modelo confirmado: "
                    + candidate["title"]
                    + "\nA proxima leitura valida registra a base inicial."
                )
                background(check_send(candidate["product"]))
                return
            products = db.rows("SELECT * FROM products WHERE id=?", (pid,))
            if not products:
                return await reply("Produto nao encontrado.")
            if name == "/opcoes":
                if not await monitor.options(pid):
                    await reply(
                        "Nenhuma oferta pendente de escolha. Use /verificar ID para buscar novamente."
                    )
            elif name == "/verificar":
                await reply("Verificacao solicitada.")
                background(check_send(pid))
            elif name == "/pausar":
                db.run("UPDATE products SET active=0 WHERE id=?", (pid,))
                await reply(
                    "Pausado. Uma leitura ja iniciada pode terminar; alertas ficam suspensos."
                )
            elif name == "/retomar":
                db.run("UPDATE products SET active=1,next_due=0 WHERE id=?", (pid,))
                await reply("Retomado; consulta agendada.")
            elif name == "/remover":
                db.run("DELETE FROM products WHERE id=?", (pid,))
                await reply("Produto e dados associados removidos.")
            elif name == "/alertas":
                if len(args) != 2 or args[1].lower() not in ("todas", "quedas"):
                    return await reply("Use /alertas ID todas ou /alertas ID quedas.")
                mode = "all" if args[1].lower() == "todas" else "drops"
                db.run("UPDATE products SET alert_mode=? WHERE id=?", (mode, pid))
                await reply(
                    "Avisos de aumentos e quedas ativados."
                    if mode == "all"
                    else "Avisos somente de quedas, respeitando os filtros."
                )
            elif name == "/configurar":
                from decimal import Decimal

                if len(args) != 4:
                    return await reply(
                        "Use /configurar ID reais porcentagem alvo (ou -)."
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
                    "Filtros atualizados; modo somente quedas ativado. Use /alertas ID todas para voltar a qualquer alteracao."
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
                        f"{when} | oferta {r['cid']} | {r['status']} | {detail}"
                    )
                for s in db.rows(
                    "SELECT s.* FROM series s JOIN candidates c ON c.id=s.candidate WHERE c.product=?",
                    (pid,),
                ):
                    lines.append(
                        f"Oferta {s['candidate']} | {s['seller']} | {s['condition']} | {s['payment']} | ultimo R$ {s['last']/100:.2f}; menor R$ {s['lowest']/100:.2f}"
                    )
                await reply("\n".join(lines) or "Sem historico.")
        except Exception:
            await reply(
                "Comando ou configuracao invalida. Consulte /ajuda; nenhum erro de leitura representa preco zero."
            )

    for name in (
        "start",
        "ajuda",
        "status",
        "buscar",
        "monitorar",
        "lista",
        "opcoes",
        "historico",
        "pausar",
        "retomar",
        "remover",
        "verificar",
        "confirmar",
        "configurar",
        "alertas",
    ):
        app.add_handler(CommandHandler(name, command))

    async def choose(update, context):
        await handle_choice(
            update, config, db, send, lambda pid: background(check_send(pid))
        )

    app.add_handler(CallbackQueryHandler(choose, pattern=r"^choose:"))

    async def subscription(update, context):
        await handle_subscription(
            update, config, db, app.bot, send, lambda pid: background(check_send(pid))
        )

    app.add_handler(CallbackQueryHandler(subscription, pattern=r"^(?:watch|scope):"))

    async def error_handler(update, context):
        # Excecoes omitidas intencionalmente para nao expor credenciais.
        pass

    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=False)
    instance.close()


if __name__ == "__main__":
    main()
