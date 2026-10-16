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
    source: str = ''


class SearchLinks(list):
    def __init__(self, links=(), notices=(), candidates=None):
        super().__init__(links)
        self.notices = list(notices)
        self.candidates = candidates or {}


def relevance(query, title):
    from .identity import model_conflict, logitech_part_number, BRANDS
    stop = {"de", "da", "do", "das", "dos", "com", "para", "e", "a", "o"}
    def terms(text):
        text = re.sub(r'(\d+)\s*[ªº°]', r'\1', text)
        text = normalize(text)
        text = re.sub(r'\b(\d+)\s+(gb|tb|mhz|hz|w)\b', r'\1\2', text)
        return set(text.split())
    wanted = terms(query) - stop
    found = terms(title)
    vacuum_parts = {'copo', 'filtro', 'escova', 'bico', 'bateria', 'carregador', 'peca'}
    if 'aspirador' in wanted and not wanted & vacuum_parts and re.match(
            r'^(?:copo|filtro|escova|bico|bateria|carregador|peca)s?\b', normalize(title)) and found & {'para', 'substituicao'}:
        return 0
    for category in ({'teclado', 'keyboard'}, {'mouse', 'mice'}, {'headset', 'headphone', 'fone'}, {'monitor', 'monitores'}):
        if wanted & category and not found & category:
            return 0
    if not (wanted & BRANDS) <= found:
        return 0
    if re.search(r'\bg pro\b', normalize(query)) and not re.search(r'\bg pro\b', normalize(title)):
        return 0
    accessories = {'arquivo', 'bios', 'manual', 'guia', 'guide', 'ebook', 'suporte', 'capa', 'pelicula'}
    if (found & accessories) - wanted:
        return 0
    for family in ({'aorus', 'elite'}, {'rog', 'strix'}):
        if family <= wanted and not family <= found:
            return 0
    if model_conflict(query, title) or not (wanted & {'wifi', 'ii', 'ax'}) <= found:
        return 0
    part, candidate_part = logitech_part_number(query), logitech_part_number(title)
    if part and candidate_part:
        return 1 if part == candidate_part else 0
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
    'individual_listing_required': 'É necessário um link de produto individual; categorias não são ofertas com preço validado',
    'conflicting_product_identifiers': 'A página apresenta códigos de produto conflitantes; a comparação foi recusada',
    'domain_access_cooldown': 'A loja recusou acesso recentemente. Novas consultas a ela ficam suspensas por até 15 minutos; as outras lojas continuam',
    'network_dns_failure': 'O servidor não conseguiu resolver o endereço da loja após três tentativas de DNS',
    'amazon_price_requires_cart': 'A Amazon ocultou o preço e pede adicionar o item ao carrinho. Nenhuma ação de compra foi feita; preço não confirmado',
    'amazon_browser_crashed': 'O processo do Chrome encerrou ou a aba falhou. Verifique memória, espaço temporário e os logs do serviço',
    'amazon_browser_start_failed': 'Não foi possível iniciar Chrome/ChromeDriver. Verifique a instalação e as permissões do usuário pricebot',
    'amazon_browser_navigation_failed': 'O Chrome não conseguiu abrir a página da Amazon',
    'amazon_browser_connection_failed': 'A conexão do Chrome com a Amazon falhou por rede, DNS ou proxy',
    'amazon_offers_panel_timeout': 'A página abriu, mas o painel de ofertas não ficou disponível no tempo limite',
    'selenium_not_installed': 'Selenium não está instalado. Atualize o serviço com deploy/update.sh',
    'amazon_offers_http_error': 'A Amazon recusou a consulta ou não carregou o painel de ofertas',
    'amazon_offers_unavailable': 'Não foi possível carregar as opções de compra da Amazon no navegador',
    'different_model': 'O título real da página não corresponde ao produto pesquisado',
    'external_search_limited': 'O limite da busca externa sem chave foi atingido. Aguarde antes de tentar novamente',
    'external_search_unavailable': 'O índice externo está indisponível. Nenhum resultado foi inventado',
    'mercadolivre_api_token_missing': 'A API oficial exige MERCADOLIVRE_ACCESS_TOKEN no arquivo .env',
    'mercadolivre_api_token_expired': 'O token da API é inválido ou expirou. Atualize MERCADOLIVRE_ACCESS_TOKEN',
    'mercadolivre_api_access_denied': 'A API oficial recusou o acesso (403). Verifique as permissões do aplicativo; o token pode não ser suficiente',
    'mercadolivre_api_failed': 'A API oficial está indisponível ou retornou uma resposta inválida',
    "marketplace_individual_listing_required": 'É necessário um link de anúncio individual; um catálogo pode trocar de vendedor',
    "browser_not_installed": 'Chromium está indisponível. Execute o instalador com --with-browser',
    "browser_navigation_failed_TimeoutError": 'A página excedeu o tempo limite de carregamento no Chromium',
    "browser_connection_failed": 'A conexão com a loja foi interrompida',
    "browser_navigation_failed_Error": 'Não foi possível navegar no Chromium',
    "browser_resource_refused": 'Um recurso da página foi recusado por segurança ou por uma falha de rede',
    "structured_product_missing_or_ambiguous": 'A página não contém dados estruturados de um único produto',
    "redirect_changed_store": 'O redirecionamento para outra loja foi recusado',
    "blocked_no_bypass": 'A loja bloqueou o acesso. Nenhuma tentativa de contornar o bloqueio foi feita',
    "captcha_no_bypass": 'CAPTCHA detectado. A consulta foi interrompida',
    "robots_unavailable": 'Não foi possível obter o robots.txt; o acesso foi suspenso',
    "robots_disallowed": 'O robots.txt não permite esta consulta',
    "search_form_not_supported": 'O formulário de busca não é compatível e precisa de adaptação',
    "network_or_rate_limit": 'Ocorreu uma falha de rede ou foi atingido o limite de consultas',
    "rate_limit_deferred": 'O limite de consultas foi atingido. Tente novamente em outro ciclo',
    "page_removed": 'A página de busca está indisponível',
}


