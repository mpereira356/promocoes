"""Suporte conservador a anuncios individuais; integracao real ainda bloqueada em teste."""
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from .base import StructuredAdapter, ReadError


class MercadoLivreAdapter(StructuredAdapter):
    name = 'Mercado Livre'
    search_fields = ('q', 'query', 'search', 'str', 'searchterm', 'as_word')

    def is_product_url(self, url):
        p = urlsplit(url)
        return (
            p.scheme == 'https'
            and p.hostname == 'produto.mercadolivre.com.br'
            and bool(re.match(r'^/MLB-\d+(?:-|$)', p.path))
        )

    def search_links(self, html, url):
        from ..discovery import LinkCandidate, structured_links
        soup = BeautifulSoup(html, 'html.parser')
        candidates = structured_links(soup, url)
        for a in soup.find_all('a', href=True):
            link = a['href']
            title = a.get('title') or a.get('aria-label') or a.get_text(' ', strip=True)
            if title and self.is_product_url(link):
                candidates.append(LinkCandidate(link, title))
        seen, result = set(), []
        for candidate in candidates:
            if self.is_product_url(candidate.url) and candidate.url not in seen:
                seen.add(candidate.url)
                result.append(candidate)
        return result

    def parse(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('marketplace_individual_listing_required')
        # Nao inferir vendedor, pagamento, condicao ou estoque do nome do marketplace.
        return super().parse(html, url)
