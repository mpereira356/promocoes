from .base import StructuredAdapter
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
import json
import re
from ..models import normalize, money
from .base import ReadError


class KabumAdapter(StructuredAdapter):
    name = "KaBuM"

    def is_product_url(self, url):
        p = urlsplit(url)
        return (p.scheme == 'https' and p.hostname in ('kabum.com.br', 'www.kabum.com.br')
            and bool(re.fullmatch(r'/produto/\d+(?:/[^/]+)?/?', p.path)))

    @staticmethod
    def catalog_data(soup):
        script = soup.find('script', id='__NEXT_DATA__')
        data = json.loads(script.get_text())['props']['pageProps']['data']
        if isinstance(data, str):
            data = json.loads(data)
        return data['catalogServer']

    def parse(self, html, url):
        if not self.is_product_url(url):
            raise ReadError('individual_listing_required')
        readings = super().parse(html, url)
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return readings
        try:
            product = json.loads(script.string or script.get_text())["props"][
                "pageProps"
            ]["product"]
            match = re.match(r"/produto/(\d+)(?:/|$)", urlsplit(url).path)
            if not match or str(product["id"]) != match.group(1):
                return readings
            if not all(
                normalize(r.title) == normalize(product["title"]) for r in readings
            ):
                return readings
        except (KeyError, TypeError, ValueError):
            return readings
        seller = product.get("sellerName")
        pix = (
            money(product.get("prices", {}).get("priceWithDiscount"))
            if isinstance(product.get("prices"), dict)
            else None
        )
        # Rotulo e preco no mesmo <p>, observados em pagina propria e marketplace.
        # Nao basta existir a palavra PIX no rodape ou nos meios aceitos pela loja.
        pix_visible = False
        if pix is not None:
            for paragraph in soup.find_all("p"):
                text = paragraph.get_text(" ", strip=True)
                values = re.findall(r"R\$\s*([\d.]+,\d{2})", text)
                if "a vista no pix" in normalize(text) and len(values) == 1:
                    amount = money(values[0].replace(".", "").replace(",", "."))
                    if amount == pix:
                        pix_visible = True
        for reading in readings:
            if isinstance(seller, str) and seller.strip():
                if reading.seller and normalize(reading.seller) != normalize(seller):
                    raise ReadError("conflicting_seller")
                reading.seller = seller.strip()
            if not reading.payment and pix_visible and reading.price == pix:
                reading.payment = "Pix"
            # isOpenbox=False nao comprova produto novo. Preservar condicao ausente.
        return readings

    def search_url(self, query):
        return "https://www.kabum.com.br/busca/" + normalize(query).replace(" ", "-")

    def search_links(self, html, url):
        from ..discovery import LinkCandidate

        soup = BeautifulSoup(html, "html.parser")
        result = super().search_links(html, url)
        # Estrutura observada no HTML real em 15/10/2026; nao utiliza precos do catalogo.
        script = soup.find("script", id="__NEXT_DATA__")
        if script:
            try:
                items = self.catalog_data(soup)['data']
                for item in items:
                    code, slug, name = (
                        item.get("code"),
                        item.get("friendlyName"),
                        item.get("name"),
                    )
                    if (
                        str(code).isdigit()
                        and isinstance(slug, str)
                        and re.fullmatch(r"[a-z0-9-]+", slug)
                        and isinstance(name, str)
                    ):
                        result.append(
                            LinkCandidate(
                                f"https://www.kabum.com.br/produto/{code}/{slug}", name
                            )
                        )
            except (KeyError, TypeError, ValueError, AttributeError):
                pass
        for a in soup.find_all("a", href=True):
            if re.match(
                r"^(?:https://(?:www\.)?kabum\.com\.br)?/produto/\d+(?:/|$)", a["href"]
            ):
                result.append(
                    LinkCandidate(urljoin(url, a["href"]), a.get_text(" ", strip=True))
                )
        return [candidate for candidate in result if self.is_product_url(candidate.url)]
