"""Links públicos e ofertas Schema.org; sem endpoints privados ou preços de índice."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import StructuredAdapter, ReadError


class PublicStoreAdapter(StructuredAdapter):
    domain = ''

    def search_links(self, html, url):
        from ..discovery import LinkCandidate
        result = super().search_links(html, url)
        for anchor in BeautifulSoup(html, 'html.parser').select('a[href]'):
            target = urljoin(url, anchor['href'])
            title = anchor.get_text(' ', strip=True) or anchor.get('title', '')
            if title and self.is_product_url(target):
                result.append(LinkCandidate(target, title))
        return [c for c in result if self.is_product_url(c.url)]

    def parse(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('individual_listing_required')
        return super().parse(html, url)
