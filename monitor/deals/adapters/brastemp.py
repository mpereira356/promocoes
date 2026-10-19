from .base import CategoryAdapter, CategoryPage
from ...adapters.brastemp import BrastempAdapter
from ...models import money
from bs4 import BeautifulSoup


class BrastempCategories(CategoryAdapter):
    domain = 'brastemp.com.br'
    categories = {'eletrodomesticos/freezers-verticais': 'https://www.brastemp.com.br/eletrodomesticos/freezer/vertical'}
    limitations = ('Frete não cotado; preços e disponibilidade referem-se ao SKU selecionado.',)

    def page(self, html, url):
        parser = BrastempAdapter()
        soup = BeautifulSoup(html, 'html.parser')
        return CategoryPage(self.product_urls([c.url for c in parser.search_links(html, url)]), self.next_page(soup, url))

    def offer(self, html, url, reading):
        result = super().offer(html, url, reading)
        parser = BrastempAdapter()
        product = parser.selected_product(BeautifulSoup(html, 'html.parser'))
        if not product or not reading.comparable:
            return result
        aggregate = product.get('offers', {})
        offers = aggregate.get('offers', []) if isinstance(aggregate, dict) else []
        # Somente a mesma leitura validada de SKU/vendedor/modalidade, nunca recomendações.
        verified = parser.parse(html, url)
        same = [r for r in verified if r.identifiers == reading.identifiers and r.price == reading.price
                and r.seller == reading.seller and r.payment == reading.payment and r.condition == reading.condition]
        if len(same) == 1 and isinstance(offers, list) and len(offers) == 1:
            offer = offers[0]
            if money(offer.get('price')) == reading.price and offer.get('priceCurrency') == reading.currency:
                previous = money(offer.get('listPrice'))
                if previous and previous > reading.price:
                    result.previous = previous
                    result.reference_source = 'listPrice da mesma oferta/SKU no HTML Brastemp'
        result.model = reading.identifiers.get('model', '')
        return result
