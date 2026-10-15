"""Valores monetarios visiveis com separadores brasileiros ou americanos."""

import re
from .models import money


def display_money(value):
    value = value.strip().replace("\u00a0", "").replace(" ", "")
    if re.fullmatch(r"(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}", value):
        return money(value.replace(".", "").replace(",", "."))
    if re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}", value):
        return money(value.replace(",", ""))
    return None
