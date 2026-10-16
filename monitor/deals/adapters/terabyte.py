from .base import CategoryAdapter, CategoryPage
from ...adapters import adapter
from bs4 import BeautifulSoup


class TerabyteCategories(CategoryAdapter):
    domain = 'terabyteshop.com.br'
    categories = {'hardware/placas-mae': 'https://www.terabyteshop.com.br/hardware/placas-mae'}
    limitations = ('Preco anterior por HTML ainda nao validado nesta loja; somente StrikethroughPrice estruturado da oferta pode qualificar.',)

    def page(self, html, url):
        links = adapter(self.domain).search_links(html, url)
        return CategoryPage(self.product_urls([x.url for x in links]), self.next_page(BeautifulSoup(html, 'html.parser'), url))

    # Del de recomendacoes nao e referencia do produto. Sem estrutura principal
    # validada para preco anterior, nao atribuir desconto percentual.
