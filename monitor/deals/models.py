from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
import re
import time
from ..models import Reading


@dataclass(frozen=True)
class DiscountFilter:
    inclusive: bool
    value: Decimal
    less: bool = False

    @classmethod
    def parse(cls, text):
        match = re.fullmatch(r'\s*(>=|>|<=|<)\s*(\d{1,3}(?:[.,]\d{1,4})?)\s*%?\s*', text)
        if not match:
            raise ValueError('Use >30, >=30, <30 ou <=30, com percentual entre 0 e 100.')
        value = Decimal(match[2].replace(',', '.'))
        if value > 100:
            raise ValueError('O percentual deve estar entre 0 e 100.')
        return cls('=' in match[1], value, match[1].startswith('<'))

    def accepts(self, old, current):
        if not valid_price(old) or not valid_price(current) or old <= current:
            return False
        left, right = Decimal(old - current) * 100, self.value * old
        if self.less:
            return left <= right if self.inclusive else left < right
        return left >= right if self.inclusive else left > right

    def __str__(self):
        return ('<' if self.less else '>') + ('=' if self.inclusive else '') + str(self.value) + '%'


def valid_price(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


@dataclass
class DealOffer:
    reading: Reading
    url: str
    domain: str
    store: str
    previous: int | None = None
    reference_source: str = ''
    model: str = ''
    coupon: str = ''
    members: str = ''
    shipping: int | None = None
    notes: list[str] = field(default_factory=list)
    available_sizes: list[str] = field(default_factory=list)
    color: str = ''
    observed_at: float = field(default_factory=time.time)

    @property
    def ratio(self):
        if valid_price(self.previous) and valid_price(self.reading.price) and self.previous > self.reading.price:
            return Fraction(self.previous - self.reading.price, self.previous)
        return None

    @property
    def percent(self):
        return Decimal(self.ratio.numerator) * 100 / self.ratio.denominator if self.ratio is not None else None

    @property
    def suspicious(self):
        return self.ratio is not None and self.ratio >= Fraction(7, 10)


@dataclass
class Coverage:
    domain: str
    store: str
    category_pages: int = 0
    product_pages: int = 0
    comparison_pages: int = 0
    discovered: int = 0
    excluded: int = 0
    discovery_pages: int = 0
    discovery_loaded: int = 0
    partial: bool = True
    notices: list[str] = field(default_factory=list)
    failed_pages: int = 0
    priced: int = 0
    qualifying: int = 0
    missing_reference: int = 0
    unavailable: int = 0
    sources: list[str] = field(default_factory=list)
    comparison_prices: int = 0


@dataclass
class DealResult:
    offer: DealOffer
    options: list[DealOffer]
    comparison: str
    lowest: DealOffer | None = None
    totals_with_shipping: bool = False
    evidence: object | None = None


@dataclass
class DealReport:
    results: list[DealResult]
    coverage: list[Coverage]
    filter: DiscountFilter
    category: str
    cep: str = ''
    comparisons_limited: bool = False
    examined: list[DealOffer] = field(default_factory=list)
    category_title: str = ''
    size: str = ''
    validation: str = 'announced'
    unconfirmed: int = 0
    not_advantageous: int = 0
    depth: str = 'quick'


def parse_size(text):
    text = text.strip().upper()
    if text in ('TODOS', 'TODAS', 'IGNORAR', '*'):
        return ''
    if not re.fullmatch(r'(?:[A-Z]{1,4}|\d{1,3}(?:[.,]\d)?|ÚNICO|UNICO)', text):
        raise ValueError('Informe um tamanho como M, G, 4 ou 42; ou todos para ignorar.')
    return text.replace(',', '.')
