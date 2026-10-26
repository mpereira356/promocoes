"""Conservative price evidence: a crossed-out price is never market proof."""
import time
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from .identity import comparable
from .models import valid_price
from ..observations import strong_identity


@dataclass(frozen=True)
class PriceEvidence:
    status: str
    peers: tuple = ()
    reference: int | None = None
    saving: Fraction = Fraction(0)
    history_low: int | None = None
    history_days: int = 0
    inflated_reference: bool = False

    @property
    def percent(self):
        return Decimal(self.saving.numerator) * 100 / self.saving.denominator


def assess(offer, pool, *, now=None, history=None, minimum_peers=2):
    now = time.time() if now is None else now
    def fresh(item):
        return -60 <= now - item.observed_at <= 900
    if not offer.reading.comparable or offer.reading.stock != 'in_stock' or not fresh(offer):
        return PriceEvidence('unconfirmed')
    if offer.coupon or offer.members or not strong_identity(offer.reading):
        history = None  # These requirements are not part of generic observations.
    peers = {}
    for other in pool:
        if (other.domain == offer.domain or not fresh(other) or not valid_price(other.reading.price)
                or not comparable(offer, other)):
            continue
        if other.domain not in peers or other.reading.price < peers[other.domain].reading.price:
            peers[other.domain] = other
    ordered = tuple(sorted(peers.values(), key=lambda item: item.reading.price))
    days = int(history.get('days', 0)) if history else 0
    historical = history.get('lowest') if history and days >= 2 and history.get('span_seconds', 0) >= 86400 else None
    historical = historical if valid_price(historical) else None
    floor = ordered[0].reading.price if ordered else None
    if floor is not None and floor <= offer.reading.price:
        return PriceEvidence('not_below_market', ordered, floor,
                             Fraction(floor - offer.reading.price, floor), historical, days)
    if len(ordered) < minimum_peers:
        if historical and historical <= offer.reading.price:
            return PriceEvidence('not_below_history', ordered, historical,
                                 Fraction(historical - offer.reading.price, historical), historical, days)
        if historical and historical > offer.reading.price:
            reference = min(historical, floor) if floor else historical
            return PriceEvidence('history_only', ordered, reference,
                                 Fraction(reference - offer.reading.price, reference), historical, days)
        return PriceEvidence('unconfirmed', ordered, history_low=historical, history_days=days)
    reference = min(floor, historical) if historical else floor
    saving = Fraction(reference - offer.reading.price, reference)
    unusual = (valid_price(offer.previous) and offer.previous * 100 > floor * 120)
    status = ('verified' if saving > 0 else
              'not_below_history' if historical and historical <= offer.reading.price < floor else
              'not_below_market')
    return PriceEvidence(status, ordered, reference, saving, historical, days, bool(unusual))


def meets_filter(evidence, discount, price):
    return evidence.status in ('verified', 'history_only') and discount.accepts(evidence.reference, price)
