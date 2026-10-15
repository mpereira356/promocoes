"""Descoberta limitada por sitemaps publicados, respeitando o mesmo Fetcher."""

import asyncio
import time
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from .adapters.base import ReadError

MAX_DOCUMENTS = 4
MAX_URLS = 50000
CACHE_SECONDS = 18000


def parse_sitemap(text):
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ReadError("invalid_sitemap")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ReadError("invalid_sitemap") from None
    kind = root.tag.rsplit("}", 1)[-1]
    if kind not in ("urlset", "sitemapindex"):
        raise ReadError("invalid_sitemap")
    entries = []
    for child in root:
        if child.tag.rsplit("}", 1)[-1] != ("url" if kind == "urlset" else "sitemap"):
            continue
        for node in child:
            if node.tag.rsplit("}", 1)[-1] == "loc" and node.text:
                entries.append(node.text.strip())
                break
        if len(entries) >= MAX_URLS:
            break
    return kind, entries


async def sitemap_candidates(store, domain, fetcher):
    from .discovery import LinkCandidate

    cache = getattr(fetcher, "discovery_cache", None)
    if cache is None:
        cache = {}
        fetcher.discovery_cache = cache
    cached = cache.get(domain)
    if cached and cached[0] > time.time() - CACHE_SECONDS:
        return cached[1]
    queue = list(store.sitemap_urls)
    visited = set()
    products = {}
    processed = 0
    last_error = None
    while queue and len(visited) < MAX_DOCUMENTS and len(products) < MAX_URLS:
        url = queue.pop(0)
        try:
            url, host = fetcher.canonical(url)
        except (ReadError, ValueError):
            continue
        if host != domain or url in visited:
            continue
        visited.add(url)
        try:
            text, final = await fetcher.html(url)
            _, final_domain = fetcher.canonical(final)
            if final_domain != domain:
                raise ReadError("redirect_changed_store")
            kind, locations = await asyncio.to_thread(parse_sitemap, text)
            processed += 1
        except ReadError as exc:
            last_error = exc
            if str(exc) in (
                "robots_unavailable",
                "robots_disallowed",
                "blocked_no_bypass",
                "captcha_no_bypass",
            ):
                break
            continue
        if kind == "sitemapindex":
            queue = locations[: MAX_DOCUMENTS - len(visited)] + queue
            continue
        for location in locations:
            try:
                link, host = fetcher.canonical(location)
            except (ReadError, ValueError):
                continue
            if host != domain or not store.is_product_url(link):
                continue
            # O slug serve somente para selecionar links candidatos, nunca para preco/estoque.
            title = unquote(urlsplit(link).path.rsplit("/", 1)[-1]).replace("-", " ")
            products.setdefault(link, LinkCandidate(link, title))
            if len(products) >= MAX_URLS:
                break
    if not products and last_error:
        raise last_error
    if not processed:
        raise ReadError("invalid_sitemap")
    result = list(products.values())
    cache[domain] = (time.time(), result)
    return result
