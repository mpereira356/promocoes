from .base import StructuredAdapter
from urllib.parse import urlencode, urljoin
from bs4 import BeautifulSoup
import re
from dataclasses import replace
from ..models import normalize
from ..display_money import display_money


class TerabyteAdapter(StructuredAdapter):
    name = "Terabyte"
    sitemap_urls = (
        "https://www.terabyteshop.com.br/sitemap-manus.xml",
        "https://www.terabyteshop.com.br/sitemap.xml",
    )

    def parse(self, html, url):
        readings = super().parse(html, url)
        soup = BeautifulSoup(html, "html.parser")
        sellers = {
            n.get_text(" ", strip=True).removeprefix("Vendido por:").strip()
            for n in soup.select(".cod-info .vendPor")
        }
        sellers.discard("")
        if len(sellers) == 1:
            for reading in readings:
                seller = next(iter(sellers))
                if reading.seller and normalize(reading.seller) != normalize(seller):
                    from .base import ReadError

                    raise ReadError("conflicting_seller")
                reading.seller = seller
        if len(readings) != 1 or readings[0].currency != "BRL":
            return readings
        reading = readings[0]
        headings = soup.find_all("h1")
        if len(headings) != 1 or normalize(
            headings[0].get_text(" ", strip=True)
        ) != normalize(reading.title):
            return readings
        prices = soup.select("#valVista")
        if len(prices) != 1:
            return readings
        values = re.findall(r"R\$\s*([\d.,]+)", prices[0].get_text(" ", strip=True))
        if len(values) != 1:
            return readings
        amount = display_money(values[0])
        block = normalize(prices[0].parent.get_text(" ", strip=True))
        if amount and "boleto ou pix" in block:
            return [
                replace(reading, price=amount, payment="Pix"),
                replace(reading, price=amount, payment="Boleto"),
            ]
        # Preco visual zero nao substitui o ultimo preco valido nem confirma oferta.
        return readings

    def is_product_url(self, url):
        from urllib.parse import urlsplit

        return bool(re.match(r"^/produto/\d+/[^/]+/?$", urlsplit(url).path))

    def search_url(self, query):
        return "https://www.terabyteshop.com.br/busca?" + urlencode({"str": query})

    def search_links(self, html, url):
        from ..discovery import LinkCandidate

        result = super().search_links(html, url)
        for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            if re.match(
                r"^(?:https://(?:www\.)?terabyteshop\.com\.br)?/produto/\d+(?:/|$)",
                a["href"],
            ):
                result.append(
                    LinkCandidate(urljoin(url, a["href"]), a.get_text(" ", strip=True))
                )
        return result
