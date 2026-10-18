import re
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup

from .base import StructuredAdapter


class FlexformAdapter(StructuredAdapter):
    name = 'Flexform'
    search_fields = ('term',)

    def is_product_url(self, url):
        p = urlsplit(url)
        return ((p.hostname or '').removeprefix('www.') == 'flexform.com.br'
                and bool(re.fullmatch(r'/cadeiras/[^/]+/[^/]+/?', p.path)))

    def search_links(self, html, url):
        from ..discovery import LinkCandidate
        soup = BeautifulSoup(html, 'html.parser')
        result = []
        for a in soup.select('a[href]'):
            link = urljoin(url, a['href'])
            if not self.is_product_url(link):
                continue
            name = a.get_text(' ', strip=True)
            image = a.find('img', alt=True)
            if image:
                name = image['alt'] or name
            if name:
                result.append(LinkCandidate(link, name))
        return result
