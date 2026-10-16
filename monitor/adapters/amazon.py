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

    def is_product_url(self, url):
        p = urlsplit(url)
        return p.hostname in ('amazon.com.br', 'www.amazon.com.br') and bool(
            re.search(r'/(?:dp|gp/product)/[A-Z0-9]{10}(?:/|$)', p.path)
        )

    def parse(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('individual_listing_required')
        soup = BeautifulSoup(html, 'html.parser')
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
            return readings
        try:
            return super().parse(html, url)
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
                if normalize(label) == 'vendido por' and 0 < len(strings[index + 1]) <= 100
            }
            if len(sellers) == 1:
                seller = next(iter(sellers))
        # Buy Box pode trocar de vendedor. Nao inventar preco, vendedor, condicao ou Pix.
        return [Reading(titles[0].get_text(' ', strip=True), seller, '', '', None, stock)]

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
