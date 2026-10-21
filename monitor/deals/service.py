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
        for domain, url in category.urls.items():
            if domain in domains and self.fetcher.canonical(url)[1] != domain:
                raise ValueError('O link de categoria não corresponde à loja selecionada.')
        if cep and (len(cep) != 8 or not cep.isdigit()):
            raise ValueError('O CEP deve conter oito dígitos.')
        async with self.lock:
            return await self._run(category, discount, domains, cep, size)

    async def _run(self, category, discount, domains, cep, size):
        coverage = {d: Coverage(d, ADAPTERS[d].store) for d in domains}
        cache, pool = {}, []

        async def discover(domain, query):
            config = copy(self.monitor.config)
            config.domains = (domain,)
            audit = []
            token = PAGE_AUDIT.set(audit)
            try:
                urls = await Search(config, self.fetcher).links(query)
                coverage[domain].notices.extend(getattr(urls, 'notices', []))
                return list(urls)
            except (ReadError, ValueError, OSError, httpx.RequestError):
                coverage[domain].notices.append('A busca complementar está indisponível; a comparação será parcial.')
                return []
            finally:
                PAGE_AUDIT.reset(token)
                documents = [e for e in audit if e['domain'] == domain]
                coverage[domain].discovery_pages += len(documents)
                coverage[domain].discovery_loaded += sum(e['ok'] for e in documents)

        async def read(url, domain, comparison=False):
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
                reason = (REASONS.get(str(exc), 'Formato da oferta não reconhecido') if isinstance(exc, ReadError)
                    else 'Falha de conexão com a loja' if isinstance(exc, (OSError, httpx.RequestError))
                    else 'Formato da oferta não reconhecido')
                coverage[domain].notices.append(f'Falha na leitura da oferta: {reason}.\n{url}')
                return []

        parent_urls = self.catalog.parent_urls(category)
        for domain in domains:
            store, cov = ADAPTERS[domain], coverage[domain]
            cov.notices.extend(store.limitations)
            if domain not in category.urls and domain not in parent_urls:
                query = category.search_query
                cov.notices.append('Sem página de categoria mapeada nesta loja: busca por termo "' + query + '"; não representa varredura da categoria inteira.')
                links = list(dict.fromkeys(await discover(domain, query)))
                cov.discovered = len(links)
                if len(links) > self.limits.products_per_store:
                    cov.notices.append(f'A leitura foi limitada aos primeiros {self.limits.products_per_store} produtos encontrados.')
                for link in links[:self.limits.products_per_store]:
                    offers = await read(link, domain)
                    offers = [o for o in offers if category.accepts_title(o.reading.title)]
                    pool.extend(offers)
                    if not any(eligible(o, discount) for o in offers):
                        cov.excluded += 1
                continue
            if domain in parent_urls:
                cov.notices.append('Consultada a categoria geral de memória RAM; apenas produtos com ' + category.memory_type.upper() + ' explícito no título podem qualificar. Cobertura limitada.')
            url, visited, links = category.urls.get(domain) or parent_urls[domain], set(), []
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
                        cov.notices.append('Não foi possível extrair links: a página está vazia ou o formato da categoria ainda não foi validado.')
                    nxt = page.next_url
                    if nxt:
                        canonical, target_domain = self.fetcher.canonical(nxt)
                        from urllib.parse import urlsplit
                        if target_domain != domain or urlsplit(canonical).path.rstrip('/') != urlsplit(final).path.rstrip('/'):
                            raise ReadError('pagination_outside_category')
                        nxt = canonical
                    url = nxt
                except (ReadError, ValueError, TypeError, KeyError, OSError, httpx.RequestError) as exc:
                    safe = (REASONS.get(str(exc), 'A página não pôde ser lida com segurança') if isinstance(exc, ReadError)
                        else 'Falha de conexão com a loja' if isinstance(exc, (OSError, httpx.RequestError))
                        else 'Formato da categoria não reconhecido')
                    cov.notices.append('A categoria não pôde ser consultada com sucesso: ' + safe)
                    url = None
                    break
            if url and len(visited) >= self.limits.category_pages:
                cov.notices.append(f'Limite de {self.limits.category_pages} páginas de categoria atingido.')
            cov.discovered = len(links)
            if len(links) > self.limits.products_per_store:
                cov.notices.append(f'A leitura foi limitada aos primeiros {self.limits.products_per_store} produtos encontrados.')
            for link in links[:self.limits.products_per_store]:
                offers = await read(link, domain)
                offers = [o for o in offers if category.accepts_title(o.reading.title)]
                pool.extend(offers)
                if not any(eligible(o, discount) for o in offers):
                    cov.excluded += 1

        qualified = select_offers([o for o in pool if not size or size in o.available_sizes], discount, limit=None)
        if size:
            for domain, cov in coverage.items():
                excluded = sum(o.domain == domain and size not in o.available_sizes for o in pool)
                cov.excluded += excluded
                cov.notices.append(f'Tamanho solicitado: {size}. {excluded} oferta(s) excluída(s) por falta de estoque confirmado nesse tamanho.')
        # Busca textual descobre candidatos; identidade forte valida a comparacao.
        for offer in qualified:
            identifiers = offer.reading.identifiers
            query = ' '.join(filter(None, [identifiers.get('brand', ''), identifiers.get('mpn', '')]))
            if not identifiers.get('mpn'):
                query = offer.reading.title
            for domain in domains:
                if domain == offer.domain:
                    continue
                urls = await discover(domain, query)
                for url in urls[:self.limits.comparisons_per_store]:
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
