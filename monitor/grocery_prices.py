"""Public regional unit prices, separate from payment-specific offers."""
import json
import re
import time
import httpx
from types import SimpleNamespace
from urllib.parse import urlsplit, urljoin, urlencode

from .adapters.base import ReadError, product_image, nodes
from .models import Reading, money, normalize


class GroceryPrices:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.extra_api = None
        self.regions = {}
        self.status = {}
        self.clients = {}
        self.boa_operations = None

    @property
    def mode(self):
        return getattr(getattr(self.fetcher, 'config', None), 'grocery_mode', 'delivery')

    def for_visit(self, reading):
        if self.mode == 'visit':
            reading.identifiers.update(shopping_mode='visit', region_verified='true',
                                       price_verified='true', physical_stock='unknown', delivery_verified='unknown')
            reading.seller = reading.seller.replace(' · CEP ', ' · visita à loja · CEP ', 1)
        return reading

    async def close(self):
        if self.extra_api is not None:
            await self.extra_api.close()
        for client in self.clients.values():
            await client.aclose()

    async def extra_json(self, path, payload=None):
        from .network import Fetcher
        if not (path == '/ex/search/search' and payload is not None
                or re.fullmatch(r'/ex/delivery-v2/ecom/deliveryOptions\?zipCode=[0-9]{8}', path)
                or re.fullmatch(r'/ex/v4/products/ecom/[0-9]+/bestPrices\?storeId=[0-9]+&sellType=&isClienteMais=false', path)):
            raise ReadError('regional_request_not_allowed')
        if self.extra_api is None:
            self.extra_api = Fetcher(SimpleNamespace(domains=('api.vendas.gpa.digital',),
                                                    browser=False, delay=self.fetcher.config.delay))
        url = 'https://api.vendas.gpa.digital' + path
        await self.extra_api.allowed_by_robots(url)
        text, _ = await self.extra_api.request(url, check_robots=True, public_post=payload)
        try:
            result = json.loads(text)
        except (ValueError, TypeError):
            raise ReadError('regional_response_invalid') from None
        if not isinstance(result, dict):
            raise ReadError('regional_response_invalid')
        return result

    async def extra_store(self, cep):
        if not re.fullmatch(r'[0-9]{8}', cep):
            raise ReadError('regional_request_not_allowed')
        key = ('extra', cep, self.mode)
        cached = self.regions.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        response = await self.extra_json('/ex/delivery-v2/ecom/deliveryOptions?zipCode=' + cep)
        options = response.get('deliveryTypes')
        if not isinstance(options, list):
            raise ReadError('regional_response_invalid')
        delivery = next((item for item in options if isinstance(item, dict)
                         and (self.mode == 'visit' or item.get('type') == 'normal') and type(item.get('storeid')) is int
                         and item['storeid'] > 0 and item.get('storeName')), None)
        if delivery is None:
            raise ReadError('regional_delivery_unavailable')
        self.regions[key] = (time.monotonic() + 300, delivery)
        return delivery

    async def discover_extra(self, query, cep):
        from .adapters.groceries import ExtraMercadoAdapter
        from .discovery import LinkCandidate
        delivery = await self.extra_store(cep)
        response = await self.extra_json('/ex/search/search', {
            'terms': query, 'page': 1, 'sortBy': 'relevance', 'resultsPerPage': 12,
            'allowRedirect': False, 'storeId': delivery['storeid'], 'department': 'ecom',
            'customerPlus': False, 'partner': 'fallback'})
        products = response.get('products')
        if not isinstance(products, list):
            raise ReadError('regional_response_invalid')
        result = []
        for item in products[:12]:
            if not isinstance(item, dict):
                continue
            url, name = item.get('urlDetails'), item.get('name')
            if not isinstance(url, str) or not isinstance(name, str) or not ExtraMercadoAdapter().is_product_url(url):
                continue
            route = re.fullmatch(r'/produto/([0-9]+)/[^/]+/?', urlsplit(url).path)
            if route and route[1] == str(item.get('id')):
                result.append(LinkCandidate(url, name, 'Extra Mercado: busca pública regional'))
        return result

    async def read(self, parser, html, url, cep):
        if parser.domain == 'boasupermercados.com.br':
            return await self.boa(parser, html, url, cep)
        if parser.domain == 'mercado.carrefour.com.br':
            return await self.carrefour(parser, url, cep)
        if parser.domain == 'atacadao.com.br':
            return await self.atacadao(parser, html, url, cep)
        if parser.domain != 'extramercado.com.br':
            readings = parser.parse(html, url)
            for reading in readings:
                reading.identifiers['postal_code'] = cep
                reading.identifiers['regional_reason'] = 'Preço regional ainda não validado nesta loja.'
            return readings
        product_id = re.fullmatch(r'/produto/([0-9]+)/[^/]+/?', urlsplit(url).path)
        if not product_id or not re.fullmatch(r'[0-9]{8}', cep):
            raise ReadError('regional_request_not_allowed')
        delivery = await self.extra_store(cep)
        response = await self.extra_json('/ex/v4/products/ecom/' + product_id[1]
            + '/bestPrices?storeId=' + str(delivery['storeid']) + '&sellType=&isClienteMais=false')
        product = response.get('content')
        if (response.get('status') != 'success' or not isinstance(product, dict)
                or str(product.get('id')) != product_id[1]
                or not isinstance(product.get('name'), str)):
            raise ReadError('regional_response_invalid')
        # Use API identity tied to the same individual URL, never search snippets.
        details = re.fullmatch(r'/produto/([0-9]+)/[^/]+/?', str(product.get('urlDetails', '')))
        if not details or details[1] != product_id[1]:
            raise ReadError('different_model')
        from bs4 import BeautifulSoup
        headings = BeautifulSoup(html, 'html.parser').select('h1')
        if headings and any(normalize(h.get_text(' ', strip=True)) != normalize(product['name']) for h in headings):
            raise ReadError('conflicting_product_title')
        infos = product.get('sellInfos')
        offers = [item for item in infos if isinstance(item, dict)
                  and item.get('storeId') == delivery['storeid'] and item.get('sellType') == '1P'] if isinstance(infos, list) else []
        if len(offers) != 1:
            raise ReadError('regional_response_invalid')
        offer = offers[0]
        unit = offer.get('variableWeightPrice')
        # A pack total (e.g. 1.5 kg) must never be passed off as its per-kg price.
        if (product.get('variableWeight') is not True or not isinstance(unit, dict)
                or not re.match(r'^1\s*kg\s*-\s*R\$', str(offer.get('comparativePrice', '')), re.I)):
            raise ReadError('regional_unit_unverified')
        price = money(unit.get('sellPrice'))
        printed = re.fullmatch(r'1\s*kg\s*-\s*R\$\s*([0-9.]+,[0-9]{2})', str(offer.get('comparativePrice', '')), re.I)
        if not printed or money(printed[1].replace('.', '').replace(',', '.')) != price:
            raise ReadError('regional_unit_unverified')
        if (not price or unit.get('productPromotions') not in (None, [])
                or offer.get('homogeneousKit') or offer.get('nominalPrice')):
            raise ReadError('regional_terms_unverified')
        storage = next((state for state in ('resfriada', 'congelada')
                        if state in normalize(product['name']).split()), '')
        if not storage:
            raise ReadError('regional_terms_unverified')
        ids = {'brand': normalize(str(product.get('brand', ''))),
               'postal_code': cep, 'price_unit': 'kg', 'price_basis': 'regional_public_unit',
               'store_id': str(delivery['storeid']), 'grocery_product_id': product_id[1],
               'delivery_verified': 'true', 'storage': storage}
        seller = (parser.name + ' · ' + str(delivery['storeName']) + ' · CEP ' + cep[:5] + '-' + cep[5:])
        stock = ('in_stock' if offer.get('stock') is True and type(offer.get('stockQuantity')) is int
                 and offer['stockQuantity'] > 0 else 'out_of_stock' if offer.get('stock') is False else 'unknown')
        reading = Reading(product['name'] + ' [preço por kg]', seller,
                          storage.capitalize() + ' · preço por kg', '', price, stock,
                          image=product_image('https://static.extramercado.com.br' + str(product.get('thumbPath', '')), url),
                          identifiers=ids)
        reading.identifiers['delivery_verified'] = ('true' if stock == 'in_stock' and delivery.get('type') == 'normal' else 'unknown')
        self.for_visit(reading)
        address = delivery.get('address')
        if isinstance(address, dict):
            # This is the public store address in the delivery option, never the shopper's address.
            reading.identifiers['store_address'] = ', '.join(str(address[k]) for k in
                ('street', 'addressNumber', 'neighborhood', 'city', 'state') if address.get(k))
        if stock != 'in_stock' and not reading.visit_listing:
            reading.price = None
            reading.identifiers.update(regional_price_pending='true',
                regional_reason='Estoque regional não confirmado para este produto e CEP; sem preço para acompanhar.')
        self.status[parser.domain] = {'postal_code': cep, 'store': str(delivery['storeName']),
                                      'stock': stock, 'price_unit': 'kg', 'mode': self.mode}
        return [reading]

    async def boa_query(self, operation, variables):
        from bs4 import BeautifulSoup
        allowed = {'ValidateSession', 'ClientManyProductsQuery', 'ClientProductQuery'}
        if operation not in allowed:
            raise ReadError('regional_request_not_allowed')
        origin = 'https://www.boasupermercados.com.br'
        if self.boa_operations is None:
            html, _ = await self.fetcher.html(origin + '/')
            scripts = BeautifulSoup(html, 'html.parser').select('script[src]')
            app = next((s['src'] for s in scripts if '/_app-' in s['src']), None)
            if not app:
                raise ReadError('regional_response_invalid')
            url = urljoin(origin, app)
            _, domain = self.fetcher.canonical(url)
            if domain != 'boasupermercados.com.br':
                raise ReadError('regional_request_not_allowed')
            await self.fetcher.allowed_by_robots(url)
            text, _ = await self.fetcher.request(url, check_robots=True)
            operations = dict(re.findall(r'operationName:"([^"]+)",operationHash:"([a-f0-9]{40})"', text))
            self.boa_operations = {name: operations[name] for name in allowed if name in operations}
        operation_hash = self.boa_operations.get(operation)
        if not operation_hash:
            raise ReadError('regional_response_invalid')
        args = {'operationName': operation, 'operationHash': operation_hash}
        if operation != 'ValidateSession':
            args['variables'] = json.dumps(variables, separators=(',', ':'))
        url = origin + '/api/graphql?' + urlencode(args)
        await self.fetcher.allowed_by_robots(url)
        text, _ = await self.fetcher.request(url, check_robots=True, public_post=(
            {**args, 'variables': variables} if operation == 'ValidateSession' else None))
        try:
            response = json.loads(text)
            if response.get('errors') or not isinstance(response.get('data'), dict):
                raise ValueError()
            return response['data']
        except (ValueError, TypeError, AttributeError):
            raise ReadError('regional_response_invalid') from None

    async def boa_session(self, cep):
        if not re.fullmatch(r'[0-9]{8}', cep):
            raise ReadError('regional_request_not_allowed')
        key = ('boa', cep)
        cached = self.regions.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        data = await self.boa_query('ValidateSession', {'session': {
            'currency': {'code': 'BRL', 'symbol': 'R$'}, 'locale': 'pt-BR',
            'channel': '{"salesChannel":"1","regionId":""}', 'country': 'BRA',
            'deliveryMode': None, 'addressType': 'residential', 'postalCode': cep,
            'geoCoordinates': None, 'person': None}, 'search': ''})
        session = data.get('validateSession')
        try:
            if (not isinstance(session, dict) or session.get('postalCode') != cep
                    or session.get('country') != 'BRA' or session.get('currency', {}).get('code') != 'BRL'
                    or not json.loads(session['channel']).get('regionId')):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ReadError('regional_delivery_unavailable') from None
        self.regions[key] = (time.monotonic() + 300, session)
        return session

    async def discover_boa(self, query, cep):
        from .discovery import LinkCandidate
        session = await self.boa_session(cep)
        data = await self.boa_query('ClientManyProductsQuery', {
            'first': 12, 'after': '0', 'sort': 'score_desc', 'term': query,
            'selectedFacets': [{'key': 'channel', 'value': session['channel']},
                               {'key': 'locale', 'value': 'pt-BR'}]})
        edges = data.get('search', {}).get('products', {}).get('edges')
        if not isinstance(edges, list):
            raise ReadError('regional_response_invalid')
        result = []
        for edge in edges[:12]:
            node = edge.get('node') if isinstance(edge, dict) else None
            if not isinstance(node, dict) or not isinstance(node.get('name'), str):
                continue
            slug, sku = node.get('slug'), node.get('sku')
            if (isinstance(slug, str) and re.fullmatch(r'[a-z0-9-]+', slug)
                    and re.fullmatch(r'[0-9]+', str(sku)) and slug.endswith('-' + str(sku))):
                result.append(LinkCandidate('https://www.boasupermercados.com.br/' + slug + '/p',
                                            node['name'], 'Boa: busca pública regional'))
        return result

    async def boa(self, parser, html, url, cep):
        route = re.fullmatch(r'/[^/]+-([0-9]+)/p/?', urlsplit(url).path)
        if not route:
            raise ReadError('different_model')
        session = await self.boa_session(cep)
        data = await self.boa_query('ClientProductQuery', {'locator': [
            {'key': 'id', 'value': route[1]}, {'key': 'channel', 'value': session['channel']},
            {'key': 'locale', 'value': 'pt-BR'}]})
        product = data.get('product')
        if not isinstance(product, dict) or str(product.get('sku')) != route[1] or not isinstance(product.get('name'), str):
            raise ReadError('different_model')
        offers = product.get('offers', {}).get('offers')
        if not isinstance(offers, list) or len(offers) != 1:
            raise ReadError('regional_response_invalid')
        offer = offers[0]
        if not isinstance(offer, dict):
            raise ReadError('regional_response_invalid')
        if offer.get('availability') != 'https://schema.org/OutOfStock':
            # The observed payload omits measurementUnit. Never guess whether
            # a positive price is the kg rate or the 1.5kg estimated pack total.
            raise ReadError('regional_unit_unverified')
        self.status[parser.domain] = {'postal_code': cep, 'store': parser.name, 'stock': 'out_of_stock'}
        return [Reading(product['name'], '', '', '', None, 'out_of_stock', identifiers={
            'regional_price_pending': 'true', 'postal_code': cep,
            'regional_reason': 'Produto indisponível no catálogo regional consultado para este CEP; sem preço para acompanhar.'})]

    async def atacadao(self, parser, html, url, cep):
        from bs4 import BeautifulSoup
        readings = parser.parse(html, url)
        products = []
        for script in BeautifulSoup(html, 'html.parser').select('script[type="application/ld+json"]'):
            try:
                products.extend(n for n in nodes(json.loads(script.get_text())) if n.get('@type') == 'Product')
            except (ValueError, TypeError):
                continue
        if len(products) != 1 or not re.fullmatch(r'[0-9]+', str(products[0].get('sku', ''))):
            raise ReadError('regional_response_invalid')
        sku = str(products[0]['sku'])
        region_url = 'https://www.atacadao.com.br/api/checkout/pub/regions?postalCode=' + cep + '&sc=1&country=BRA'
        await self.fetcher.allowed_by_robots(region_url)
        text, _ = await self.fetcher.request(region_url, check_robots=True)
        try:
            regions = json.loads(text)
        except ValueError:
            raise ReadError('regional_response_invalid') from None
        sellers = {}
        if isinstance(regions, list):
            for region in regions:
                for seller in region.get('sellers', []) if isinstance(region, dict) else []:
                    if (isinstance(seller, dict) and re.fullmatch(r'atacadaobr[0-9]+', str(seller.get('id', '')))
                            and isinstance(seller.get('name'), str)):
                        sellers[seller['id']] = seller['name']
        requested = list(sellers)[:4]
        if not requested:
            raise ReadError('regional_delivery_unavailable')
        simulation_url = 'https://www.atacadao.com.br/api/checkout/pub/orderForms/simulation?sc=1'
        text, _ = await self.fetcher.request(simulation_url, public_post={
            'items': [{'id': sku, 'quantity': 1, 'seller': seller} for seller in requested],
            'country': 'BRA', 'postalCode': cep})
        try:
            response = json.loads(text)
        except ValueError:
            raise ReadError('regional_response_invalid') from None
        if not isinstance(response, dict) or not isinstance(response.get('items'), list) or not isinstance(response.get('logisticsInfo'), list):
            raise ReadError('regional_response_invalid')
        logistics = {i.get('itemIndex'): i for i in response['logisticsInfo'] if isinstance(i, dict)}
        result = []
        storage = next((state for state in ('resfriada', 'congelada')
                        if state in normalize(str(products[0].get('description', '')) + ' ' + readings[0].title).split()), '')
        for index, item in enumerate(response['items']):
            if not isinstance(item, dict) or index >= len(requested):
                continue
            slas = logistics.get(index, {}).get('slas', [])
            unit_price = (item.get('priceDefinition') or {}).get('pricePerUnit')
            if (str(item.get('id')) != sku or item.get('seller') != requested[index]
                    or item.get('requestIndex') != index
                    or item.get('measurementUnit') != 'kg' or item.get('unitMultiplier') != 1
                    or type(unit_price) is not int or unit_price <= 0
                    or unit_price != item.get('sellingPrice') or item.get('priceTags')
                    or not storage):
                continue
            deliverable = (item.get('availability') == 'available' and isinstance(slas, list)
                           and any(isinstance(sla, dict) and sla.get('deliveryChannel') == 'delivery' for sla in slas))
            if not deliverable and self.mode != 'visit':
                continue
            stock = {'available': 'in_stock', 'withoutStock': 'out_of_stock'}.get(item.get('availability'), 'unknown')
            source = readings[0]
            ids = dict(source.identifiers)
            ids.pop('regional_price_pending', None)
            ids.pop('regional_reason', None)
            ids.update(postal_code=cep, price_unit='kg', price_basis='regional_public_unit',
                       store_id=item['seller'], grocery_product_id=sku,
                       delivery_verified='true' if deliverable else 'unknown', storage=storage)
            result.append(self.for_visit(Reading(source.title + ' [preço por kg]',
                parser.name + ' · ' + sellers[item['seller']] + ' · CEP ' + cep[:5] + '-' + cep[5:],
                storage.capitalize() + ' · preço por kg', '', unit_price, stock,
                image=source.image, identifiers=ids)))
        self.status[parser.domain] = {'postal_code': cep, 'checked_stores': len(requested),
                                     'stock': result[0].stock if result else 'unverified_delivery_or_stock', 'mode': self.mode}
        if result:
            return result
        for reading in readings:
            reading.identifiers.update(postal_code=cep,
                regional_reason='Nas lojas consultadas, não houve estoque e entrega confirmados para este produto e CEP.')
        return readings

    async def carrefour(self, parser, url, cep):
        from .public_payloads import router_data
        from bs4 import BeautifulSoup
        if not re.fullmatch(r'[0-9]{8}', cep):
            raise ReadError('regional_request_not_allowed')
        key = (parser.domain, cep, self.mode)
        if key not in self.clients:
            if len(self.clients) >= 4:
                oldest = next(iter(self.clients))
                await self.clients.pop(oldest).aclose()
                self.regions.pop(oldest, None)
            self.clients[key] = httpx.AsyncClient(timeout=30, follow_redirects=False,
                headers={'User-Agent': 'PriceMonitor/1.0 (+personal price monitoring)'})
        client = self.clients[key]
        region = self.regions.get(key)
        if not region or region[0] < time.monotonic():
            text, _ = await self.fetcher.request('https://mercado.carrefour.com.br/action/set-regionalization',
                client=client, public_post={'CEP': cep[:5] + '-' + cep[5:], 'source': 'cep-component', 'page-view-id': ''})
            try:
                response = json.loads(text)['result']
                if (str(response.get('postalCode', '')).replace('-', '') != cep
                        or not response.get('regionId')
                        or (self.mode != 'visit' and response.get('regionContextProps', {}).get('deliveryType') != 'residential')):
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise ReadError('regional_delivery_unavailable') from None
            self.regions[key] = (time.monotonic() + 300, response['regionId'])
        await self.fetcher.allowed_by_robots(url)
        html, final = await self.fetcher.request(url, check_robots=True, client=client, fresh=True)
        if final != url:
            raise ReadError('different_model')
        data = router_data(html).get('produto-slug')
        if not isinstance(data, dict) or str(data.get('zipCode', '')).replace('-', '') != cep:
            raise ReadError('regional_response_invalid')
        product = data.get('product')
        route = re.fullmatch(r'/produto/[^/]+-([0-9]+)/?', urlsplit(url).path)
        schema = data.get('schema')
        if not isinstance(product, dict) or not isinstance(schema, dict) or not route:
            raise ReadError('regional_response_invalid')
        if str(schema.get('sku', '')) != route[1] or schema.get('offers', {}).get('priceCurrency') != 'BRL':
            raise ReadError('different_model')
        title = product.get('productName')
        headings = BeautifulSoup(html, 'html.parser').select('h1[data-testid="pdp-product-name"]')
        if (not isinstance(title, str) or len(headings) != 1
                or normalize(headings[0].get_text(' ', strip=True)) != normalize(title)):
            raise ReadError('conflicting_product_title')
        items = product.get('items')
        if not isinstance(items, list) or len(items) != 1 or items[0].get('measurementUnit') != 'kg':
            raise ReadError('regional_unit_unverified')
        sellers = items[0].get('sellers', [])
        defaults = [s for s in sellers if isinstance(s, dict) and s.get('sellerDefault') is True]
        if len(defaults) != 1:
            raise ReadError('regional_terms_unverified')
        seller = defaults[0]
        offer = seller.get('commertialOffer')
        if not isinstance(offer, dict) or not seller.get('sellerId') or not seller.get('sellerName'):
            raise ReadError('regional_response_invalid')
        price = money(offer.get('Price'))
        # The storefront explicitly exposes unit Price and estimated calculatedPrice.
        # Never divide the schema pack total by the approximate weight.
        if not price or offer.get('teasers') or offer.get('GiftSkuIds') or offer.get('BuyTogether'):
            raise ReadError('regional_terms_unverified')
        printed = re.findall(r'R\$\s*([0-9.]+,[0-9]{2})\s*/\s*kg',
                             headings[0].parent.parent.get_text(' ', strip=True), re.I)
        if not printed or any(money(p.replace('.', '').replace(',', '.')) != price for p in printed):
            raise ReadError('regional_unit_unverified')
        storage = next((state for state in ('resfriada', 'congelada') if state in normalize(title).split()), '')
        if not storage:
            raise ReadError('regional_terms_unverified')
        quantity = offer.get('AvailableQuantity')
        stock = 'in_stock' if type(quantity) in (int, float) and quantity > 0 else 'out_of_stock'
        ids = {'postal_code': cep, 'price_unit': 'kg', 'price_basis': 'regional_public_unit',
               'store_id': str(seller['sellerId']), 'grocery_product_id': route[1],
               'delivery_verified': 'true', 'storage': storage}
        reading = Reading(title + ' [preço por kg]', str(seller['sellerName']) + ' · CEP ' + cep[:5] + '-' + cep[5:],
            storage.capitalize() + ' · preço por kg', '', price, stock,
            image=product_image(schema.get('image'), url), identifiers=ids)
        self.for_visit(reading)
        if stock != 'in_stock' and not reading.visit_listing:
            reading.price = None
            reading.identifiers.update(regional_price_pending='true',
                regional_reason='Produto sem estoque no catálogo regional consultado; sem preço para acompanhar.')
        self.status[parser.domain] = {'postal_code': cep, 'store': str(seller['sellerName']), 'stock': stock, 'mode': self.mode}
        return [reading]
