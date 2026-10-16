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
from .deals.service import Deals
from .deals.telegram import PromotionsTelegram
from .telegram_text import send_text

HELP = """🛍️ Bot de ofertas e monitoramento

BUSCAS
/buscar nome — buscar ofertas com ID, fotos e medalhas. Não ativa acompanhamento.
/buscarml nome — encontrar links do Mercado Livre. Resultados ainda não verificados serão identificados.
/promocoes — busca pontual por categoria, desconto e lojas. Não cria acompanhamento.
/categoria nome ou https://link — procurar qualquer tema ou usar uma página de categoria da loja.
/categorias — navegar por departamentos e subcategorias; /categorias atualizar relê os menus das lojas.
/descontopromo >=30 — informar percentual personalizado na etapa de desconto.
/ceppromo 01001000 — informar o CEP da consulta. O frete ainda não é cotado.

MONITORAMENTO
/monitorar ID_DO_ANUNCIO — escolher entre acompanhar só esta oferta ou procurar o mesmo produto em outras lojas.
/monitorar nome ou https://link — procurar anúncios para você escolher.
/lista — ver produtos, status e ofertas pendentes.
/opcoes PRODUTO_ID — reenviar ofertas candidatas com foto e botão de escolha.
/confirmar OFERTA_ID — confirmar exatamente o título e o link exibidos.
/historico ID — ver as últimas 30 leituras e os menores preços por modalidade.
/pausar ID — interromper o acompanhamento.
/retomar ID — reativar e agendar uma consulta imediata.
/remover ID — excluir o produto, o histórico e os alertas associados.
/verificar ID — consultar agora, mesmo se estiver pausado.
/configurar ID reais porcentagem alvo — definir filtros por produto; use - para remover o alvo.
/alertas ID todas|quedas — avisar sobre qualquer alteração ou somente sobre quedas que atendam aos filtros.

Exemplo de filtros
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
/descontopromo >30 — exclui exatamente 30%; aceita, por exemplo, 31%.
/descontopromo >=30 — inclui exatamente 30%. Use na etapa de desconto de /promocoes.
Use ponto para centavos em /configurar: 50.90 significa R$ 50,90. Informe todos os valores, sem R$ ou separador de milhar.

/status — ver a versão instalada e o modo de acesso às lojas.

Observações
• A busca padrão consulta diretamente as lojas, sem chave de API.
• Os horários seguem America/Sao_Paulo.
• O frete não está incluído.
• Os monitoramentos não expiram. Por padrão, há avisos de aumentos e quedas quando os dados permitem comparação.
• ID de anúncio, ID de oferta e ID de monitoramento são diferentes. Confira qual ID cada mensagem solicita.
• Antes de confirmar uma oferta, confira o modelo, a variante e o link."""


CONFIGURE_HELP = 'Exemplo de filtros\n' + HELP.split('Exemplo de filtros\n', 1)[1].split('\n/status', 1)[0]


def main():
    config = Config.load()
    instance = InstanceLock(config.db)
    # Bibliotecas HTTP podem registrar URL do Telegram contendo token.
    logging.basicConfig(level=logging.CRITICAL)
    db = DB(config.db)
    fetcher = Fetcher(config)
    tasks = set()

    async def send(text):
        await send_text(lambda t, **kw: app.bot.send_message(config.chat, t, **kw), text)

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
        task = asyncio.create_task(coro)
        tasks.add(task)

        def done(completed):
            tasks.discard(completed)
            if not completed.cancelled():
                completed.exception()  # Consumir falhas sem imprimir objetos que podem conter tokens.

        task.add_done_callback(done)

    async def send_promotion(text):
        await send(text)

    promotions = PromotionsTelegram(config, Deals(monitor), send_promotion, background)
    for name in ('promocoes', 'categoria', 'categorias', 'descontopromo', 'ceppromo'):
        app.add_handler(CommandHandler(name, promotions.command))
    app.add_handler(CallbackQueryHandler(promotions.callback, pattern=r'^promo:'))

    async def check_send(pid):
        try:
            await send(await monitor.check(pid))
        except Exception:
            await send('⚠️ Não foi possível concluir a verificação. Os dados válidos anteriores foram preservados.')

    async def command(update, context):
        if not authorized(update, config):
            return

        async def reply(text):
            await send_text(update.effective_message.reply_text, text)

        name = update.effective_message.text.split()[0].split("@")[0].lower()
        args = context.args
        try:
            if name in ("/ajuda", "/start"):
                error = monitor.search.configuration_error()
                return await reply(
                    f"Versão: {VERSION}\n"
                    + HELP
                    + ("\n\n" + search_error_message(error) if error else "")
                )
            if name == "/status":
                return await reply(
                    f'ℹ️ Status do bot\n\nVersão: {VERSION}\nBusca: {config.provider}\nChromium: {"ativado" if config.browser else "desativado"}\nPichau/Terabyte: descoberta por sitemaps.\nPreço e estoque são conferidos na página da oferta. CAPTCHA e robots.txt continuam sendo respeitados.'
                )
            if name == "/lista":
                rows = db.rows("SELECT * FROM products ORDER BY id")
                lines = []
                for p in rows:
                    lines.append(
                        f"🔔 Monitoramento {p['id']} — {p['query']}\nStatus: {'ativo' if p['active'] else 'pausado'}\nAnúncio de referência: {p['seed_ad'] or 'legado'}\nAbrangência: {p['scope']}\nAlertas: {p['alert_mode']}\nPrazo: sem vencimento\nPróxima consulta: {datetime.fromtimestamp(p['next_due'],ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}\n"
                    )
                    for c in db.rows(
                        "SELECT * FROM candidates WHERE product=?", (p["id"],)
                    ):
                        last = db.rows(
                            "SELECT status FROM checks WHERE candidate=? ORDER BY id DESC LIMIT 1",
                            (c["id"],),
                        )
                        lines.append(
                            f"  🏷️ Anúncio {c['ad_id'] or 'pendente'} · Oferta {c['id']}\n  Confirmação: {'confirmada' if c['confirmed'] else 'aguardando confirmação'}\n  Produto: {c['title']}\n  Última leitura: {last[0]['status'] if last else 'pendente'}\n  {c['url']}\n"
                        )
                return await reply("\n".join(lines) or 'Sua lista ainda está vazia. Use /buscar nome ou /monitorar nome para começar.')
            if name in ("/monitorar", "/buscar", "/buscarml"):
                query = " ".join(args).strip()
                if not query or len(query) > 600:
                    return await reply('Informe um nome ou link com até 600 caracteres.')
                if name == "/monitorar" and query.isdigit():
                    return await ask_scope(app.bot, config.chat, db, int(query))
                if "://" in query:
                    query, _ = fetcher.canonical(query)
                else:
                    error = monitor.search.configuration_error() if name != '/buscarml' else None
                    if error:
                        return await reply(
                            search_error_message(error)
                            + "\nNenhum novo cadastro foi criado."
                        )

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
                await reply('🔎 Verificação solicitada. Avisarei quando a consulta terminar.')
                background(check_send(pid))
            elif name == "/pausar":
                db.run("UPDATE products SET active=0 WHERE id=?", (pid,))
                await reply(
                    '⏸️ Monitoramento pausado. Uma leitura já iniciada ainda pode terminar; os alertas ficam suspensos.'
                )
            elif name == "/retomar":
                db.run("UPDATE products SET active=1,next_due=0 WHERE id=?", (pid,))
                await reply('▶️ Monitoramento retomado. Uma consulta foi agendada.')
            elif name == "/remover":
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

    for name in (
        "start",
        "ajuda",
        "status",
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
