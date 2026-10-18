"""Distingue uma barreira de acesso de um widget opcional de avaliacoes."""

import json
import re
from bs4 import BeautifulSoup

MARKERS = ("cf-chl-", "g-recaptcha", "hcaptcha", "verify you are human")


def is_access_challenge(html):
    lower = html.lower()
    if any(marker in lower for marker in (
        "we need to verify that you're not a robot",
        'enter the characters you see below',
        'digite os caracteres que voce ve abaixo',
        'digite os caracteres que você vê abaixo',
        '/errors/validatecaptcha',
    )):
        return True
    if not any(marker in lower for marker in MARKERS):
        return False
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
    if any(
        marker in title
        for marker in (
            "just a moment",
            "verify you are human",
            "access denied",
            "attention required",
            "captcha",
        )
    ):
        return True
    # Shopify inclui protecao de formularios em paginas publicas completas.
    # Nao confundir o nome da biblioteca dentro de scripts com um desafio ativo.
    if (re.search(r'Shopify\.shop\s*=', html)
            and soup.select('form[action="/search"]')
            and soup.select('a[href*="/products/"]')
            and not any(m in lower for m in ('cf-chl-', 'verify you are human'))):
        visible = BeautifulSoup(html, 'html.parser')
        for script in visible.select('script, style'):
            script.decompose()
        if not any(marker in str(visible).lower() for marker in MARKERS):
            return False
    # Ler dados publicos ja entregues nao exige interagir com CAPTCHA de comentario.
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            from .adapters.base import nodes

            for node in nodes(json.loads(script.string or script.get_text())):
                kind = node.get("@type")
                if (
                    (kind == "Product" or isinstance(kind, list) and "Product" in kind)
                    and node.get("name")
                    and node.get("offers")
                ):
                    return False
        except (ValueError, TypeError):
            continue
    return True
