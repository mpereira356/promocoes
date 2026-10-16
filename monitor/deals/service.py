"""Consulta manual limitada e sem qualquer dependencia de banco/agendador."""
import asyncio
from copy import copy
from dataclasses import dataclass
from ..adapters.base import ReadError
from ..models import normalize
from ..search import Search
from ..network import PAGE_AUDIT
from .adapters import ADAPTERS, CATEGORIES
from .identity import model_relation, comparable
from .models import Coverage, DealResult, DealReport, valid_price


@dataclass(frozen=True)
class Limits:
    category_pages: int = 2
    products_per_store: int = 12
    comparisons_per_store: int = 2


class Deals:
    def __init__(self, monitor, limits=None):
        self.monitor = monitor
        self.fetcher = monitor.fetcher
        self.limits = limits or Limits()
        if any(not 1 <= n <= 100 for n in vars(self.limits).values()):
            raise ValueError('Limites devem estar entre 1 e 100.')
        self.lock = asyncio.Lock()

    async def run(self, category, discount, domains, cep=''):
        domains = list(dict.fromkeys(domains))
        if category not in CATEGORIES or not domains or any(d not in ADAPTERS or d not in self.monitor.config.domains for d in domains):
            raise ValueError('Categoria ou loja nao habilitada.')
        if cep and (len(cep) != 8 or not cep.isdigit()):
            raise ValueError('CEP deve ter oito digitos.')
        if self.lock.locked():
            raise ValueError('Ja existe uma consulta de promocoes em andamento.')
        async with self.lock:
            return await self._run(category, discount, domains, cep)

    async def _run(self, category, discount, domains, cep):
        coverage = {d: Coverage(d, ADAPTERS[d].store) for d in domains}
        cache, pool = {}, []

        async def read(url, domain, comparison=False):
            try:
                url, actual = self.fetcher.canonical(url)
                if actual != domain:
                    return []
                if url in cache:
                    return cache[url]
                cache[url] = []
                cov = coverage[domain]
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
            except (ReadError, ValueError, TypeError, KeyError):
                coverage[domain].notices.append('Falha de leitura de oferta: ' + url)
                return []

        for domain in domains:
            store, cov = ADAPTERS[domain], coverage[domain]
            cov.notices.extend(store.limitations)
            if category not in store.categories:
                cov.notices.append('Categoria ainda nao mapeada nesta loja.')
                continue
            url, visited, links = store.category_url(category), set(), []
            for _ in range(self.limits.category_pages):
                if not url or url in visited:
                    break
                visited.add(url)
                cov.category_pages += 1  # Tentativas, inclusive paginas bloqueadas.
                try:
                    html, final = await self.fetcher.html(url)
                    if self.fetcher.canonical(final)[1] != domain:
                        raise ReadError('redirect_changed_store')
                    page = store.page(html, final)
                    for candidate in page.urls:
                        if candidate not in links:
                            links.append(candidate)
                    if not page.urls:
                        cov.notices.append('Nenhum link extraido: pagina vazia ou formato de categoria nao validado.')
                    nxt = page.next_url
                    if nxt:
                        canonical, target_domain = self.fetcher.canonical(nxt)
                        from urllib.parse import urlsplit
                        if target_domain != domain or urlsplit(canonical).path.rstrip('/') != urlsplit(final).path.rstrip('/'):
                            raise ReadError('pagination_outside_category')
                        nxt = canonical
                    url = nxt
                except (ReadError, ValueError, TypeError, KeyError) as exc:
                    safe = str(exc) if isinstance(exc, ReadError) else 'formato_nao_suportado'
                    cov.notices.append('Categoria nao consultada com sucesso: ' + safe)
                    url = None
                    break
            if url and len(visited) >= self.limits.category_pages:
                cov.notices.append(f'Limite de {self.limits.category_pages} paginas de categoria atingido.')
            cov.discovered = len(links)
            if len(links) > self.limits.products_per_store:
                cov.notices.append(f'Leitura limitada aos primeiros {self.limits.products_per_store} produtos descobertos.')
            for link in links[:self.limits.products_per_store]:
                offers = await read(link, domain)
                pool.extend(offers)
                if not any(eligible(o, discount) for o in offers):
                    cov.excluded += 1

        qualified = select_offers(pool, discount, limit=None)
        # Busca textual descobre candidatos; identidade forte valida a comparacao.
        for offer in qualified:
            identifiers = offer.reading.identifiers
            query = ' '.join(filter(None, [identifiers.get('brand', ''), identifiers.get('mpn', '')]))
            if not identifiers.get('mpn'):
                query = offer.reading.title
            for domain in domains:
                if domain == offer.domain:
                    continue
                config = copy(self.monitor.config)
                config.domains = (domain,)
                search = Search(config, self.fetcher)
                audit = []
                token = PAGE_AUDIT.set(audit)
                try:
                    urls = await search.links(query)
                    coverage[domain].notices.extend(getattr(urls, 'notices', []))
                    for url in list(urls)[:self.limits.comparisons_per_store]:
                        pool.extend(await read(url, domain, comparison=True))
                except (ReadError, ValueError):
                    coverage[domain].notices.append('Busca complementar indisponivel; comparacao parcial.')
                finally:
                    PAGE_AUDIT.reset(token)
                    # Ofertas ja sao contadas separadamente; contar aqui somente
                    # documentos usados para descobrir links, nao robots/retries.
                    product_urls = set(cache)
                    documents = [e for e in audit if e['domain'] == domain and e['url'] not in product_urls]
                    coverage[domain].discovery_pages += len(documents)
                    coverage[domain].discovery_loaded += sum(e['ok'] for e in documents)

        results = [compare_offer(o, pool) for o in qualified[:3]]
        return DealReport(results, list(coverage.values()), discount, category, cep, True, pool)


def eligible(offer, discount):
    return (offer.reading.currency == 'BRL' and offer.reading.stock == 'in_stock'
            and discount.accepts(offer.previous, offer.reading.price))


def select_offers(pool, discount, limit=3):
    result = []
    for offer in sorted((o for o in pool if eligible(o, discount)), key=lambda o: o.ratio, reverse=True):
        # O mesmo titulo so serve para evitar duplicata; nunca confirma comparacao.
        if any(model_relation(offer, old) is True or normalize(offer.reading.title) == normalize(old.reading.title) for old in result):
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
        return DealResult(offer, [offer], 'comparação não confirmada')
    lowest = min([offer] + others, key=lambda o: o.reading.price)
    label = 'existe oferta mais barata' if lowest.reading.price < offer.reading.price else 'menor preço encontrado'
    return DealResult(offer, [offer] + others[:2], label, lowest)
