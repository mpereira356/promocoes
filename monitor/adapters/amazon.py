"""Amazon: sem seletores de preco nao validados; exige oferta estruturada explicita."""
import re
from urllib.parse import urlsplit
from .base import StructuredAdapter, ReadError
from bs4 import BeautifulSoup
from ..models import Reading, normalize


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
        try:
            return super().parse(html, url)
        except ReadError as exc:
            if str(exc) != 'structured_product_missing_or_ambiguous':
                raise
        # IDs e texto observados em pagina real B08MPZ14FY em 15/10/2026.
        soup = BeautifulSoup(html, 'html.parser')
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
