import asyncio
import time
from .adapters import adapter
from .adapters.base import ReadError
from .search import search_error_message
from .models import Reading, normalize
from .identity import same_product, monitoring_search_terms
from .message_style import short_reason, summarize_notices
from .discovery import REASONS, reading_relevance
import json


class Monitor:
    def __init__(self, db, config, fetcher, search, send, send_candidate=None):
        self.db, self.config, self.fetcher, self.search, self.send = (
            db,
            config,
            fetcher,
            search,
            send,
        )
        self.locks = {}
        self.inflight = {}
        self.alert_lock = asyncio.Lock()
        self.send_candidate = send_candidate
        self.amazon_offers = None
        self.snapshot_inflight = {}

    async def options(self, pid, only_new=False):
        extra = " AND c.notified=0 AND p.active=1" if only_new else ""
        pending = self.db.rows(
            """SELECT c.*,p.query AS monitor_query FROM candidates c JOIN products p ON p.id=c.product
            WHERE c.product=? AND c.confirmed=0 AND c.title<>''"""
            + extra
            + " ORDER BY c.id",
            (pid,),
        )
        for candidate in pending:
            card = dict(candidate)
            card['notification_context'] = 'check' if only_new else 'requested'
            if self.send_candidate:
                await self.send_candidate(card)
            else:
                await self.send(
                    f"🔎 Oferta aguardando confirmação · Monitoramento {candidate['product']}\n"
                    f"Você acompanha: {candidate['monitor_query']}\n\n"
                    f"Esta oferta foi encontrada para esse monitoramento e aguarda sua escolha.\n"
                    f"Tipo de aviso: sugestão de oferta; nenhuma mudança de preço foi confirmada neste aviso.\n\n"
                    f"{candidate['title']}\n{candidate['url']}\n\n"
                    f"Para incluir no acompanhamento, use /confirmar {candidate['id']}. Você pode ignorar esta sugestão."
                )
            self.db.run(
                "UPDATE candidates SET notified=1 WHERE id=?", (candidate["id"],)
            )
        return len(pending)

    async def read(self, url):
        url, _ = self.fetcher.canonical(url)
        if url in self.inflight:
            return await asyncio.shield(self.inflight[url])
        task = asyncio.create_task(self._read(url))
        self.inflight[url] = task
        try:
            return await task
        finally:
            self.inflight.pop(url, None)

    async def _read(self, url):
        return (await self.read_snapshot(url))[0]

    async def read_snapshot(self, url):
        """Leituras e HTML da mesma consulta, sem gravar anuncios ou historico."""
        url, _ = self.fetcher.canonical(url)
        task = self.snapshot_inflight.get(url)
        if task is None:
            task = asyncio.create_task(self._load_snapshot(url))
            self.snapshot_inflight[url] = task
            def done(completed):
                if self.snapshot_inflight.get(url) is completed:
                    self.snapshot_inflight.pop(url, None)
                if not completed.cancelled():
                    completed.exception()
            task.add_done_callback(done)
        return await asyncio.shield(task)

    async def _load_snapshot(self, url):
        url, domain = self.fetcher.canonical(url)
        html, final = await self.fetcher.html(url)
        _, final_domain = self.fetcher.canonical(final)
        if final_domain != domain:
            raise ReadError("redirect_changed_store")
        parser = adapter(final_domain)
        try:
            readings = parser.parse(html, final)
            if final_domain == 'amazon.com.br' and all(r.price is None for r in readings):
                public_url = parser.public_offers_url(html, final)
                if public_url:
                    try:
                        fragment, fragment_url = await self.fetcher.html(public_url, isolated=True)
                        if fragment_url != public_url:
                            raise ReadError('redirect_changed_store')
                        public_readings, public_html = parser.offers_fragment(readings, fragment, final)
                        if any(r.price is not None for r in public_readings):
                            return public_readings, public_html, final
                    except ReadError as exc:
                        # Somente formato ausente/rota removida permite seguir
                        # para o navegador; recusas e limites sao preservados.
                        if str(exc) not in ('page_removed', 'amazon_offers_unavailable'):
                            raise
            if final_domain == 'amazon.com.br' and self.config.browser and all(r.price is None for r in readings):
                offers_url = parser.buying_options_url(html, final)
                if not offers_url and any(r.stock != 'out_of_stock' for r in readings):
                    offers_url = parser.hidden_price_panel_url(html, final)
                if parser.price_requires_cart(html) and not offers_url:
                    if any(r.starting_price is not None for r in readings):
                        return readings, html, final
                    raise ReadError('amazon_price_requires_cart')
                if offers_url:
                    from .amazon_offers import AmazonOffersReader
                    if self.amazon_offers is None:
                        self.amazon_offers = AmazonOffersReader(self.fetcher)
                    try:
                        panel_html = await self.amazon_offers.html(offers_url)
                        panel_readings = parser.parse(panel_html, final)
                        if {normalize(r.title) for r in panel_readings} != {normalize(r.title) for r in readings}:
                            raise ReadError('conflicting_product_title')
                        return parser.enrich_identifiers(panel_readings, readings[0].identifiers), panel_html, final
                    except ReadError as exc:
                        if (str(exc) in ('amazon_browser_start_failed', 'amazon_browser_crashed',
                                'selenium_not_installed', 'browser_not_installed', 'amazon_offers_panel_timeout')
                                and any(r.starting_price is not None for r in readings)):
                            return readings, html, final
                        raise
            return readings, html, final
        except ReadError as exc:
            if (
                self.config.browser
                and str(exc) == "structured_product_missing_or_ambiguous"
            ):
                html = await self.fetcher.render(final)
                return parser.parse(html, final), html, final
            raise

    async def check(self, pid):
        lock = self.locks.setdefault(pid, asyncio.Lock())
        if lock.locked():
            return '⏳ Já existe uma verificação em andamento para este produto.'
        async with lock:
            products = self.db.rows("SELECT * FROM products WHERE id=?", (pid,))
            if not products:
                return 'Produto não encontrado. Confira o ID e tente novamente.'
            p = products[0]
            seed_ad = self.db.get_ad(p["seed_ad"]) if p["seed_ad"] else None
            seed_reading = (
                Reading(**json.loads(seed_ad["reading"])) if seed_ad else None
            )
            notes = []
            query = monitoring_search_terms(seed_reading.title, seed_reading.identifiers) if seed_reading else monitoring_search_terms(p['query'])
            try:
                if p["query"].startswith("https://"):
                    urls = [p["query"]]
                else:
                    try:
                        urls = await self.search.links(query)
                        notes.extend(summarize_notices(getattr(urls, "notices", [])))
                    except ReadError as exc:
                        urls = []
                        notes.append(search_error_message(str(exc)))
                # O indice pode estar limitado; anuncios ja conhecidos ainda sao
                # candidatos. Nunca reaproveitar o preco salvo como leitura atual.
                if p['scope'] == 'all':
                    urls = list(urls)
                    reused = 0
                    per_domain = {}
                    for ad in self.db.rows('SELECT * FROM ads ORDER BY observed_at DESC LIMIT 300'):
                        if ad['url'] in urls:
                            continue
                        try:
                            _, domain = self.fetcher.canonical(ad['url'])
                            old = Reading(**json.loads(ad['reading']))
                        except (ReadError, ValueError, TypeError):
                            continue
                        relation = same_product(seed_reading, old) if seed_reading else None
                        if relation is False or (relation is None and not reading_relevance(query, old)):
                            continue
                        if per_domain.get(domain, 0) >= 6:
                            continue
                        urls.append(ad['url'])
                        per_domain[domain] = per_domain.get(domain, 0) + 1
                        reused += 1
                    if reused:
                        notes.append(f'🔗 {reused} link(s) compatível(is) recuperado(s) do banco. Preço e estoque serão lidos novamente nas lojas.')
                if seed_ad and seed_ad["url"] not in urls:
                    urls = list(urls) + [seed_ad["url"]]
                for url in urls:
                    _, domain = self.fetcher.canonical(url)
                    self.db.candidate(pid, url, adapter(domain).name)
                candidates = self.db.rows(
                    "SELECT * FROM candidates WHERE product=? ORDER BY id", (pid,)
                )
                if not candidates and not notes:
                    notes.append(
                        'Não encontramos ofertas nesta consulta. Tente um nome mais curto ou cadastre um link.'
                    )
                unavailable_stores = {}
                coverage = {}
                for candidate in candidates:
                    domain = None
                    try:
                        if not self.db.rows('SELECT id FROM candidates WHERE id=?', (candidate['id'],)):
                            continue
                        _, domain = self.fetcher.canonical(candidate['url'])
                        stats = coverage.setdefault(domain, {'read': 0, 'priced': set(), 'failed': 0, 'deferred': 0})
                        if domain in unavailable_stores:
                            stats['deferred'] += 1
                            unavailable_stores[domain]['count'] += 1
                            self.db.failure(candidate['id'], 'store_check_deferred')
                            continue
                        readings = await self.read(candidate["url"])
                        if not readings:
                            raise ReadError('structured_product_missing_or_ambiguous')
                        stats['read'] += 1
                        # Produto pode ter sido removido enquanto aguardava a rede.
                        current = self.db.rows(
                            "SELECT * FROM candidates WHERE id=?", (candidate["id"],)
                        )
                        if not current:
                            continue
                        for reading in readings:
                            if not seed_reading and not p['query'].startswith('https://') and not reading_relevance(p['query'], reading):
                                self.db.failure(candidate['id'], 'different_model')
                                notes.append(f"🔎 Oferta {candidate['id']} descartada: produto incompatível com o monitoramento.")
                                continue
                            relation = (
                                same_product(seed_reading, reading)
                                if seed_reading
                                else None
                            )
                            if relation is False:
                                self.db.failure(candidate["id"], "different_model")
                                notes.append(f"🔎 Oferta {candidate['id']} descartada: produto incompatível com o monitoramento.")
                                continue
                            ad = self.db.save_ad(
                                candidate["url"], candidate["store"], reading
                            )
                            self.db.run(
                                "UPDATE candidates SET ad_id=? WHERE id=?",
                                (ad["id"], candidate["id"]),
                            )
                            if (
                                p["scope"] == "all"
                                and relation is True
                                and not current[0]["confirmed"]
                            ):
                                self.db.run(
                                    "UPDATE candidates SET confirmed=1,title=? WHERE id=?",
                                    (reading.title, candidate["id"]),
                                )
                            fresh = self.db.rows(
                                "SELECT * FROM candidates WHERE id=?",
                                (candidate["id"],),
                            )[0]
                            info = self.db.record(fresh, reading)
                            if type(reading.price) is int and reading.price > 0:
                                stats['priced'].add(candidate['id'])
                            price = (
                                'R$ ' + f'{reading.price // 100:,}'.replace(',', '.') + f',{reading.price % 100:02d}'
                                if reading.price is not None
                                else 'Preço não lido'
                            )
                            stock = {'in_stock': 'Disponível segundo a página', 'out_of_stock': 'Indisponível', 'unknown': 'Não confirmado pela página'}.get(reading.stock, 'Não confirmado pela página')
                            if info.startswith('Preço atual:'):
                                info = 'Menor registrado:' + info.split('Menor registrado:', 1)[-1]
                            elif info.startswith('Nova oferta ou condição:'):
                                info = 'Preço inicial registrado.'
                            notes.append(f"🆔 Anúncio {ad['id']} · Oferta {candidate['id']}\n{reading.title}\n\n"
                                         f"🏪 {candidate['store']} · {price} · {reading.payment or 'pagamento não informado'}\n"
                                         f"{stock}\n{info}\n{candidate['url']}")
                    except Exception as exc:
                        if domain in coverage:
                            coverage[domain]['failed'] += 1
                        # Nunca colocar excecoes de bibliotecas/URLs com tokens em logs ou mensagens.
                        code = (
                            str(exc) if isinstance(exc, ReadError) else "reading_error"
                        )
                        if self.db.rows(
                            "SELECT id FROM candidates WHERE id=?", (candidate["id"],)
                        ):
                            self.db.failure(candidate["id"], code)
                        reason = REASONS.get(code, 'Não foi possível validar a leitura da página')
                        if domain is not None and code in ('blocked_no_bypass', 'captcha_no_bypass', 'domain_access_cooldown',
                                'robots_unavailable', 'robots_disallowed', 'rate_limit_deferred', 'store_rate_cooldown'):
                            unavailable_stores[domain] = {'store': candidate['store'], 'count': 1,
                                'reason': reason, 'url': candidate['url']}
                            continue
                        notes.append(
                            f"⚠️ Oferta {candidate['id']} — {candidate['store']}: {short_reason(reason)}.\n{candidate['url']}"
                        )
                for item in unavailable_stores.values():
                    notes.append(f"⚠️ {item['store']}: {short_reason(item['reason'])}.\n"
                        f"{item['count']} oferta(s) sem atualização. Preços anteriores preservados.\n{item['url']}")
                lines = ['🏪 Resumo por loja']
                for domain, stats in coverage.items():
                    if not stats['priced']:
                        continue
                    name = adapter(domain).name
                    line = f"{name}: {len(stats['priced'])} preço(s)"
                    if stats['failed']: line += f" · {stats['failed']} falha(s)"
                    if stats['deferred']: line += f" · {stats['deferred']} adiada(s)"
                    lines.append(line)
                if len(lines) > 1:
                    notes.append('\n'.join(lines))
                await self.options(pid, only_new=True)
                await self.deliver()
            finally:
                self.db.run(
                    "UPDATE products SET next_due=? WHERE id=?",
                    (time.time() + self.config.interval, pid),
                )
            return (f"🔎 Verificação do monitoramento {pid}\nVocê acompanha: {p['query'][:300]}\n\n"
                    + "\n\n".join(notes))

    async def deliver(self):
        async with self.alert_lock:
            rows = self.db.rows(
                """SELECT a.* FROM alerts a JOIN series s ON s.id=a.series
                JOIN candidates c ON c.id=s.candidate JOIN products p ON p.id=c.product
                WHERE a.sent_at IS NULL AND p.active=1 ORDER BY a.id"""
            )
            for row in rows:
                try:
                    await self.send(row["message"])
                except Exception:
                    break
                self.db.run(
                    "UPDATE alerts SET sent_at=? WHERE id=?", (time.time(), row["id"])
                )

    async def scheduler(self, runner=None):
        async def inline(factory):
            return await factory()
        run = runner or inline

        async def active_check(pid):
            # A situacao pode mudar enquanto o agendamento aguarda na fila.
            if self.db.rows('SELECT id FROM products WHERE id=? AND active=1', (pid,)):
                await self.check(pid)
        # next_due persistido: atrasados rodam uma vez ao reiniciar, sem tempestade de catch-up.
        while True:
            try:
                await run(self.deliver)
                due = self.db.rows(
                    "SELECT id FROM products WHERE active=1 AND next_due<=?",
                    (time.time(),),
                )
                # Sequencial entre produtos para limitar pressao nas lojas; comandos continuam assincronos.
                for row in due:
                    if self.db.rows(
                        "SELECT id FROM products WHERE id=? AND active=1", (row["id"],)
                    ):
                        await run(lambda pid=row['id']: active_check(pid))
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(15)
