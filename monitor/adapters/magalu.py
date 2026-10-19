import re
from urllib.parse import quote, urlsplit

from .public_store import PublicStoreAdapter


class MagaluAdapter(PublicStoreAdapter):
    name = 'Magalu'
    domain = 'magazineluiza.com.br'
    external_discovery = True

    def search_url(self, query):
        return 'https://www.magazineluiza.com.br/busca/' + quote(query, safe='') + '/'

    def is_product_url(self, url):
        p = urlsplit(url)
        return (p.hostname in (self.domain, 'www.' + self.domain, 'm.' + self.domain)
                and bool(re.fullmatch(r'/[^/]+/p/[a-zA-Z0-9]+(?:/[a-zA-Z0-9]+){0,2}/?', p.path)))
