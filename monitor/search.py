"""Busca descobre URLs; snippets e precos da API nunca sao usados."""

import asyncio
import httpx
from .adapters.base import ReadError


def search_error_message(code):
    return {
        'marketplace_not_authorized': 'Adicione mercadolivre.com.br a ALLOWED_DOMAINS no arquivo .env e reinicie o serviço.',
        "search_not_configured": (
            "A busca por nome não está configurada: falta SEARCH_API_KEY no arquivo .env.\n\n"
            "Crie uma chave em https://api-dashboard.search.brave.com/ e configure:\n"
            "SEARCH_PROVIDER=brave\nSEARCH_API_KEY=sua_chave\n\n"
            "Depois, salve e reinicie o robô. O token do Telegram não substitui essa chave."
        ),
        "search_disabled": "A busca por nome está desativada. Configure SEARCH_PROVIDER=direct no arquivo .env para pesquisar nas lojas sem chave, ou cadastre um link.",
        "search_provider_invalid": "SEARCH_PROVIDER inválido. Use direct (sem chave), brave (opcional) ou disabled.",
        "search_auth_error": "A API de busca recusou a chave ou a permissão. Confira a chave e o acesso no painel Brave Search.",
        "search_rate_limit_deferred": "A API de busca atingiu o limite de consultas. Aguarde antes de tentar novamente.",
        "search_unavailable": "A API de busca não respondeu após as tentativas. Tente novamente mais tarde.",
    }.get(code, "A API de busca retornou um erro. Confira sua conta e tente novamente.")


class Search:
    def __init__(self, config, fetcher):
        self.config, self.fetcher = config, fetcher
        self.lock = asyncio.Lock()

    async def marketplace_links(self, query):
        from types import SimpleNamespace
        from .discovery import DirectSearch
        if 'mercadolivre.com.br' not in self.config.domains:
            raise ReadError('marketplace_not_authorized')
        config = SimpleNamespace(
            domains=('mercadolivre.com.br',), browser=self.config.browser,
            mercadolivre_token='',
            mercadolivre_discovery='external',
        )
        async with self.lock:
            return await DirectSearch(config, self.fetcher).links(query)

    def configuration_error(self):
        if self.config.provider == "direct":
            return None
        if self.config.provider == "disabled":
            return "search_disabled"
        if self.config.provider != "brave":
            return "search_provider_invalid"
        if not self.config.key.strip():
            return "search_not_configured"
        return None

    async def links(self, query):
        error = self.configuration_error()
        if error:
            raise ReadError(error)
        if self.config.provider == "direct":
            from .discovery import DirectSearch

            async with self.lock:
                return await DirectSearch(self.config, self.fetcher).links(query)
        async with self.lock:
            from .search_scope import search_domains
            domains = search_domains(query, self.config.domains)
            if not domains:
                from .discovery import SearchLinks
                return SearchLinks(notices=['Nenhuma loja compatível com carnes está habilitada nesta configuração.'])
            async with httpx.AsyncClient(timeout=30) as client:
                for attempt in range(3):
                    try:
                        response = await client.get(
                            "https://api.search.brave.com/res/v1/web/search",
                            headers={
                                "X-Subscription-Token": self.config.key,
                                "Accept": "application/json",
                            },
                            params={
                                "q": query
                                + " ("
                                + " OR ".join("site:" + d for d in domains)
                                + ")",
                                "count": 20,
                            },
                        )
                        if response.status_code == 200:
                            data = response.json()
                            break
                        if response.status_code in (401, 403):
                            raise ReadError("search_auth_error")
                        if response.status_code not in (429, 500, 502, 503, 504):
                            raise ReadError("search_api_error")
                        retry = response.headers.get("Retry-After", "")
                        if retry and (not retry.isdigit() or int(retry) > 60):
                            raise ReadError("search_rate_limit_deferred")
                    except (httpx.RequestError, ValueError):
                        retry = ""
                    if attempt == 2:
                        raise ReadError("search_unavailable")
                    await asyncio.sleep(max(2 ** (attempt + 1), int(retry or 0)))
        result = []
        for item in data.get("web", {}).get("results", []):
            try:
                url, domain = self.fetcher.canonical(item["url"])
                if domain not in domains:
                    continue
                from .adapters import adapter
                checker = getattr(adapter(domain), 'is_product_url', None)
                if domain != 'mercadolivre.com.br' and checker and not checker(url):
                    continue
                if url not in result:
                    result.append(url)
            except (ReadError, KeyError, ValueError):
                continue
        return result[:15]
