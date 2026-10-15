"""Descoberta em paginas publicas; nenhum preco do catalogo e utilizado."""

import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlencode
from bs4 import BeautifulSoup
from .models import normalize
from .adapters.base import ReadError, nodes


@dataclass
class LinkCandidate:
    url: str
    title: str


class SearchLinks(list):
    def __init__(self, links=(), notices=()):
        super().__init__(links)
        self.notices = list(notices)


def relevance(query, title):
    stop = {"de", "da", "do", "das", "dos", "com", "para", "e", "a", "o"}
    wanted = set(normalize(query).split()) - stop
    found = set(normalize(title).split())
    if not wanted or not found:
        return 0
    # Nunca sugerir B650/X870 quando foi pedido B550, ou RTX 4060 para RTX 4070.
    models = {t for t in wanted if any(c.isdigit() for c in t)}
    if not models <= found:
        return 0
    score = len(wanted & found) / len(wanted)
    return score if score >= 0.6 else 0


def documents(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            yield from nodes(json.loads(script.string or script.get_text()))
        except (TypeError, ValueError):
            continue


def structured_links(soup, base):
    result = []
    for item in documents(soup):
        kind = item.get("@type")
        if kind == "Product" and isinstance(item.get("url"), str):
            result.append(
                LinkCandidate(urljoin(base, item["url"]), str(item.get("name", "")))
            )
        elif kind == "ListItem":
            product = item.get("item")
            if isinstance(product, dict):
                url = product.get("url") or product.get("@id")
                name = product.get("name") or item.get("name", "")
            else:
                url = product if isinstance(product, str) else item.get("url")
                name = item.get("name", "")
            if isinstance(url, str):
                result.append(LinkCandidate(urljoin(base, url), str(name)))
    return result


def form_search_url(html, base, query, fields=None):
    """Usar apenas formulario GET realmente declarado pela loja."""
    soup = BeautifulSoup(html, "html.parser")
    for form in soup.find_all("form"):
        if form.get("method", "get").lower() != "get":
            continue
        for field in form.find_all("input"):
            name = field.get("name", "")
            if name.lower() not in (fields or ("q", "query", "search", "str", "searchterm")):
                continue
            action = form.get("action")
            if not action:
                continue
            url = urljoin(base, action)
            params = [
                (i.get("name"), i.get("value", ""))
                for i in form.find_all("input", type="hidden")
                if i.get("name")
            ]
            params.append((name, query))
            return url + ("&" if "?" in url else "?") + urlencode(params)
    raise ReadError("search_form_not_supported")


REASONS = {
    'mercadolivre_api_token_missing': 'API oficial exige MERCADOLIVRE_ACCESS_TOKEN no .env',
    'mercadolivre_api_token_expired': 'token da API invalido ou expirado; atualize MERCADOLIVRE_ACCESS_TOKEN',
    'mercadolivre_api_access_denied': 'API oficial recusou acesso (403); verifique permissoes do aplicativo, token pode nao ser suficiente',
    'mercadolivre_api_failed': 'API oficial indisponivel ou resposta invalida',
    "marketplace_individual_listing_required": "exige link de anuncio individual; catalogo pode trocar de vendedor",
    "browser_not_installed": "Chromium indisponivel; execute o instalador com --with-browser",
    "browser_navigation_failed_TimeoutError": "tempo limite ao carregar a pagina no Chromium",
    "browser_connection_failed": "conexao com a loja interrompida",
    "browser_navigation_failed_Error": "falha de navegacao no Chromium",
    "browser_resource_refused": "recurso da pagina recusado por seguranca ou falha de rede",
    "structured_product_missing_or_ambiguous": "pagina sem dados estruturados de um produto unico",
    "redirect_changed_store": "redirecionamento para outra loja recusado",
    "blocked_no_bypass": "acesso bloqueado pela loja; sem tentativa de contorno",
    "captcha_no_bypass": "CAPTCHA detectado; consulta interrompida",
    "robots_unavailable": "nao foi possivel obter robots.txt; acesso suspenso",
    "robots_disallowed": "robots.txt nao permite esta consulta",
    "search_form_not_supported": "formulario de busca nao suportado; exige adaptacao",
    "network_or_rate_limit": "erro de rede ou limite de consultas",
    "rate_limit_deferred": "limite de consultas; tentar em outro ciclo",
    "page_removed": "pagina de busca indisponivel",
}


class DirectSearch:
    def __init__(self, config, fetcher):
        self.config, self.fetcher = config, fetcher

    async def links(self, query):
        from .adapters import ADAPTERS

        links, notices, groups = [], [], []
        for domain in self.config.domains:
            factory = ADAPTERS.get(domain)
            if not factory:
                notices.append(
                    f"{domain}: dominio autorizado para links, mas sem adaptador de busca direta. Adicionar o dominio nao instala uma integracao."
                )
                continue
            store = factory()
            try:
                if domain == 'mercadolivre.com.br' and getattr(self.config, 'mercadolivre_token', ''):
                    from .mercadolivre_api import discover
                    candidates = await discover(query, self.config.mercadolivre_token, self.fetcher)
                elif store.sitemap_urls:
                    from .sitemaps import sitemap_candidates

                    candidates = await sitemap_candidates(store, domain, self.fetcher)
                else:
                    url = store.search_url(query)
                    if url is None:
                        home = "https://www." + domain + "/"
                        html, final = await self.fetcher.html(home)
                        url = form_search_url(html, final, query, getattr(store, 'search_fields', None))
                    url, search_domain = self.fetcher.canonical(url)
                    if search_domain != domain:
                        raise ReadError("url_not_allowed")
                    html, final = await self.fetcher.html(url)
                    _, final_domain = self.fetcher.canonical(final)
                    if final_domain != domain:
                        raise ReadError("redirect_changed_store")
                    candidates = store.search_links(html, final)
                    if not candidates and self.config.browser:
                        # Somente HTML aceito sem bloqueio; nunca fallback para 403/CAPTCHA.
                        candidates = store.search_links(
                            await self.fetcher.render(final), final
                        )
                ranked = sorted(
                    ((relevance(query, c.title), c) for c in candidates),
                    key=lambda x: x[0],
                    reverse=True,
                )
                accepted = []
                for score, c in ranked:
                    if not score:
                        continue
                    try:
                        link, link_domain = self.fetcher.canonical(c.url)
                    except (ReadError, ValueError):
                        continue
                    if link_domain == domain and link not in accepted:
                        accepted.append(link)
                groups.append(accepted[:6])
                if not accepted:
                    notices.append(
                        f"{store.name}: nenhum candidato compativel na fonte consultada (HTML ou sitemap limitado). Isso nao prova ausencia do produto."
                    )
            except Exception as exc:
                reason = (
                    REASONS.get(str(exc), "falha ao ler a busca")
                    if isinstance(exc, ReadError)
                    else "falha ao ler a busca"
                )
                notices.append(f"{store.name}: {reason}.")
                if domain == 'mercadolivre.com.br' and not getattr(self.config, 'mercadolivre_token', ''):
                    notices.append('Mercado Livre: descoberta sem autenticacao falhou. A alternativa oficial exige aplicativo e token; nao ha busca real validada neste ambiente.')
        # Distribuir o limite entre lojas; a ultima loja nao deve desaparecer.
        for index in range(6):
            for group in groups:
                if index < len(group) and group[index] not in links:
                    links.append(group[index])
        return SearchLinks(links[:15], notices)
