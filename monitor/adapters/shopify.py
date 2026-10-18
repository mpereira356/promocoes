"""Dados Shopify publicados no proprio HTML, sem APIs privadas ou checkout."""
import json
import re
from urllib.parse import urlsplit, parse_qs

from bs4 import BeautifulSoup

from .base import StructuredAdapter, ReadError, product_image
from ..models import Reading, normalize


class ShopifyAdapter(StructuredAdapter):
    domain = ''
    product_selector = ''

    def is_product_url(self, url):
        p = urlsplit(url)
        return ((p.hostname or '').removeprefix('www.') == self.domain
                and bool(re.fullmatch(r'/products/[a-z0-9][a-z0-9-]*/?', p.path)))

    def product(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('structured_product_missing_or_ambiguous')
        soup = BeautifulSoup(html, 'html.parser')
        scripts = soup.select(self.product_selector)
        if len(scripts) != 1:
            raise ReadError('structured_product_missing_or_ambiguous')
        try:
            data = json.loads(scripts[0].get_text())
            data = data['productJSON'] if self.domain == 'sensetup.com.br' else data
        except (ValueError, TypeError, KeyError):
            raise ReadError('structured_product_missing_or_ambiguous') from None
        headings = soup.find_all('h1')
        if (not isinstance(data, dict) or not isinstance(data.get('title'), str)
                or len(headings) != 1
                or normalize(headings[0].get_text(' ', strip=True)) != normalize(data['title'])
                or data.get('handle') != urlsplit(url).path.rstrip('/').rsplit('/', 1)[-1]):
            raise ReadError('different_model')
        currencies = re.findall(r'Shopify\.currency\s*=\s*(\{[^;]+\})\s*;', html)
        try:
            if len(currencies) != 1 or json.loads(currencies[0]).get('active') != 'BRL':
                raise ValueError
        except (ValueError, TypeError):
            raise ReadError('currency_not_confirmed') from None
        return data

    def variants(self, data, url):
        variants = data.get('variants')
        if (not isinstance(variants, list) or not variants
                or any(not isinstance(v, dict) for v in variants)):
            raise ReadError('ambiguous_offer_variants')
        ids = [str(v.get('id', '')) for v in variants]
        if not all(i.isdigit() for i in ids) or len(set(ids)) != len(ids):
            raise ReadError('ambiguous_offer_variants')
        selection = parse_qs(urlsplit(url).query).get('variant', [])
        if selection:
            if len(selection) != 1 or selection[0] not in ids:
                raise ReadError('ambiguous_offer_variants')
            return [variants[ids.index(selection[0])]]
        return variants

    def parse(self, html, url):
        data = self.product(html, url)
        variants = self.variants(data, url)
        prices = [v.get('price') for v in variants]
        valid = all(type(p) is int and p > 0 for p in prices)
        common = valid and len(set(prices)) == 1
        states = [v.get('available') for v in variants]
        stock = ('in_stock' if all(v is True for v in states) else
                 'out_of_stock' if all(v is False for v in states) else 'unknown')
        title = data['title']
        if len(variants) == 1 and variants[0].get('title') not in (None, '', 'Default Title'):
            title += ' - ' + str(variants[0]['title'])
        image = data.get('featured_image')
        if len(variants) == 1:
            variant_image = variants[0].get('featured_image')
            if isinstance(variant_image, dict):
                image = variant_image.get('src') or image
        identifiers = {}
        if isinstance(data.get('vendor'), str):
            identifiers['brand'] = normalize(data['vendor'])
        # SKU interno da loja nao e MPN nem prova de identidade entre lojas.
        return [Reading(title, '', '', '', prices[0] if common else None, stock,
                        image=product_image(image, url), identifiers=identifiers,
                        starting_price=min(prices) if valid and not common else None,
                        starting_price_url=url if valid and not common else '')]
