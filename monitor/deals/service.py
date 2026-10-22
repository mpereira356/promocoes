"""Consulta manual limitada e sem qualquer dependencia de banco/agendador."""
import asyncio
import httpx
from copy import copy
from dataclasses import dataclass
from ..adapters.base import ReadError
from ..models import normalize
from ..search import Search
from ..network import PAGE_AUDIT
from ..discovery import REASONS
from .adapters import ADAPTERS
from .identity import model_relation, comparable
from .models import Coverage, DealResult, DealReport, valid_price, parse_size
from .catalog import CategoryCatalog, Category


@dataclass(frozen=True)
class Limits:
    category_pages: int = 2
    products_per_store: int = 12
    comparisons_per_store: int = 2
    category_sources: int = 12


class Deals:
    def __init__(self, monitor, limits=None):
        self.monitor = monitor
        self.fetcher = monitor.fetcher
        self.limits = limits or Limits()
        self.catalog = CategoryCatalog()
        if any(not 1 <= n <= 100 for n in vars(self.limits).values()):
            raise ValueError('Os limites devem estar entre 1 e 100.')
        self.lock = asyncio.Lock()

    async def run(self, category, discount, domains, cep='', size=''):
        size = parse_size(size) if size else ''
        domains = list(dict.fromkeys(domains))
        if isinstance(category, str):
            category = self.catalog.items.get(category)
        if not isinstance(category, Category) or not domains or any(d not in ADAPTERS or d not in self.monitor.config.domains for d in domains):
            raise ValueError('Esta categoria ou loja não está habilitada.')
        if self.lock.locked():
            raise ValueError('Já existe uma consulta de promoções em andamento.')
        for domain in domains:
            for _, url in self.catalog.sources(category, domain):
                if self.fetcher.canonical(url)[1] != domain:
                    raise ValueError('O link de categoria não corresponde à loja selecionada.')
        if cep and (len(cep) != 8 or not cep.isdigit()):
            raise ValueError('O CEP deve conter oito dígitos.')
        async with self.lock:
            return await self._run(category, discount, domains, cep, size)

    async def _run(self, category, discount, domains, cep, size):
        coverage = {d: Coverage(d, ADAPTERS[d].store) for d in domains}
        cache, pool = {}, []
        stopped = set()
        stop_reasons = {'blocked_no_bypass', 'captcha_no_bypass', 'domain_access_cooldown',
                        'rate_limit_deferred', 'store_rate_cooldown', 'robots_unavailable'}

        async def discover(domain, query):
            if domain in stopped:
                return []
            config = copy(self.monitor.config)
            config.domains = (domain,)
            audit = []
            token = PAGE_AUDIT.set(audit)
            try:
                urls = await Search(config, self.fetcher).links(query)
                coverage[domain].notices.extend(getattr(urls, 'notices', []))
                return list(urls)
            except (ReadError, ValueError, OSError, httpx.RequestError) as exc:
                reason = REASONS.get(str(exc), 'A busca complementar está indisponível')
                coverage[domain].notices.append(reason)
                coverage[domain].failed_pages += 1
                if str(exc) in stop_reasons:
                    stopped.add(domain)
                return []
            finally:
                PAGE_AUDIT.reset(token)
                documents = [e for e in audit if e['domain'] == domain]
                coverage[domain].discovery_pages += len(documents)
                coverage[domain].discovery_loaded += sum(e['ok'] for e in documents)

        async def read(url, domain, comparison=False):
            if domain in stopped:
                return []
            try:
                url, actual = self.fetcher.canonical(url)
                if actual != domain:
                    return []
                if url in cache:
                    return cache[url]
                cache[url] = []
                cov = coverage[domain]
                if domain == 'mercadolivre.com.br':
                    from ..adapters.mercadolivre import MercadoLivreAdapter
                    if not MercadoLivreAdapter().is_product_url(url):
                        cov.notices.append('Links de catálogo com vários vendedores foram descartados; não identificam uma oferta individual comparável.')
                        return []
                if comparison:
                    cov.comparison_pages += 1
                else:
                    cov.product_pages += 1
                readings, html, final = await self.monitor.read_snapshot(url)
                if self.fetcher.canonical(final)[1] != domain:
                    raise ReadError('redirect_changed_store')
                offers = [ADAPTERS[domain].offer(html, final, r) for r in readings]
                cache[url] = offers
                return offers
            except (ReadError, ValueError, TypeError, KeyError, OSError, httpx.RequestError) as exc:
                coverage[domain].failed_pages += 1
                if str(exc) in stop_reasons:
                    stopped.add(domain)
                reason = (REASONS.get(str(exc), 'Formato da oferta não reconhecido') if isinstance(exc, ReadError)
                    else 'Falha de conexão com a loja' if isinstance(exc, (OSError, httpx.RequestError))
                    else 'Formato da oferta não reconhecido')
                coverage[domain].notices.append(f'Falha na leitura da oferta: {reason}.\n{url}')
                return []

        async def category_links(source, start_url, domain, aggregate=False):
            store, cov = ADAPTERS[domain], coverage[domain]
            if getattr(store, 'catalog_discovery', '') == 'sitemap':
                from ..adapters import adapter
                from ..sitemaps import sitemap_candidates
                from ..discovery import relevance
                audit = []
                token = PAGE_AUDIT.set(audit)
                try:
                    candidates = await sitemap_candidates(adapter(domain), domain, self.fetcher)
                    root_terms = {
                        'hardware': {'placa', 'processador', 'memoria', 'ssd', 'hd', 'fonte', 'cooler', 'gabinete'},
                        'perifericos': {'mouse', 'teclado', 'headset', 'fone', 'webcam', 'mousepad'},
                    }
                    def score(candidate):
                        if source.key in root_terms:
                            return int(bool(set(normalize(candidate.title).split()) & root_terms[source.key]))
                        return relevance(source.search_query, candidate.title) if source.accepts_parent_title(candidate.title) else 0
                    matched = sorted(((score(c), c) for c in candidates), key=lambda pair: pair[0], reverse=True)
                    links = list(dict.fromkeys(c.url for score_value, c in matched if score_value))
                    if links:
                        cov.notices.append('Descoberta por sitemap público da loja; preços relidos nas páginas dos produtos.')
                        return links
                except ReadError as exc:
                    if str(exc) in stop_reasons or str(exc) == 'robots_disallowed':
                        cov.failed_pages += 1
                        stopped.add(domain)
                        cov.notices.append(REASONS.get(str(exc), 'Catálogo indisponível'))
                        return []
                except (OSError, httpx.RequestError):
                    cov.failed_pages += 1
                    cov.notices.append('Falha de conexão com o catálogo da loja.')
                    stopped.add(domain)
                    return []
                finally:
                    PAGE_AUDIT.reset(token)
                    documents = [e for e in audit if e['domain'] == domain]
                    cov.discovery_pages += len(documents)
                    cov.discovery_loaded += sum(e['ok'] for e in documents)
            url, visited, links = start_url, set(), []
            pages = 1 if aggregate else self.limits.category_pages
            for _ in range(pages):
                if not url or url in visited or domain in stopped:
                    break
                visited.add(url)
                cov.category_pages += 1
                try:
                    html, final = await self.fetcher.html(url)
                    if self.fetcher.canonical(final)[1] != domain:
                        raise ReadError('redirect_changed_store')
                    page = store.page(html, final)
                    links.extend(link for link in page.urls if link not in links)
                    if not page.urls:
                        cov.notices.append('Página de categoria sem links de produtos reconhecidos.')
                    nxt = page.next_url
                    if nxt:
                        canonical, target_domain = self.fetcher.canonical(nxt)
                        from urllib.parse import urlsplit
                        if target_domain != domain or urlsplit(canonical).path.rstrip('/') != urlsplit(final).path.rstrip('/'):
                            raise ReadError('pagination_outside_category')
                        nxt = canonical
                    url = nxt
                except (ReadError, ValueError, TypeError, KeyError, OSError, httpx.RequestError) as exc:
                    cov.failed_pages += 1
                    if str(exc) in stop_reasons:
                        stopped.add(domain)
                    safe = (REASONS.get(str(exc), 'Formato de categoria não reconhecido') if isinstance(exc, ReadError)
                            else 'Falha de conexão com a loja' if isinstance(exc, (OSError, httpx.RequestError))
                            else 'Formato da categoria não reconhecido')
                    cov.notices.append(source.title + ': ' + safe)
                    url = None
                    break
            if url and len(visited) >= pages:
                cov.notices.append(f'Limite de {pages} página(s) por categoria atingido.')
            return links

        for domain in domains:
            cov = coverage[domain]
            sources = self.catalog.sources(category, domain)
            groups = []
            if not sources:
                if not category.query:
                    cov.notices.append('Loja sem categoria mapeada para esta escolha; nenhuma busca genérica foi executada.')
                    continue
                cov.notices.append('Busca por termo "' + category.search_query + '"; cobertura parcial.')
                groups.append((category, list(dict.fromkeys(await discover(domain, category.search_query)))))
            else:
                if len(sources) > self.limits.category_sources:
                    cov.notices.append(f'Cobertura limitada a {self.limits.category_sources} de {len(sources)} categorias mapeadas.')
                for source, url in sources[:self.limits.category_sources]:
                    if domain in stopped:
                        break
                    cov.sources.append(source.title)
                    if domain not in source.urls:
                        cov.notices.append('Categoria geral da loja usada com filtro de produto: ' + source.search_query)
                    links = await category_links(source, url, domain, bool(category.children))
                    groups.append((source, links))
            # Share the product budget across subcategories instead of taking all
            # products from the first category in an aggregate selection.
            links, seen = [], set()
            for index in range(max((len(urls) for _, urls in groups), default=0)):
                for source, urls in groups:
                    if index < len(urls) and urls[index] not in seen:
                        seen.add(urls[index])
                        links.append((source, urls[index]))
            cov.discovered = len(links)
            if len(links) > self.limits.products_per_store:
                cov.notices.append(f'Leitura limitada a {self.limits.products_per_store} de {len(links)} produtos encontrados.')
            for source, link in links[:self.limits.products_per_store]:
                if domain in stopped:
                    break
                accepts = source.accepts_parent_title if domain not in source.urls and not source.query else source.accepts_title
                offers = [o for o in await read(link, domain) if accepts(o.reading.title)]
                pool.extend(offers)
                cov.priced += sum(valid_price(o.reading.price) for o in offers)
                cov.missing_reference += sum(not valid_price(o.previous) for o in offers)
                cov.unavailable += sum(o.reading.stock != 'in_stock' for o in offers)
                cov.qualifying += sum(eligible(o, discount) and (not size or size in o.available_sizes) for o in offers)
                if not any(eligible(o, discount) and (not size or size in o.available_sizes) for o in offers):
                    cov.excluded += 1

        qualified = select_offers([o for o in pool if not size or size in o.available_sizes], discount, limit=None)
        if size:
            for domain, cov in coverage.items():
                excluded = sum(o.domain == domain and size not in o.available_sizes for o in pool)
                cov.excluded += excluded
                cov.notices.append(f'Tamanho solicitado: {size}. {excluded} oferta(s) excluída(s) por falta de estoque confirmado nesse tamanho.')
        # Busca textual descobre candidatos; identidade forte valida a comparacao.
        for offer in (qualified[:3] if category.query else []):
            identifiers = offer.reading.identifiers
            query = ' '.join(filter(None, [identifiers.get('brand', ''), identifiers.get('mpn', '')]))
            if not identifiers.get('mpn'):
                query = offer.reading.title
            for domain in domains:
                if domain == offer.domain or domain in stopped or coverage[domain].comparison_pages >= self.limits.comparisons_per_store:
                    continue
                urls = await discover(domain, query)
                for url in urls[:self.limits.comparisons_per_store - coverage[domain].comparison_pages]:
                    pool.extend(await read(url, domain, comparison=True))

        comparable_pool = [o for o in pool if not size or size in o.available_sizes]
        results = [compare_offer(o, comparable_pool) for o in qualified[:3]]
        return DealReport(results, list(coverage.values()), discount, category.key, cep, True, pool, category.title, size)


