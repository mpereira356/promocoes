"""Public grocery discovery; regional/weighted prices fail closed."""
import json
import re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from .public_store import PublicStoreAdapter
from .base import ReadError, nodes


class GroceryAdapter(PublicStoreAdapter):
    external_discovery = True

    def is_product_url(self, url):
        p = urlsplit(url)
        return (p.scheme == 'https' and not p.username and not p.password
                and p.hostname in (self.domain, 'www.' + self.domain)
                and bool(re.fullmatch(self.product_path, p.path)))

    def parse(self, html, url):
        readings = super().parse(html, url)
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                products.extend(n for n in nodes(json.loads(script.get_text()))
                                if n.get('@type') == 'Product')
            except (ValueError, TypeError):
                continue
        if len(products) != 1:
            raise ReadError('structured_product_missing_or_ambiguous')
        # A public default price is not evidence of the shopper's delivery region.
        # No regional session has been configured for these integrations yet.
        # Never seed a price history/alert with a default store's price.
        for reading in readings:
            reading.price = None
            reading.payment = ''
            reading.stock = 'unknown'
            reading.identifiers['regional_price_pending'] = 'true'
        return readings


class AtacadaoAdapter(GroceryAdapter):
    domain = 'atacadao.com.br'
    name = 'Atacadão'
    product_path = r'/[^/]+/p/?'


class ExtraMercadoAdapter(GroceryAdapter):
    domain = 'extramercado.com.br'
    name = 'Extra Mercado'
    product_path = r'/produto/\d+/[^/]+/?'


class CarrefourMercadoAdapter(GroceryAdapter):
    domain = 'mercado.carrefour.com.br'
    name = 'Carrefour Mercado'
    product_path = r'/produto/[^/]+-\d+/?'

    def discovery_url(self, query):
        from ..models import normalize
        words = set(normalize(query).split())
        if words & {'picanha', 'picanhas'}:
            return ('https://mercado.carrefour.com.br/categoria/'
                    'acougue-e-peixaria/carnes-bovinas/picanha/')
        return None


class BoaSupermercadosAdapter(GroceryAdapter):
    domain = 'boasupermercados.com.br'
    name = 'Boa Supermercados'
    product_path = r'/[^/]+/p/?'
