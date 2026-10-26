import re
from ..models import normalize
from ..identity import model_conflict, part_number_key, specific_part_number


def model_relation(a, b):
    """True somente com identificador forte ou marca e modelo declarados."""
    ra, rb = a.reading, b.reading
    for key in ('color', 'size', 'voltage', 'generation', 'capacity'):
        va, vb = ra.identifiers.get(key), rb.identifiers.get(key)
        if va or vb:
            if not va or not vb:
                return None
            if normalize(va) != normalize(vb):
                return False
    if model_conflict(ra.title, rb.title):
        return False
    ta, tb = normalize(ra.title), normalize(rb.title)
    ca = set(re.findall(r'\b(\d+)\s*(gb|tb)\b', ta))
    cb = set(re.findall(r'\b(\d+)\s*(gb|tb)\b', tb))
    if ca and cb and ca != cb:
        return False
    if bool(ca) != bool(cb):
        return None
    wa, wb = re.search(r'\bwifi\s*([4567])\b', ta), re.search(r'\bwifi\s*([4567])\b', tb)
    if wa and wb and wa[1] != wb[1]:
        return False
    for pattern in (r'\bddr\s*([345])\b', r'\brev(?:isao)?\s*(\d+(?:\s+\d+)?)\b'):
        va, vb = re.search(pattern, ta), re.search(pattern, tb)
        if va and vb and va[1] != vb[1]:
            return False
        if bool(va) != bool(vb):
            return None
    # Mesmo MPN pode abranger revisoes; ausencia de evidencia nao confirma Wi-Fi.
    wifi_a, wifi_b = bool(re.search(r'\bwifi(?:\d+[a-z]*)?\b', ta)), bool(re.search(r'\bwifi(?:\d+[a-z]*)?\b', tb))
    if wifi_a != wifi_b:
        return None
    ia, ib = ra.identifiers, rb.identifiers
    for key in ('gtin', 'mpn'):
        left = part_number_key(ia[key]) if key == 'mpn' and ia.get(key) else ia.get(key)
        right = part_number_key(ib[key]) if key == 'mpn' and ib.get(key) else ib.get(key)
        if left and right and left != right:
            return False
    if ia.get('gtin') and ia.get('gtin') == ib.get('gtin'):
        return True
    brand = ia.get('brand') and ia.get('brand') == ib.get('brand')
    if brand and specific_part_number(ia.get('mpn')) and part_number_key(ia['mpn']) == part_number_key(ib.get('mpn', '')):
        return True
    if brand and a.model and b.model and normalize(a.model) == normalize(b.model):
        return True
    return None


def comparable(a, b):
    return bool(
        model_relation(a, b) is True
        and a.reading.condition and a.reading.condition == b.reading.condition
        and a.reading.seller and b.reading.seller
        and a.reading.payment and normalize(a.reading.payment) == normalize(b.reading.payment)
        and a.reading.currency == b.reading.currency == 'BRL'
        and a.coupon == b.coupon and a.members == b.members
        and a.reading.stock == b.reading.stock == 'in_stock'
        and a.reading.price and b.reading.price
    )