def eligible(offer, discount):
    return (offer.reading.currency == 'BRL' and offer.reading.stock == 'in_stock'
            and discount.accepts(offer.previous, offer.reading.price))


def select_offers(pool, discount, limit=3):
    result = []
    for offer in sorted((o for o in pool if eligible(o, discount)), key=lambda o: o.ratio, reverse=True):
        # O mesmo titulo so serve para evitar duplicata; nunca confirma comparacao.
        if any(model_relation(offer, old) is True or
               (normalize(offer.reading.title) == normalize(old.reading.title)
                and offer.reading.identifiers.get('color', '') == old.reading.identifiers.get('color', '')
                and offer.reading.identifiers.get('size', '') == old.reading.identifiers.get('size', '')) for old in result):
            continue
        result.append(offer)
        if limit is not None and len(result) == limit:
            break
    return result


def compare_offer(offer, pool):
    others, seen = [], set()
    for candidate in sorted((p for p in pool if valid_price(p.reading.price)), key=lambda p: p.reading.price):
        if candidate.domain == offer.domain or candidate.domain in seen or not comparable(offer, candidate):
            continue
        seen.add(candidate.domain)
        others.append(candidate)
    if not others:
        return DealResult(offer, [offer], 'Comparação não confirmada')
    lowest = min([offer] + others, key=lambda o: o.reading.price)
    label = 'Foi encontrada uma oferta com preço menor' if lowest.reading.price < offer.reading.price else 'Menor preço encontrado'
    return DealResult(offer, [offer] + others[:2], label, lowest)
