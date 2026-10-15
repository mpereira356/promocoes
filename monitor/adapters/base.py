"""Extracao Schema.org conservadora, sem seletores de preco inventados."""

import json
import re
from urllib.parse import urljoin, urlsplit
import ipaddress
from bs4 import BeautifulSoup
from ..models import Reading, money, normalize


class ReadError(Exception):
    pass


def nodes(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from nodes(v)
    elif isinstance(value, list):
        for v in value:
            yield from nodes(v)


def tail(value):
    return str(value or "").rstrip("/").split("/")[-1]


def product_image(value, page_url):
    """Somente imagens atribuidas ao Product, nunca de anuncios/recomendacoes."""
    if isinstance(value, list):
        for item in value:
            image = product_image(item, page_url)
            if image:
                return image
        return ""
    if isinstance(value, dict):
        value = value.get("contentUrl") or value.get("url")
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        return ""
    try:
        image = urljoin(page_url, value.strip())
        p = urlsplit(image)
        host = (p.hostname or "").lower()
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            return ""
        if "." not in host or host.endswith((".localhost", ".local", ".internal")):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        return image
    except ValueError:
        return ""


class StructuredAdapter:
    name = "Schema.org (generico)"
    sitemap_urls = ()

    def search_url(self, query):
        return None

    def search_links(self, html, url):
        from ..discovery import structured_links

        return structured_links(BeautifulSoup(html, "html.parser"), url)

    def parse(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        roots = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                roots.extend(nodes(json.loads(script.string or script.get_text())))
            except (ValueError, TypeError):
                continue
        products = [
            n
            for n in roots
            if "Product"
            in (
                n.get("@type") if isinstance(n.get("@type"), list) else [n.get("@type")]
            )
        ]
        # Recusar pagina de categoria ou recomendacoes com varios produtos.
        if len(products) != 1:
            raise ReadError("structured_product_missing_or_ambiguous")
        product = products[0]
        image = product_image(product.get("image"), url)
        identifiers = {}
        for key in ("gtin", "gtin8", "gtin12", "gtin13", "gtin14"):
            value = str(product.get(key) or "")
            if value.isdigit() and len(value) in (8, 12, 13, 14):
                checksum = sum(
                    int(d) * (3 if i % 2 == 0 else 1)
                    for i, d in enumerate(reversed(value[:-1]))
                )
                if (10 - checksum % 10) % 10 == int(value[-1]):
                    identifiers["gtin"] = value.zfill(14)
        mpn = product.get("mpn")
        if isinstance(mpn, str) and mpn.strip():
            identifiers["mpn"] = normalize(mpn)
        brand = product.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        if isinstance(brand, str) and brand.strip():
            identifiers["brand"] = normalize(brand)
        title = product.get("name")
        if not isinstance(title, str) or not title.strip():
            raise ReadError("product_title_missing")
        offers = product.get("offers", [])
        if isinstance(offers, dict):
            offers = [offers]
        readings = []
        for offer in offers:
            if not isinstance(offer, dict) or tail(offer.get("@type")) != "Offer":
                continue  # AggregateOffer.lowPrice nao e uma oferta confirmada.
            seller = offer.get("seller", {})
            seller = seller.get("name", "") if isinstance(seller, dict) else ""
            condition = tail(offer.get("itemCondition") or product.get("itemCondition"))
            if condition not in {
                "NewCondition",
                "UsedCondition",
                "RefurbishedCondition",
                "DamagedCondition",
            }:
                condition = ""
            # Nao atribuir Pix a um price generico. Aceita somente um metodo explicito.
            payment = offer.get("acceptedPaymentMethod", "")
            if not isinstance(payment, str):
                payment = ""
            payment = payment.strip()
            normalized_payment = normalize(payment)
            # Uma lista textual de meios aceitos nao associa um preco a um deles.
            if normalized_payment not in ("pix", "boleto") and not re.fullmatch(
                r"cartao (?:a vista|\d{1,2}x (?:com|sem) juros total)",
                normalized_payment,
            ):
                payment = ""
            stock = {
                "InStock": "in_stock",
                "OutOfStock": "out_of_stock",
                "SoldOut": "out_of_stock",
                "Discontinued": "out_of_stock",
            }.get(tail(offer.get("availability")), "unknown")
            readings.append(
                Reading(
                    title.strip(),
                    str(seller),
                    condition,
                    payment,
                    money(offer.get("price")),
                    stock,
                    str(offer.get("priceCurrency", "")),
                )
            )
        if not readings:
            # Titulo ainda pode ser confirmado, mas nunca fabricar preco.
            readings = [Reading(title.strip(), "", "", "", None)]
        # Dados conflitantes da mesma modalidade nao podem atualizar a serie.
        keys = [(r.seller, r.condition, r.payment, r.currency) for r in readings]
        if len(set(keys)) != len(keys):
            raise ReadError("ambiguous_offer_variants")
        for reading in readings:
            reading.image = image
            reading.identifiers = identifiers.copy()
        return readings
