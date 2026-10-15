from .base import StructuredAdapter
from bs4 import BeautifulSoup
from dataclasses import replace
import re
from ..models import normalize
from ..display_money import display_money


class PichauAdapter(StructuredAdapter):
    name = "Pichau"
    sitemap_urls = ("https://www.pichau.com.br/media/sitemap.xml",)

    def parse(self, html, url):
        readings = super().parse(html, url)
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
