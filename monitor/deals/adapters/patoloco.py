from bs4 import BeautifulSoup
from .base import CategoryAdapter, CategoryPage
from ...adapters.patoloco import PatolocoAdapter


class PatolocoCategories(CategoryAdapter):
    domain = 'patoloco.com.br'
    categories = {}

    def page(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        return CategoryPage(self.product_urls([c.url for c in PatolocoAdapter().search_links(html, url)]), self.next_page(soup, url))
