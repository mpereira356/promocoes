from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CategoryAdapter, CategoryPage, primary_scope, one_display_price


class PichauCategories(CategoryAdapter):
    domain = 'pichau.com.br'
    catalog_discovery = 'sitemap'
    categories = {'hardware/placas-mae': 'https://www.pichau.com.br/hardware/placa-m-e'}

    def page(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('a[data-cy="list-product"][href]')
        if not cards:
            return super().page(html, url)
        return CategoryPage(self.product_urls([urljoin(url, a['href']) for a in cards]), self.next_page(soup, url))

    def offer(self, html, url, reading):
        result = super().offer(html, url, reading)
        scope = primary_scope(BeautifulSoup(html, 'html.parser'), reading, 'div[class*="-price_vista-"]')
        if scope and reading.payment == 'Pix':
            current = scope.select('div[class*="-price_vista-"]')
            previous = scope.select('div[class*="-price_from"]')
            if len(previous) == 1 and one_display_price(current[0]) == reading.price:
                result.previous = one_display_price(previous[0])
                result.reference_source = 'preco de/por do bloco principal Pichau'
        return result
