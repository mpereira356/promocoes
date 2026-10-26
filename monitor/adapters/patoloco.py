"""Public Product/Offer microdata observed on the retailer's own page."""
import re
from urllib.parse import urlsplit, urlencode
from bs4 import BeautifulSoup
from .public_store import PublicStoreAdapter
from .base import ReadError, product_image, tail
from ..models import Reading, money, normalize


class PatolocoAdapter(PublicStoreAdapter):
    domain = 'patoloco.com.br'
    name = 'Patoloco'

    def is_product_url(self, url):
        p = urlsplit(url)
        return (p.hostname in (self.domain, 'www.' + self.domain)
                and bool(re.fullmatch(r'/[a-z0-9]+(?:-[a-z0-9]+){2,}/?', p.path)))

    def search_url(self, query):
        return 'https://patoloco.com.br/busca/?' + urlencode({'buscar-por': query})

    def parse(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('individual_listing_required')
        soup = BeautifulSoup(html, 'html.parser')
        products = soup.select('[itemtype="http://schema.org/Product"]')
        if len(products) != 1:
            raise ReadError('structured_product_missing_or_ambiguous')
        product = products[0]
        names = product.select('[itemprop="name"]')
        offers = product.select('[itemtype="http://schema.org/Offer"]')
        if len(names) != 1 or len(offers) != 1:
            raise ReadError('ambiguous_offer_variants')
        title = names[0].get_text(' ', strip=True)
        if not title or not any(normalize(h.get_text(' ', strip=True)).startswith(normalize(title)) for h in product.select('h1')):
            raise ReadError('conflicting_product_title')
        scope = offers[0]
        prices, currencies = scope.select('[itemprop="price"]'), scope.select('[itemprop="priceCurrency"]')
        if len(prices) != 1 or len(currencies) != 1 or currencies[0].get('content') != 'BRL':
            raise ReadError('ambiguous_offer_variants')
        price = money(prices[0].get('content'))
        if not price:
            raise ReadError('structured_product_missing_or_ambiguous')
        available = scope.select('[itemprop="availability"]')
        stock = {'InStock': 'in_stock', 'OutOfStock': 'out_of_stock'}.get(tail(available[0].get('href')), 'unknown') if len(available) == 1 else 'unknown'
        condition = product.select('[itemprop="itemCondition"]')
        condition = tail(condition[0].get('href') or condition[0].get('content')) if len(condition) == 1 else ''
        condition = condition if condition in ('NewCondition', 'UsedCondition', 'RefurbishedCondition') else ''
        brands = product.select('[itemprop="brand"]')
        ids = {'brand': normalize(brands[0].get_text(' ', strip=True))} if len(brands) == 1 else {}
        part = re.search(r' - ([A-Z0-9-]*\d[A-Z0-9-]*)$', title)
        if part:
            ids['mpn'] = normalize(part[1])  # Manufacturer code in title; never the internal SKU.
        image = product.select_one('[itemprop="image"]')
        image = product_image(image.get('src'), url) if image else ''
        payment_text = normalize(scope.get_text(' ', strip=True))
        methods = ['Pix', 'Boleto'] if 'pix ou boleto' in payment_text else []
        if not methods:
            methods = ['']
        return [Reading(title, self.name, condition, method, price, stock, image=image, identifiers=ids.copy()) for method in methods]
