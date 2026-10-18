from .base import StructuredAdapter, ReadError, nodes
from bs4 import BeautifulSoup
from dataclasses import replace
import re
import json
from urllib.parse import urlsplit
from ..models import normalize, Reading
from ..display_money import display_money


class PichauAdapter(StructuredAdapter):
    name = "Pichau"
    sitemap_urls = ("https://www.pichau.com.br/media/sitemap.xml",)

    def parse(self, html, url):
        try:
            readings = super().parse(html, url)
        except ReadError as exc:
            if str(exc) != 'structured_product_missing_or_ambiguous':
                raise
            # Fallback validado no DOM fornecido pelo usuario. Nunca substituir
            # um Product ambiguo ou malformado por dados de outro bloco.
            soup = BeautifulSoup(html, 'html.parser')
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string or script.get_text())
                except (ValueError, TypeError):
                    raise exc
                for node in nodes(data):
                    types = node.get('@type', [])
                    if isinstance(types, str):
                        types = [types]
                    if not isinstance(types, list):
                        raise exc
                    if any(str(t).rstrip('/').split('/')[-1] == 'Product' for t in types):
                        raise exc
            headings = soup.select('h1[data-cy="product-page-title"]')
            if (urlsplit(url).hostname not in ('pichau.com.br', 'www.pichau.com.br')
                    or not self.is_product_url(url) or len(headings) != 1
                    or len(soup.find_all('h1')) != 1):
                raise exc
            title = headings[0].get_text(' ', strip=True)
            if not title:
                raise exc
            readings = [Reading(title, '', '', '', None)]
            result = self._pix_price(readings, html)
            if result[0].price is None:
                raise exc
            return result
        return self._pix_price(readings, html)

    def _pix_price(self, readings, html):
        if len(readings) != 1 or readings[0].currency != "BRL":
            return readings
        reading = readings[0]
        soup = BeautifulSoup(html, "html.parser")
        headings = soup.find_all("h1")
        if len(headings) != 1 or normalize(
            headings[0].get_text(" ", strip=True)
        ) != normalize(reading.title):
            return readings
        scope = headings[0]
        for _ in range(7):
            scope = scope.parent
            if scope is None:
                return readings
            prices = scope.select('div[class*="-price_vista-"]')
            if not prices:
                continue
            if len(prices) != 1:
                return readings
            block = prices[0].parent.get_text(" ", strip=True)
            if "no pix" not in normalize(block) or "a vista" not in normalize(block):
                return readings
            values = re.findall(r"R\$\s*([\d.,]+)", prices[0].get_text(" ", strip=True))
            if len(values) != 1:
                return readings
            price = display_money(values[0])
            if price is not None:
                return [replace(reading, price=price, payment="Pix")]
            return readings
        return readings

    def is_product_url(self, url):
        from urllib.parse import urlsplit

        path = urlsplit(url).path.strip("/")
        return bool(
            path
            and "/" not in path
            and "-" in path
            and not path.endswith((".xml", ".xml.gz"))
        )
