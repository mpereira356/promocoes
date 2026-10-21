from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .base import CategoryAdapter, CategoryPage
from ...adapters.lacoste import LacosteAdapter


class LacosteCategories(CategoryAdapter):
    domain = 'lacoste.com'
    categories = {}
    limitations = ('Tamanhos sem estoque explícito são excluídos quando há filtro de tamanho. Descontos no carrinho não são somados ao desconto anunciado.',)

    def page(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        urls = [urljoin(url, a['href']) for a in soup.select('a[href]')]
        return CategoryPage(self.product_urls(urls), self.next_page(soup, url))

    def offer(self, html, url, reading):
        result = super().offer(html, url, reading)
        parser = LacosteAdapter()
        soup, product = parser.product(html, url)
        result.previous = parser.reference_price(soup, product, reading)
        result.reference_source = 'Preço riscado da mesma oferta Lacoste'
        result.available_sizes = parser.sizes(soup, product, reading)
        data = parser.page_product(soup, product)
        result.color = (data['color'].get('label', '') if data else '') or str(product.get('color', '')) or reading.identifiers.get('color', '')
        result.notes.append('Tamanhos disponíveis: ' + (', '.join(result.available_sizes) or 'não confirmados'))
        if result.color:
            result.notes.append('Cor: ' + result.color)
        return result
