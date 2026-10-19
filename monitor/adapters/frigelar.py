import re
from urllib.parse import urlsplit, unquote

from .public_store import PublicStoreAdapter


class FrigelarAdapter(PublicStoreAdapter):
    name = 'Frigelar'
    domain = 'frigelar.com.br'
    # Publicados pelo sitemap.xml anunciado no robots.txt (19/10/2026).
    sitemap_urls = ('https://www.frigelar.com.br/productSitemap.xml',
                    'https://www.frigelar.com.br/productSitemap-2.xml')

    def sitemap_title(self, url):
        return unquote(urlsplit(url).path.strip('/').split('/')[0]).replace('-', ' ')

    def is_product_url(self, url):
        p = urlsplit(url)
        return ((p.hostname or '').removeprefix('www.') == self.domain
                and bool(re.fullmatch(r'/[^/]+/p/[a-zA-Z0-9_-]+/?', p.path)))
