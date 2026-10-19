import re
from urllib.parse import urlsplit

from .public_store import PublicStoreAdapter


class ShopeeAdapter(PublicStoreAdapter):
    name = 'Shopee'
    domain = 'shopee.com.br'
    # Descoberta pública pelo índice existente; nunca usar preços de snippets.
    external_discovery = True

    def is_product_url(self, url):
        p = urlsplit(url)
        return ((p.hostname or '').removeprefix('www.') == self.domain and bool(
            re.fullmatch(r'/(?:[^/]+-i\.\d+\.\d+|product/\d+/\d+)/?', p.path)))
