"""Descoberta no indice Tavily: modo oficial sem chave, sem extrair paginas."""
import asyncio
import time
from collections import OrderedDict
from urllib.parse import urlsplit, unquote
import re
import httpx
from .adapters.base import ReadError
from .discovery import LinkCandidate, relevance
from .models import normalize
from .identity import model_conflict


class CachedCandidates(list):
    def __init__(self, values, domain):
        super().__init__(values)
        self.notices = [f'{domain}: links recuperados do cache por indisponibilidade do índice externo; preço e estoque serão consultados novamente na loja.']


class ExternalMarketSearch:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.lock = asyncio.Lock()
        self.cache = OrderedDict()
        self.cooldown = 0

    async def links(self, query, domain='mercadolivre.com.br'):
        if domain not in self.fetcher.config.domains:
            raise ReadError('url_not_allowed')
        key = (domain, query.strip().casefold())
        async with self.lock:
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                return list(cached[1])
            if self.cooldown > time.monotonic():
                if cached and cached[0] + 7 * 86400 > time.monotonic():
                    return CachedCandidates(cached[1], domain)
                raise ReadError('external_search_limited')
            async with httpx.AsyncClient(timeout=40, follow_redirects=False) as client:
                for attempt in range(3):
                    try:
                        response = await client.post(
                            'https://api.tavily.com/search',
                            headers={'X-Tavily-Access-Mode': 'keyless', 'X-Client-Source': 'price-monitor'},
                            json={'query': query + ' site:' + domain,
                                  'include_domains': [domain],
                                  'include_domains_mode': 'restrict', 'search_depth': 'basic',
                                  'auto_parameters': False, 'max_results': 10,
                                  'include_answer': False, 'include_raw_content': False,
                                  'include_images': False},
                        )
                    except httpx.RequestError:
                        response = None
                    if response is not None:
                        if response.status_code in (429, 432, 433):
                            retry = response.headers.get('Retry-After', '')
                            self.cooldown = time.monotonic() + max(60, int(retry) if retry.isdigit() else 3600)
                            if cached and cached[0] + 7 * 86400 > time.monotonic():
                                return CachedCandidates(cached[1], domain)
                            raise ReadError('external_search_limited')
                        if response.status_code == 200:
                            break
                        if response.status_code not in (500, 502, 503, 504):
                            raise ReadError('external_search_unavailable')
                    if attempt == 2:
                        raise ReadError('external_search_unavailable')
                    await asyncio.sleep(2 ** (attempt + 1))
            try:
                items = response.json()['results']
                if not isinstance(items, list):
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise ReadError('external_search_unavailable') from None
            result, seen = [], set()
            for item in items:
                if not isinstance(item, dict):
                    continue
                url, title = item.get('url'), item.get('title')
                if not isinstance(url, str) or not isinstance(title, str) or not title.strip():
                    continue
                try:
                    url, result_domain = self.fetcher.canonical(url)
                except (ReadError, ValueError):
                    continue
                p = urlsplit(url)
                # O indice pode apresentar titulo antigo para URL de outro modelo.
                # Sem poder conferir a pagina, rejeitar conflito com o proprio slug.
                if model_conflict(query, unquote(p.path).replace('-', ' ')):
                    continue
                unwanted = {'arquivo', 'bios', 'manual', 'reparo'}
                if (set(normalize(title).split()) & unwanted) - set(normalize(query).split()):
                    continue
                if domain == 'mercadolivre.com.br':
                    individual = p.hostname == 'produto.mercadolivre.com.br' and re.match(r'^/MLB-\d+(?:-|$)', p.path)
                    catalog = p.hostname in ('www.mercadolivre.com.br', 'mercadolivre.com.br') and re.search(r'/(?:p/MLB\d+|up/MLBU\d+)(?:/|$)', p.path)
                    product_url = individual or catalog
                else:
                    from .adapters import adapter
                    product_url = getattr(adapter(domain), 'is_product_url', lambda u: False)(url)
                if result_domain == domain and product_url and url not in seen:
                    seen.add(url)
                    result.append(LinkCandidate(url, title.strip(), 'Tavily Search'))
            self.cache[key] = (time.monotonic() + 5 * 3600, result)
            self.cache.move_to_end(key)
            while len(self.cache) > 32:
                self.cache.popitem(last=False)
            return list(result)
