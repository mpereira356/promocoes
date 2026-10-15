"""Identidade conservadora entre lojas: nunca usar SKU interno como modelo."""

from .models import normalize


def same_product(seed, candidate):
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
