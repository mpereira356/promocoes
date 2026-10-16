"""Amazon: oferta estruturada ou painel publico AOD observado em pagina real."""
import re
from urllib.parse import urlsplit, urljoin, parse_qs
from .base import StructuredAdapter, ReadError
from bs4 import BeautifulSoup
from ..models import Reading, normalize
from ..display_money import display_money


class AmazonAdapter(StructuredAdapter):
    name = 'Amazon Brasil'
    external_discovery = True

    def details_identifiers(self, soup, url):
        asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(url).path)
        fields = {}
        for row in soup.select('#productDetails_feature_div table.prodDetTable tr'):
            labels, values = row.find_all('th', recursive=False), row.find_all('td', recursive=False)
            if len(labels) == len(values) == 1:
                key = normalize(labels[0].get_text(' ', strip=True))
                fields.setdefault(key, set()).add(values[0].get_text(' ', strip=True))
        if not asin or fields.get('asin') != {asin[1]}:
            return {}
        result = {}
        for key, label in [('brand', 'nome da marca'), ('mpn', 'numero da peca')]:
            values = fields.get(label, set())
            if len(values) == 1:
                value = next(iter(values))
                if value and len(value) <= 120:
                    result[key] = normalize(value)
        return result

    def enrich_identifiers(self, readings, details):
        for reading in readings:
            if any(reading.identifiers.get(k) and reading.identifiers[k] != v for k, v in details.items()):
                raise ReadError('conflicting_product_identifiers')
            reading.identifiers = details | reading.identifiers
        return readings

    def price_requires_cart(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        return any('adicione este item ao seu carrinho' in normalize(n.get_text(' ', strip=True))
            for n in soup.select('#priceNotAvailable_feature_div'))

    def primary_price(self, soup, url):
        asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(url).path)
        if not asin or {n.get('value') for n in soup.select('input#ASIN')} != {asin[1]}:
            return None
        blocks = soup.select('#corePriceDisplay_desktop_feature_div .a-price.apex-pricetopay-value, '
            '#corePrice_feature_div .a-price.apex-pricetopay-value, #buybox .a-price.apex-pricetopay-value')
        prices = set()
        for block in blocks:
            values = set()
            for label in block.select('.a-offscreen'):
                text = label.get_text(' ', strip=True)
                if not text:
                    continue
                match = re.fullmatch(r'R\$\s*([\d.,]+)', text)
                amount = display_money(match[1]) if match else None
                if amount is None:
                    return None
                values.add(amount)
            symbols, whole, fraction = block.select('.a-price-symbol'), block.select('.a-price-whole'), block.select('.a-price-fraction')
            if len(symbols) == len(whole) == len(fraction) == 1:
                if symbols[0].get_text(strip=True) != 'R$' or not re.fullmatch(r'\d{2}', fraction[0].get_text(strip=True)):
                    return None
                amount = display_money(whole[0].get_text(strip=True).rstrip(',') + ',' + fraction[0].get_text(strip=True))
                if amount is None:
                    return None
                values.add(amount)
            if len(values) != 1:
                return None
            prices.update(values)
        return next(iter(prices)) if len(prices) == 1 else None

    def is_product_url(self, url):
        p = urlsplit(url)
        return p.hostname in ('amazon.com.br', 'www.amazon.com.br') and bool(
            re.search(r'/(?:dp|gp/product)/[A-Z0-9]{10}(?:/|$)', p.path)
        )

    def parse(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('individual_listing_required')
        soup = BeautifulSoup(html, 'html.parser')
        details = self.details_identifiers(soup, url)
        expected_asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(url).path)[1]
        actual_asins = {n.get('value') for n in soup.select('input#ASIN')}
        if actual_asins and actual_asins != {expected_asin}:
            raise ReadError('different_model')
        titles = soup.select('#productTitle')
        rows = soup.select('#aod-offer-list #aod-offer')
        if rows:
            if len(titles) != 1:
                raise ReadError('product_title_missing')
            title = titles[0].get_text(' ', strip=True)
            header_titles = {normalize(t.get_text(' ', strip=True)) for t in soup.select('#aod-asin-title-text')}
            if header_titles != {normalize(title)}:
                raise ReadError('conflicting_product_title')
            readings = []
            for row in rows[:20]:
                prices = set()
                invalid_price = False
                for block in row.select('[id^="aod-price-"]'):
                    for label in block.select('.apex-pricetopay-accessibility-label'):
                        match = re.fullmatch(r'R\$\s*([\d.,]+)', label.get_text(' ', strip=True))
                        amount = display_money(match[1]) if match else None
                        if amount:
                            prices.add(amount)
                        else:
                            invalid_price = True
                    for value in block.select('.a-price.apex-pricetopay-value'):
                        symbols = value.select('.a-price-symbol')
                        whole = value.select('.a-price-whole')
                        fraction = value.select('.a-price-fraction')
                        if len(symbols) == len(whole) == len(fraction) == 1 and symbols[0].get_text(strip=True) == 'R$':
                            major = whole[0].get_text(strip=True).rstrip(',')
                            minor = fraction[0].get_text(strip=True)
                            amount = display_money(major + ',' + minor) if re.fullmatch(r'\d{2}', minor) else None
                            if amount:
                                prices.add(amount)
                price = next(iter(prices)) if len(prices) == 1 and not invalid_price else None
                sellers = set()
                for link in row.select('#aod-offer-soldBy a[aria-label][href]'):
                    params = parse_qs(urlsplit(link['href']).query)
                    seller_id = params.get('seller', [''])[0]
                    if re.fullmatch(r'[A-Z0-9]+', seller_id):
                        sellers.add((seller_id, link.get_text(' ', strip=True)))
                seller = ''
                if len(sellers) == 1:
                    seller_id, seller_name = next(iter(sellers))
                    seller = f'{seller_name} (ID {seller_id})'
                headings = row.select('#aod-offer-heading')
                condition = {'novo': 'NewCondition', 'usado': 'UsedCondition', 'recondicionado': 'RefurbishedCondition'}.get(
                    normalize(headings[0].get_text(' ', strip=True)) if len(headings) == 1 else '', '')
                # O painel observado nao declara modalidade ou estoque explicitamente.
                readings.append(Reading(title, seller, condition, '', price, 'unknown'))
            keys = [(r.seller, r.condition, r.payment) for r in readings]
            if len(keys) != len(set(keys)):
                raise ReadError('ambiguous_offer_variants')
            return self.enrich_identifiers(readings, details)
        try:
            return self.enrich_identifiers(super().parse(html, url), details)
        except ReadError as exc:
            if str(exc) != 'structured_product_missing_or_ambiguous':
                raise
        # IDs e texto observados em pagina real B08MPZ14FY em 15/10/2026.
        titles = soup.select('#productTitle')
        if len(titles) != 1 or not titles[0].get_text(' ', strip=True):
            raise ReadError('product_title_missing')
        boxes = soup.select('#buybox')
        stock = 'unknown'
        seller = ''
        if len(boxes) == 1:
            text = normalize(boxes[0].get_text(' ', strip=True))
            if 'nao disponivel' in text and 'nao temos previsao' in text:
                stock = 'out_of_stock'
            strings = list(boxes[0].stripped_strings)
            sellers = {
                strings[index + 1] for index, label in enumerate(strings[:-1])
                if normalize(label) in ('vendido por', 'enviado vendido') and 0 < len(strings[index + 1]) <= 100
            }
            if len(sellers) == 1:
                seller = next(iter(sellers))
        price = None
        if len(boxes) == 1 and not self.price_requires_cart(html):
            price = self.primary_price(soup, url)
            asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(url).path)[1]
            sellers = set()
            for link in boxes[0].select('#sellerProfileTriggerId[href]'):
                params = parse_qs(urlsplit(link['href']).query)
                sid = params.get('seller', [''])[0]
                if params.get('asin') == [asin] and re.fullmatch(r'[A-Z0-9]+', sid):
                    sellers.add((sid, link.get_text(' ', strip=True)))
            if len(sellers) == 1:
                sid, name = next(iter(sellers))
                seller = f'{name} (ID {sid})'
            elif len(sellers) > 1:
                seller, price = '', None
            availability = {normalize(n.get_text(' ', strip=True)) for n in boxes[0].select('#availability')}
            if availability == {'em estoque'}:
                stock = 'unknown' if stock == 'out_of_stock' else 'in_stock'
        # O preço total não identifica sozinho Pix, parcelamento ou condição.
        return [Reading(titles[0].get_text(' ', strip=True), seller, '', '', price, stock, identifiers=details)]

    def buying_options_url(self, html, url):
        if not self.is_product_url(url):
            return None
        asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(url).path)
        if not asin:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for a in soup.select('#buybox-see-all-buying-choices a[href]'):
            target = urljoin(url, a['href'])
            p = urlsplit(target)
            if p.scheme == 'https' and p.hostname == urlsplit(url).hostname and re.match(r'^/gp/offer-listing/' + asin[1] + r'(?:/|$)', p.path):
                links.add(target)
        return next(iter(links)) if len(links) == 1 else None

    def hidden_price_panel_url(self, html, url):
        """URL do painel observada no redirecionamento real de opcoes de compra."""
        if not self.is_product_url(url):
            return None
        asin = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(url).path)
        soup = BeautifulSoup(html, 'html.parser')
        if asin and len(soup.select('#productTitle')) == 1 and soup.select('#priceNotAvailable_feature_div'):
            return urljoin(url, '/dp/' + asin[1] + '/ref=olp-opf-redir?aod=1')
        return None