class DirectSearch:
    def __init__(self, config, fetcher):
        self.config, self.fetcher = config, fetcher

    async def external_candidates(self, query, domain):
        from .external_market_search import ExternalMarketSearch
        if not getattr(self.fetcher, 'external_market_search', None):
            self.fetcher.external_market_search = ExternalMarketSearch(self.fetcher)
        return await self.fetcher.external_market_search.links(query, domain)

    async def links(self, query):
        from .adapters import ADAPTERS
        from .identity import search_terms

        query = search_terms(query)

        links, notices, groups, details = [], [], [], {}
        for domain in self.config.domains:
            factory = ADAPTERS.get(domain)
            if not factory:
                notices.append(
                    f"{domain}: o domínio está autorizado para links, mas ainda não tem adaptador de busca direta. Autorizar o domínio não instala uma integração."
                )
                continue
            store = factory()
            try:
                if domain == 'mercadolivre.com.br' and getattr(self.config, 'mercadolivre_token', ''):
                    from .mercadolivre_api import discover
                    candidates = await discover(query, self.config.mercadolivre_token, self.fetcher)
                elif domain == 'mercadolivre.com.br' and getattr(self.config, 'mercadolivre_discovery', 'external') == 'external':
                    candidates = await self.external_candidates(query, domain)
                elif getattr(store, 'external_discovery', False):
                    candidates = await self.external_candidates(query, domain)
                elif store.sitemap_urls:
                    from .sitemaps import sitemap_candidates

                    try:
                        candidates = await sitemap_candidates(store, domain, self.fetcher)
                    except ReadError as exc:
                        if str(exc) in ('robots_disallowed', 'robots_unavailable', 'blocked_no_bypass', 'captcha_no_bypass'):
                            raise
                        candidates = []
                    if not any(relevance(query, c.title) for c in candidates):
                        candidates = await self.external_candidates(query, domain)
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
                notices.extend(getattr(candidates, 'notices', []))
                accepted = []
                for score, c in ranked:
                    if not score:
                        continue
                    try:
                        link, link_domain = self.fetcher.canonical(c.url)
                    except (ReadError, ValueError):
                        continue
                    if link_domain == domain and link not in accepted:
                        checker = getattr(store, 'is_product_url', None)
                        if domain != 'mercadolivre.com.br' and checker and not checker(link):
                            continue
                        accepted.append(link)
                        details[link] = c
                groups.append(accepted[:6])
                if not accepted:
                    notices.append(
                        f"{store.name}: não encontramos um candidato compatível na fonte consultada (HTML, sitemap limitado ou índice externo). Isso não prova que o produto não exista."
                    )
            except Exception as exc:
                reason = (
                    REASONS.get(str(exc), "falha ao ler a busca")
                    if isinstance(exc, ReadError)
                    else "falha ao ler a busca"
                )
                notices.append(f"{store.name}: {reason}.")
                if domain == 'mercadolivre.com.br':
                    notices.append('Mercado Livre: a descoberta falhou nesta consulta. Isso não prova que o produto não exista.')
        # Distribuir o limite entre lojas; a ultima loja nao deve desaparecer.
        for index in range(6):
            for group in groups:
                if index < len(group) and group[index] not in links:
                    links.append(group[index])
        return SearchLinks(links[:15], notices, {u: details[u] for u in links[:15]})
