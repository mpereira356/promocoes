from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
import unicodedata


def normalize(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"wi[ -]?fi", "wifi", s)
    return " ".join(re.findall(r"[a-z0-9]+", s))


def money(value):
    try:
        # JSON-LD usa ponto decimal; nunca inferir separadores locais.
        d = Decimal(str(value))
        if d.is_finite() and d > 0 and d == d.quantize(Decimal(".01")):
            return int(d * 100)
    except (InvalidOperation, ValueError, TypeError):
        pass
    return None


@dataclass
class Reading:
    title: str
    seller: str
    condition: str
    payment: str
    price: int | None
    stock: str = "unknown"
    currency: str = "BRL"
    image: str = ""
    identifiers: dict = field(default_factory=dict)
    # Referencia publica de varias ofertas, sem atribuir preco a um vendedor.
    starting_price: int | None = None
    starting_price_url: str = ""

    @property
    def regional_unit_context(self):
        ids = self.identifiers
        return bool(ids.get('price_basis') == 'regional_public_unit'
                    and ids.get('price_unit') == 'kg'
                    and re.fullmatch(r'[0-9]{8}', ids.get('postal_code', ''))
                    and ids.get('store_id') and ids.get('grocery_product_id')
                    and ids.get('storage') in ('resfriada', 'congelada')
                    and re.sub(r'\D', '', self.seller).endswith(ids.get('postal_code', '')))

    @property
    def visit_listing(self):
        """Published regional price; physical stock/collection is not promised."""
        ids = self.identifiers
        return bool(self.regional_unit_context and ids.get('shopping_mode') == 'visit'
                    and ids.get('region_verified') == 'true' and ids.get('price_verified') == 'true')

    @property
    def public_unit_price(self):
        """Explicit regional public metric, never a payment-specific comparison."""
        return bool(self.regional_unit_context and (self.visit_listing or (
            self.identifiers.get('delivery_verified') == 'true' and self.stock == 'in_stock')))

    # Payment-specific offers require complete terms. Regional public unit rates
    # form a separate, explicitly labelled metric for the same store and CEP.
    @property
    def comparable(self):
        return (
            isinstance(self.price, int)
            and not isinstance(self.price, bool)
            and self.price > 0
            and self.currency == "BRL"
            and bool(self.seller)
            and bool(self.condition)
            and (bool(self.payment) or self.public_unit_price)
        )

    @property
    def listing_price_complete(self):
        """For explicit per-monitor published-price policy only, not market proof."""
        return bool(not self.condition and type(self.price) is int and self.price > 0
                    and self.currency == 'BRL' and self.seller and self.payment
                    and self.stock == 'in_stock')


def qualifies(old, new, minimum=0, percent=0, target=None):
    if old is None or new >= old:
        return False
    delta = old - new
    return (
        delta >= minimum
        and Decimal(delta) * 100 >= Decimal(str(percent)) * old
        and (target is None or new <= target)
    )
