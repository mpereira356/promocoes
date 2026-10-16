"""Identidade conservadora entre lojas: nunca usar SKU interno como modelo."""

from .models import normalize
import re


def model_conflict(left, right):
    """Conflitos explicitos de familias conhecidas, sem adivinhar sinonimos."""
    a, b = normalize(left), normalize(right)
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
    for key in ("gtin", "mpn"):
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
