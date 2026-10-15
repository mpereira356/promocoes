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

    # Somente comparar quando a pagina identifica todos esses campos.
    @property
    def comparable(self):
        return (
            isinstance(self.price, int)
            and not isinstance(self.price, bool)
            and self.price > 0
            and self.currency == "BRL"
            and bool(self.seller)
            and bool(self.condition)
            and bool(self.payment)
        )


def qualifies(old, new, minimum=0, percent=0, target=None):
    if old is None or new >= old:
        return False
    delta = old - new
    return (
        delta >= minimum
        and Decimal(delta) * 100 >= Decimal(str(percent)) * old
        and (target is None or new <= target)
    )
