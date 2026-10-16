"""Contratos de categoria. Precos sempre vêm da pagina individual da oferta."""
from dataclasses import dataclass
import re
from urllib.parse import urljoin, urlsplit, parse_qs
from bs4 import BeautifulSoup
from ...adapters import adapter
from ...discovery import documents, structured_links
from ...models import normalize
from ..models import DealOffer


@dataclass
class CategoryPage:
    urls: list[str]
    next_url: str | None = None


class CategoryAdapter:
    domain = ''
    categories = {}
    limitations = ()

    @property
    def store(self):
        return adapter(self.domain).name

    def category_url(self, category):
        return self.categories[category]

    def page(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        links = structured_links(soup, url)
        return CategoryPage(self.product_urls([x.url for x in links]), self.next_page(soup, url))

    def product_urls(self, urls):
        result = []
        for url in urls:
            host = (urlsplit(url).hostname or '').removeprefix('www.')
            allowed = host == self.domain or (self.domain == 'mercadolivre.com.br' and host == 'produto.mercadolivre.com.br')
            parser = adapter(self.domain)
            checker = getattr(parser, 'is_product_url', lambda u: bool(re.match(r'^/produto/\d+/[^/]+/?$', urlsplit(u).path)))
            if allowed and checker(url) and url not in result:
                result.append(url)
        return result

    def next_page(self, soup, url):
        current = urlsplit(url)
        page = int(parse_qs(current.query).get('page', ['1'])[0])
        for a in soup.find_all('a', href=True):
            target = urljoin(url, a['href'])
            p = urlsplit(target)
            if p.netloc != current.netloc or p.path.rstrip('/') != current.path.rstrip('/'):
                continue
            if 'next' in a.get('rel', []) or a.get_text(strip=True) == str(page + 1):
                return target
        return None

    def offer(self, html, url, reading):
        """Somente metadados atribuidos inequivocamente ao Product principal."""
        result = DealOffer(reading, url, self.domain, self.store)
        soup = BeautifulSoup(html, 'html.parser')
        products = [n for n in documents(soup) if n.get('@type') == 'Product']
        if len(products) == 1 and normalize(str(products[0].get('name', ''))) == normalize(reading.title):
            model = products[0].get('model')
            if (isinstance(model, str) and re.search(r'[a-z]', normalize(model))
                    and re.search(r'\d', model) and not re.fullmatch(r'[abxhz]\d{3}[a-z]?', normalize(model))):
                result.model = model.strip()
            # Preco riscado estruturado, somente na oferta do mesmo vendedor e
            # mesmo preco atual. Nunca usar AggregateOffer.lowPrice como preco de.
            from ...models import money
            from ...adapters.base import tail
            offers = products[0].get('offers', [])
            if isinstance(offers, dict):
                offers = [offers]
            refs = set()
            for offer in offers if isinstance(offers, list) else []:
                if not isinstance(offer, dict) or tail(offer.get('@type')) != 'Offer':
                    continue
                seller = offer.get('seller', {})
                seller = seller.get('name', '') if isinstance(seller, dict) else seller
                if money(offer.get('price')) != reading.price or not reading.seller or normalize(str(seller)) != normalize(reading.seller):
                    continue
                specifications = offer.get('priceSpecification', [])
                if isinstance(specifications, dict):
                    specifications = [specifications]
                for spec in specifications if isinstance(specifications, list) else []:
                    if (isinstance(spec, dict) and tail(spec.get('priceType')) == 'StrikethroughPrice'
                            and not any(spec.get(k) for k in ('validForMemberTier', 'eligibleCustomerType', 'eligibleQuantity', 'billingDuration', 'billingIncrement'))
                            and spec.get('priceCurrency') == reading.currency == 'BRL'):
                        old = money(spec.get('price'))
                        if old:
                            refs.add(old)
            if len(refs) == 1:
                result.previous = refs.pop()
                result.reference_source = 'Schema.org StrikethroughPrice da mesma oferta'
        return result


def primary_scope(soup, reading, selector):
    headings = soup.find_all('h1')
    if len(headings) != 1 or normalize(headings[0].get_text(' ', strip=True)) != normalize(reading.title):
        return None
    scope = headings[0]
    for _ in range(7):
        scope = scope.parent
        if scope is None:
            return None
        matches = scope.select(selector)
        if matches:
            return scope if len(matches) == 1 else None
    return None


def one_display_price(node):
    from ...display_money import display_money
    values = re.findall(r'R\$\s*([\d.,]+)', node.get_text(' ', strip=True))
    return display_money(values[0]) if len(values) == 1 else None
