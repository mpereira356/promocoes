"""Busca descobre URLs; snippets e precos da API nunca sao usados."""

import asyncio
import httpx
from .adapters.base import ReadError


def search_error_message(code):
    return {
        "search_not_configured": (
            "A busca por nome nao esta configurada: falta SEARCH_API_KEY no arquivo .env.\n"
            "Crie uma chave em https://api-dashboard.search.brave.com/ e preencha:\n"
            "SEARCH_PROVIDER=brave\nSEARCH_API_KEY=sua_chave\n"
            "Depois salve e reinicie o robo. O token do Telegram nao substitui essa chave."
        ),
        "search_disabled": "A busca por nome esta desativada. Use SEARCH_PROVIDER=direct no .env para pesquisar nas lojas sem chave, ou cadastre um link.",
        "search_provider_invalid": "SEARCH_PROVIDER invalido. Use direct (sem chave), brave (opcional) ou disabled.",
        "search_auth_error": "A API de busca recusou a chave ou a permissao. Confira sua chave e o acesso no painel Brave Search.",
        "search_rate_limit_deferred": "A API de busca limitou as consultas. Aguarde antes de tentar novamente.",
        "search_unavailable": "A API de busca nao respondeu apos as tentativas. Tente novamente mais tarde.",
    }.get(code, "A API de busca retornou um erro. Confira sua conta e tente novamente.")


class Search:
    def __init__(self, config, fetcher):
        self.config, self.fetcher = config, fetcher
        self.lock = asyncio.Lock()

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
                                + " OR ".join("site:" + d for d in self.config.domains)
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
                if url not in result:
                    result.append(url)
            except (ReadError, KeyError, ValueError):
                continue
        return result[:15]
