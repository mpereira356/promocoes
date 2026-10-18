"""Categorias publicas observadas nas tres lojas de cadeiras."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import CategoryAdapter, CategoryPage
from ...adapters import adapter
from ...models import normalize


class ChairCategories(CategoryAdapter):
    limitations = ('Pagamento, vendedor e condicao ausentes permanecem nao confirmados; frete nao cotado.',)

    def page(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        urls = self.product_urls([urljoin(url, a['href']) for a in soup.select('a[href]')])
        return CategoryPage(urls, self.next_page(soup, url))

    def offer(self, html, url, reading):
        offer = super().offer(html, url, reading)
        parser = adapter(self.domain)
        if not hasattr(parser, 'product'):
            return offer
        data = parser.product(html, url)
        variants = parser.variants(data, url)
        refs = [v.get('compare_at_price') for v in variants]
        if (normalize(reading.title).startswith(normalize(data['title']))
                and all(v.get('price') == reading.price for v in variants)
                and all(type(r) is int and r > 0 for r in refs)
                and len(set(refs)) == 1):
            offer.previous = refs[0]
            offer.reference_source = 'compare_at_price das mesmas variantes no HTML da loja'
        return offer


class SensetupCategories(ChairCategories):
    domain = 'sensetup.com.br'
    categories = {'cadeiras/ergonomicas': 'https://sensetup.com.br/collections/cadeiras-ergonomicas'}


class ElementsCategories(ChairCategories):
    domain = 'loja.elements.com.br'
    categories = {'cadeiras/ergonomicas': 'https://loja.elements.com.br/collections/cadeiras'}


class FlexformCategories(ChairCategories):
    domain = 'flexform.com.br'
    categories = {'cadeiras/ergonomicas': 'https://www.flexform.com.br/cadeiras/cadeiras-ergonomicas'}
