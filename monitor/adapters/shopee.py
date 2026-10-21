import re
from urllib.parse import urlsplit

from .public_store import PublicStoreAdapter
from .base import ReadError


class ShopeeAdapter(PublicStoreAdapter):
    name = 'Shopee'
    domain = 'shopee.com.br'
    # Descoberta pública pelo índice existente; nunca usar preços de snippets.
    external_discovery = True

    def parse(self, html, url):
        try:
            return super().parse(html, url)
        except ReadError as exc:
            if str(exc) == 'structured_product_missing_or_ambiguous' and 'Please enable JavaScript on your browser.' in html:
                raise ReadError('store_requires_javascript') from None
            raise

    def is_product_url(self, url):
        p = urlsplit(url)
        return ((p.hostname or '').removeprefix('www.') == self.domain and bool(
            re.fullmatch(r'/(?:[^/]+-i\.\d+\.\d+|product/\d+/\d+)/?', p.path)))
