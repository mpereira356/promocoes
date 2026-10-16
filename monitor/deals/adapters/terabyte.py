from .base import CategoryAdapter, CategoryPage, one_display_price
from ...adapters import adapter
from bs4 import BeautifulSoup


class TerabyteCategories(CategoryAdapter):
    domain = 'terabyteshop.com.br'
    categories = {'hardware/placas-mae': 'https://www.terabyteshop.com.br/hardware/placas-mae'}
    limitations = ('Preço anterior por HTML limitado ao bloco de preço à vista validado; outros layouts podem não qualificar.',)

    def page(self, html, url):
        links = adapter(self.domain).search_links(html, url)
        return CategoryPage(self.product_urls([x.url for x in links]), self.next_page(BeautifulSoup(html, 'html.parser'), url))

    def offer(self, html, url, reading):
        result = super().offer(html, url, reading)
        if reading.payment not in ('Pix', 'Boleto') or reading.currency != 'BRL':
            return result
        scope = adapter(self.domain).cash_price_scope(BeautifulSoup(html, 'html.parser'), url, reading)
        if scope is None or one_display_price(scope.select_one('#valVista')) != reading.price:
            return result
        previous = scope.select('p.precode del')
        if len(previous) == 1:
            old = one_display_price(previous[0])
            if old and old > reading.price:
                result.previous = old
                result.reference_source = 'preço de/por do bloco à vista Terabyte; não comprova queda histórica'
        return result
