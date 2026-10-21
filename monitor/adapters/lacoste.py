"""Produtos da loja brasileira; variantes nunca herdam estoque de outra cor."""
import json
import re
from urllib.parse import urlsplit, urljoin, urlencode, parse_qs
from bs4 import BeautifulSoup
from .base import ReadError, nodes, tail
from .public_store import PublicStoreAdapter
from ..models import money, normalize


class LacosteAdapter(PublicStoreAdapter):
    name = 'Lacoste Brasil'
    domain = 'lacoste.com'
    # The search route is disallowed. Image sitemap titles are public product names.
    sitemap_urls = ('https://www.lacoste.com/br/sitemap_1-image.xml',)
    sitemap_image_titles = True

    def is_product_url(self, url):
        p = urlsplit(url)
        return ((p.hostname or '').removeprefix('www.') == self.domain
                and bool(re.fullmatch(r'/br/lacoste/(?:[^/]+/)*(?=[^/]*\d)[A-Za-z0-9_-]+\.html', p.path)))

    def search_url(self, query):
        return 'https://www.lacoste.com/br/search/?' + urlencode({'q': query})

    def product(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                products.extend(n for n in nodes(json.loads(script.get_text()))
                                if tail(n.get('@type')) == 'Product')
            except (ValueError, TypeError):
                continue
        # Recommendations cannot establish identity or price for the main item.
        matches = [p for p in products if p.get('url') and
                   urlsplit(urljoin(url, p['url'])).path == urlsplit(url).path]
        if len(matches) == 1:
            product = matches[0]
        elif len(products) == 1:
            product = products[0]
            if product.get('url') and not matches:
                requested = urlsplit(url).path.rsplit('/', 1)[-1].removesuffix('.html')
                sections = soup.select('.js-pdp-section[data-ean][data-ref-col]')
                offers = product.get('offers', [])
                offers = offers if isinstance(offers, list) else [offers]
                skus = {str(o.get('sku', '')) for o in offers if isinstance(o, dict)}
                if (len(sections) != 1 or not
                        ((requested == sections[0]['data-ean'] and requested in skus)
                         or requested == sections[0]['data-ref-col'])):
                    raise ReadError('different_model')
        else:
            raise ReadError('structured_product_missing_or_ambiguous')
        headings = soup.select('h1')
        if len(headings) != 1 or normalize(headings[0].get_text(' ', strip=True)) != normalize(str(product.get('name', ''))):
            raise ReadError('conflicting_product_title')
        selected_color = parse_qs(urlsplit(url).query).get('color', [''])[0]
        requested_size = parse_qs(urlsplit(url).query).get('size', [''])[0]
        own_size = parse_qs(urlsplit(product.get('url', '')).query).get('size', [''])[0]
        if requested_size and requested_size != own_size:
            raise ReadError('ambiguous_offer_variants')
        own_color = parse_qs(urlsplit(urljoin(url, product.get('url', ''))).query).get('color', [''])[0]
        if selected_color and own_color and selected_color != own_color:
            raise ReadError('ambiguous_offer_variants')
        declared_color = str(product.get('color', ''))
        if selected_color and declared_color and declared_color != selected_color:
            # Color names may be accompanied by a separate code in the DOM.
            selected = soup.select('[data-color-code]')
            if own_color != selected_color and not any(n.get('data-color-code') == selected_color and
                       normalize(n.get_text(' ', strip=True)) == normalize(declared_color) for n in selected):
                raise ReadError('ambiguous_offer_variants')
        return soup, product

    def parse(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('individual_listing_required')
        soup, product = self.product(html, url)
        # Isolate the validated primary Product before using the shared parser.
        readings = super().parse('<script type="application/ld+json">' + json.dumps(product).replace('</', '<\\/') + '</script>', url)
        for reading in readings:
            reading.seller = reading.seller or self.name
            own_query = parse_qs(urlsplit(product.get('url', '')).query)
            reading.identifiers['color'] = parse_qs(urlsplit(url).query).get('color', [''])[0] or own_query.get('color', [''])[0] or str(product.get('color', ''))
            if own_query.get('size'):
                reading.identifiers['size'] = own_query['size'][0].upper()
            if isinstance(product.get('size'), (str, int)):
                reading.identifiers['size'] = str(product['size']).strip().upper()
            data = self.page_product(soup, product)
            if data:
                reading.identifiers['mpn'] = normalize(data['masterProductId'] + '-' + data['color']['id'])
                reading.identifiers['model'] = normalize(data['masterProductId'])
                reading.identifiers['color'] = data['color']['id']
                selected_size = parse_qs(urlsplit(product.get('url', '')).query).get('size', [''])[0]
                if selected_size:
                    reading.identifiers['size'] = selected_size.upper()
        return readings

    def page_product(self, soup, product):
        values = []
        for script in soup.select('script:not([src])'):
            match = re.search(r'\bwindow\.currentProduct\s*=\s*', script.get_text())
            if not match:
                continue
            try:
                data, _ = json.JSONDecoder().raw_decode(script.get_text()[match.end():])
            except (ValueError, TypeError):
                continue
            if (isinstance(data, dict) and isinstance(data.get('color'), dict)
                    and normalize(str(data.get('name', ''))) == normalize(product.get('name', ''))
                    and urlsplit(data['color'].get('url', '')).path == urlsplit(product.get('url', '')).path
                    and parse_qs(urlsplit(product.get('url', '')).query).get('color', [''])[0] == data['color'].get('id')
                    and isinstance(data.get('id'), str) and isinstance(data.get('masterProductId'), str)
                    and isinstance(data['color'].get('id'), str)
                    and self.product_section(soup, data) is not None):
                values.append(data)
        return values[0] if len(values) == 1 else None

    def product_section(self, soup, data):
        matches = [n for n in soup.select('.js-pdp-section')
                   if data['id'] in (n.get('data-ref-col'), n.get('data-ean'))
                   and n.get('data-ref-col') == data['masterProductId'] + '-' + data['color']['id']]
        return matches[0] if len(matches) == 1 else None

    def sizes(self, soup, product, reading):
        sizes = set()
        # Schema size is usable only for this individual in-stock offer.
        if reading.stock == 'in_stock' and isinstance(product.get('size'), (str, int)):
            sizes.add(str(product['size']).strip().upper())
        if reading.stock == 'in_stock' and reading.identifiers.get('size'):
            sizes.add(reading.identifiers['size'])
        # Explicit availability is required; merely displaying a size is insufficient.
        for node in soup.select('main [data-size][data-available]'):
            if node.find_parent('aside') or node.find_parent(attrs={'data-recommendations': True}):
                continue
            if (node.get('data-available', '').lower() == 'true' and not node.has_attr('disabled')
                    and node.get('aria-disabled') != 'true'):
                color = node.get('data-color-code', '')
                if not color or color == reading.identifiers.get('color'):
                    sizes.add(node['data-size'].strip().upper())
        return sorted(s for s in sizes if re.fullmatch(r'[A-Z0-9À-Ú., -]{1,12}', s))

    def reference_price(self, soup, product, reading):
        refs = set()
        offers = product.get('offers', [])
        for offer in offers if isinstance(offers, list) else [offers]:
            if not isinstance(offer, dict) or tail(offer.get('@type')) != 'Offer':
                continue
            if money(offer.get('price')) != reading.price or offer.get('priceCurrency') != 'BRL':
                continue
            specs = offer.get('priceSpecification', [])
            for spec in specs if isinstance(specs, list) else [specs]:
                if (isinstance(spec, dict) and tail(spec.get('priceType')) == 'StrikethroughPrice'
                        and spec.get('priceCurrency') == 'BRL'
                        and not any(spec.get(k) for k in ('validForMemberTier', 'eligibleCustomerType', 'eligibleQuantity'))):
                    value = money(spec.get('price'))
                    if value and value > reading.price:
                        refs.add(value)
        # DOM fallback only in the main product price block, excluding recommendations.
        blocks = soup.select('main .product-price, main [data-product-price]')
        if not refs and len(blocks) == 1:
            from ..display_money import display_money
            current = blocks[0].select('.sales .value, [data-current-price]')
            old = blocks[0].select('del, s, .price-standard, .price-original')
            if len(current) == len(old) == 1:
                value = display_money(current[0].get_text(' ', strip=True).replace('R$', '').strip())
                previous = display_money(old[0].get_text(' ', strip=True).replace('R$', '').strip())
                if value == reading.price and previous and previous > value:
                    refs.add(previous)
        data = self.page_product(soup, product)
        if not refs and data:
            from ..display_money import display_money
            section = self.product_section(soup, data)
            for block in section.select('.js-pdp-price'):
                old = block.select('del[aria-hidden="true"]')
                current = block.select('div[aria-hidden="true"]')
                if len(old) == len(current) == 1:
                    previous = display_money(old[0].get_text(strip=True).replace('R$', '').strip())
                    price = display_money(current[0].get_text(strip=True).replace('R$', '').strip())
                    if price == reading.price and previous and previous > price:
                        refs.add(previous)
        return refs.pop() if len(refs) == 1 else None
