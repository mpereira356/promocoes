"""Identidade conservadora entre lojas: nunca usar SKU interno como modelo."""

from .models import normalize
import re

BRANDS = frozenset({'logitech', 'corsair', 'superframe', 'ajazz', 'razer', 'redragon',
    'hyperx', 'havit', 'asus', 'gigabyte', 'msi', 'asrock', 'kingston', 'crucial', 'samsung'})


def brand_conflict(left, right):
    a, b = set(normalize(left).split()) & BRANDS, set(normalize(right).split()) & BRANDS
    return bool(a and b and a.isdisjoint(b))


def logitech_part_number(text):
    if 'logitech' not in normalize(text).split():
        return ''
    match = re.search(r'\b920[\s-]+(\d{6})\b', text, re.I)
    return '920-' + match[1] if match else ''


def search_terms(title, identifiers=None):
    """Consulta curta para descoberta; nunca transforma título em identidade verificada."""
    identifiers = identifiers or {}
    brand, mpn = identifiers.get('brand', ''), identifiers.get('mpn', '')
    if mpn:
        if normalize(brand) == 'logitech g':
            brand = 'logitech'
        match = re.fullmatch(r'920[\s-]+(\d{6})', mpn)
        if match:
            mpn = '920-' + match[1]
        return ' '.join(filter(None, [brand, mpn]))
    part = logitech_part_number(title)
    return 'Logitech ' + part if part else title


def model_conflict(left, right):
    """Conflitos explicitos de familias conhecidas, sem adivinhar sinonimos."""
    a, b = normalize(left), normalize(right)
    if brand_conflict(left, right):
        return True
    if 'echo dot' in a and 'echo dot' in b:
        if ('max' in a.split()) != ('max' in b.split()):
            return True
        ga = re.search(r'\becho dot (\d+)(?:a|th)?\b', a)
        gb = re.search(r'\becho dot (\d+)(?:a|th)?\b', b)
        if ga and gb and ga[1] != gb[1]:
            return True
    if 'logitech' in a.split() and 'logitech' in b.split():
        ma, mb = re.search(r'\bg pro( x)?\b', a), re.search(r'\bg pro( x)?\b', b)
        if ma and mb and bool(ma[1]) != bool(mb[1]):
            return True
    chip_a = set(re.findall(r'\b[bxyz]\d{3}[a-z]?\b', a))
    chip_b = set(re.findall(r'\b[bxyz]\d{3}[a-z]?\b', b))
    if chip_a and chip_b and chip_a != chip_b:
        return True
    if {'aorus', 'elite'} <= set(a.split()) and {'aorus', 'elite'} <= set(b.split()):
        if ('ax' in a.split()) != ('ax' in b.split()):
            return True
    if 'rog strix' in a and 'rog strix' in b:
        # B550-F e B550-E nao sao intercambiaveis.
        model_a = re.search(r'\bb550\s+([fe])\b', a)
        model_b = re.search(r'\bb550\s+([fe])\b', b)
        if model_a and model_b and model_a[1] != model_b[1]:
            return True
    return False


def same_product(seed, candidate):
    if model_conflict(seed.title, candidate.title):
        return False
    left, right = seed.identifiers, candidate.identifiers
    for key in ("gtin", "mpn", "generation"):
        if left.get(key) and right.get(key) and left[key] != right[key]:
            return False
    if left.get("gtin") and left.get("gtin") == right.get("gtin"):
        return True
    if (
        left.get("mpn")
        and left.get("mpn") == right.get("mpn")
        and left.get("brand")
        and left.get("brand") == right.get("brand")
    ):
        return True
    if normalize(seed.title) == normalize(candidate.title) and any(
        c.isdigit() for c in seed.title
    ):
        return True
    return None  # Exige confirmacao; falta evidencia de que e o mesmo modelo.
