"""Schema.org e dados Next.js do produto selecionado, observados na loja oficial."""
import json
import re
from urllib.parse import urlsplit, parse_qs, unquote

from bs4 import BeautifulSoup

from .base import ReadError, tail
from .public_store import PublicStoreAdapter
from ..models import money, normalize


class BrastempAdapter(PublicStoreAdapter):
    name = 'Brastemp oficial'
    domain = 'brastemp.com.br'
    sitemap_urls = ('https://www.brastemp.com.br/sitemap/product-0.xml',
                    'https://www.brastemp.com.br/sitemap/product-1.xml')

    def is_product_url(self, url):
        p = urlsplit(url)
        return ((p.hostname or '').removeprefix('www.') == self.domain
                and bool(re.fullmatch(r'/[^/]+/p/?', p.path)))

    def sitemap_title(self, url):
        return unquote(urlsplit(url).path.strip('/').split('/')[0]).replace('-', ' ')

    def selected_product(self, soup):
        scripts = soup.select('script#__NEXT_DATA__[type="application/json"]')
        if not scripts:
            return None
        if len(scripts) != 1:
            raise ReadError('structured_product_missing_or_ambiguous')
        try:
            product = json.loads(scripts[0].get_text())['props']['pageProps']['data']['product']
            if not isinstance(product, dict):
                raise TypeError
            return product
        except (ValueError, KeyError, TypeError):
            raise ReadError('structured_product_missing_or_ambiguous') from None

    def parse(self, html, url):
        readings = super().parse(html, url)
        soup = BeautifulSoup(html, 'html.parser')
        product = self.selected_product(soup)
        if product is None:
            return readings
        from ..discovery import documents
        products = [p for p in documents(soup) if p.get('@type') == 'Product']
        if len(products) != 1:
            raise ReadError('structured_product_missing_or_ambiguous')
        sku = str(product.get('sku', ''))
        if not sku or str(products[0].get('sku', '')) != sku:
            raise ReadError('conflicting_product_identifiers')
        requested = parse_qs(urlsplit(url).query).get('idsku', [])
        suffix = re.search(r'-(\d{6,})/p/?$', urlsplit(url).path)
        if (requested and requested != [sku]) or (suffix and suffix[1] != sku):
            raise ReadError('different_model')
        gtin = str(product.get('gtin', ''))
        if readings[0].identifiers.get('gtin') and readings[0].identifiers['gtin'] != gtin.zfill(14):
            raise ReadError('conflicting_product_identifiers')
        headings = soup.select('h1')
        group = product.get('isVariantOf', {})
        if not isinstance(group, dict):
            raise ReadError('structured_product_missing_or_ambiguous')
        full_title = group.get('name', '')
        if (len(headings) != 1 or not isinstance(full_title, str)
                or normalize(headings[0].get_text(' ', strip=True)) != normalize(full_title)
                or not set(normalize(readings[0].title).split()) <= set(normalize(full_title).split())):
            raise ReadError('different_model')
        variants = group.get('skuVariants', {})
        active = variants.get('activeVariations', {}) if isinstance(variants, dict) else {}
        voltage = active.get('Voltagem', '') if isinstance(active, dict) else ''
        properties = product.get('additionalProperty', [])
        if not isinstance(properties, list):
            raise ReadError('structured_product_missing_or_ambiguous')
        declared = {p.get('value') for p in properties if isinstance(p, dict) and p.get('name') == 'Voltagem'}
        if voltage and declared and declared != {voltage}:
            raise ReadError('conflicting_product_identifiers')
        for reading in readings:
            reading.title = full_title.strip()
            if isinstance(voltage, str) and re.fullmatch(r'(?:110|115|127|220|240)V', voltage):
                reading.title += ' · ' + voltage
                reading.identifiers['voltage'] = voltage
            model = product.get('productGroupReference', '')
            if isinstance(model, str) and re.fullmatch(r'[A-Za-z0-9-]{3,30}', model):
                reading.identifiers['model'] = normalize(model)
        aggregate = product.get('offers', {})
        offers = aggregate.get('offers', []) if isinstance(aggregate, dict) else []
        if len(readings) == 1 and isinstance(offers, list) and len(offers) == 1 and isinstance(offers[0], dict):
            offer, reading = offers[0], readings[0]
            if reading.price is not None and (money(offer.get('price')) != reading.price
                    or offer.get('priceCurrency') != reading.currency):
                raise ReadError('ambiguous_offer_variants')
            if reading.price is not None:
                expected_stock = {'InStock': 'in_stock', 'OutOfStock': 'out_of_stock', 'SoldOut': 'out_of_stock'}.get(tail(offer.get('availability')))
                if expected_stock and reading.stock != 'unknown' and reading.stock != expected_stock:
                    raise ReadError('ambiguous_offer_variants')
                seller = offer.get('seller', {})
                if isinstance(seller, dict) and not reading.seller:
                    identifier = str(seller.get('identifier', ''))
                    reading.seller = seller.get('name', '') or ('Vendedor ID ' + identifier if re.fullmatch(r'[A-Za-z0-9_-]{1,60}', identifier) else '')
                # Uma parcela sem juros com total explícito, nunca valor de parcela de N vezes.
                cards = {'American Express', 'Visa', 'Mastercard', 'Elo', 'Diners', 'Hipercard'}
                plans = product.get('availableInstallments', [])
                for plan in plans if isinstance(plans, list) else []:
                    if (isinstance(plan, dict) and type(plan.get('installmentNumber')) is int and plan['installmentNumber'] == 1
                            and plan.get('installmentInterest') == 0
                            and plan.get('installmentPaymentSystemName') in cards
                            and money(plan.get('totalValuePlusInterestRate')) == reading.price
                            and money(plan.get('installmentValue')) == reading.price):
                        reading.payment = reading.payment or 'Cartão à vista (' + plan['installmentPaymentSystemName'] + ')'
                        break
        return readings
