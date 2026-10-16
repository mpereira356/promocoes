import json
import re
from urllib.parse import urlsplit, urlencode
from bs4 import BeautifulSoup
from .base import CategoryAdapter, CategoryPage
from ...models import money, normalize
from ...adapters.kabum import KabumAdapter


class KabumCategories(CategoryAdapter):
    domain = 'kabum.com.br'
    categories = {'hardware/placas-mae': 'https://www.kabum.com.br/hardware/placas-mae'}

    def page(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')
        if not script:
            return super().page(html, url)
        try:
            catalog = KabumAdapter.catalog_data(soup)
            urls = []
            for item in catalog['data']:
                code, slug = str(item.get('code', '')), item.get('friendlyName', '')
                if code.isdigit() and isinstance(slug, str) and re.fullmatch('[a-z0-9-]+', slug):
                    urls.append(f'https://www.kabum.com.br/produto/{code}/{slug}')
            pagination = catalog.get('pagination', {})
            current, nxt = pagination.get('current'), pagination.get('next')
            next_url = None
            if isinstance(nxt, int) and isinstance(current, int) and nxt == current + 1:
                next_url = urlsplit(url)._replace(query=urlencode({'page_number': nxt, 'page_size': 60})).geturl()
            return CategoryPage(self.product_urls(urls), next_url)
        except (ValueError, KeyError, TypeError, AttributeError):
            return super().page(html, url)

    def offer(self, html, url, reading):
        result = super().offer(html, url, reading)
        script = BeautifulSoup(html, 'html.parser').find('script', id='__NEXT_DATA__')
        try:
            product = json.loads(script.get_text())['props']['pageProps']['product']
            match = re.match(r'/produto/(\d+)(?:/|$)', urlsplit(url).path)
            if not match or str(product['id']) != match[1] or normalize(product['title']) != normalize(reading.title):
                return result
            result.previous = money(product.get('prices', {}).get('oldPrice'))
            result.reference_source = 'oldPrice do produto na KaBuM'
            prime = product.get('prime') or {}
            if prime.get('isLoggedUserExclusive') is True and reading.price in (money(prime.get('price')), money(prime.get('priceWithDiscount'))):
                # Nao assumir que preco publico e preco exclusivo sao a mesma oferta.
                result.members = 'KaBuM Prime (exclusividade declarada)'
            stamp = product.get('stamps') or {}
            if isinstance(stamp, dict) and 'cupom' in normalize(str(stamp.get('title', ''))):
                result.notes.append('Cupom divulgado: ' + str(stamp.get('title')) + '; nao aplicado novamente ao preco.')
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
        return result
