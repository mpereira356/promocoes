import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from dataclasses import replace
import pytest
from monitor.adapters.kabum import KabumAdapter
from monitor.models import Reading
from monitor.config import normalize_domains
from monitor.presentation import offer_text, send_offer


def offer_page(
    seller="KaBuM!",
    visible="100,00",
    amount="100.00",
    condition="",
    code=42,
    data_code=42,
    title="Placa B550",
):
    schema = {
        "@type": "Product",
        "name": title,
        "offers": {
            "@type": "Offer",
            "price": "100.00",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
        },
    }
    if condition:
        schema["offers"]["itemCondition"] = "https://schema.org/" + condition
    data = {
        "props": {
            "pageProps": {
                "product": {
                    "id": data_code,
                    "title": title,
                    "sellerName": seller,
                    "prices": {"priceWithDiscount": amount},
                    "flags": {"isOpenbox": False},
                }
            }
        }
    }
    return (
        '<script type="application/ld+json">'
        + json.dumps(schema)
        + "</script>"
        + '<script id="__NEXT_DATA__">'
        + json.dumps(data)
        + "</script>"
        + f"<p><span>R$ {visible}</span><span>à vista no PIX</span></p>"
    )


def test_kabum_enriches_real_evidence_and_preserves_unknown_condition():
    r = KabumAdapter().parse(offer_page(), "https://www.kabum.com.br/produto/42/a")[0]
    assert r.seller == "KaBuM!" and r.payment == "Pix"
    assert r.condition == "" and not r.comparable


@pytest.mark.parametrize("code,seller", [("692460", "KaBuM!"), ("683504", "GIGANTEC")])
def test_real_metadata_snapshot_seller_not_assumed(code, seller):
    p = json.loads(
        Path(f"tests/fixtures/kabum_offer_{code}_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    schema = {
        "@type": "Product",
        "name": p["title"],
        "offers": {"@type": "Offer", "price": "123.45", "priceCurrency": "BRL"},
    }
    html = '<script type="application/ld+json">' + json.dumps(schema) + "</script>"
    html += (
        '<script id="__NEXT_DATA__">'
        + json.dumps({"props": {"pageProps": {"product": p}}})
        + "</script>"
    )
    r = KabumAdapter().parse(html, f"https://www.kabum.com.br/produto/{code}")[0]
    assert r.seller == seller and not r.condition
    assert not r.payment  # Sem rotulo/preco da modalidade, nao atribuir Pix.


@pytest.mark.parametrize(
    "changes", [{"visible": "90,00"}, {"amount": "90.00"}, {"data_code": 43}]
)
def test_pix_requires_matching_visible_price_and_identity(changes):
    r = KabumAdapter().parse(
        offer_page(**changes), "https://www.kabum.com.br/produto/42"
    )[0]
    assert not r.payment


def test_pix_in_footer_does_not_label_offer():
    html = offer_page().replace(
        "<p><span>R$ 100,00</span><span>à vista no PIX</span></p>",
        "<footer>à vista no PIX</footer>",
    )
    r = KabumAdapter().parse(html, "https://www.kabum.com.br/produto/42")[0]
    assert not r.payment


def test_condition_explicit_is_comparable():
    r = KabumAdapter().parse(
        offer_page(condition="NewCondition"), "https://www.kabum.com.br/produto/42"
    )[0]
    assert r.comparable


def test_domains_www_normalized_and_deduplicated():
    assert normalize_domains(" www.amazon.com.br,AMAZON.com.br,kabum.com.br ") == (
        "amazon.com.br",
        "kabum.com.br",
    )
    with pytest.raises(ValueError):
        normalize_domains("https://www.amazon.com.br/")


def test_preview_photo_and_text_fallback():
    async def run():
        r = Reading(
            "Produto simulado",
            "Loja",
            "",
            "Pix",
            10000,
            "in_stock",
            image="https://example.org/a.jpg",
        )
        text = offer_text(r, "KaBuM")
        assert "in_stock" not in text
        assert "Disponível segundo a página" in text
        assert (
            "Condição: ❓ Não declarada" in text and "Alertas de preço suspensos" in text
        )
        bot = SimpleNamespace(send_photo=AsyncMock(), send_message=AsyncMock())
        await send_offer(bot, -1, r, "https://www.kabum.com.br/produto/42", "KaBuM")
        bot.send_photo.assert_awaited_once()
        bot.send_photo.side_effect = OSError()
        await send_offer(bot, -1, r, "https://www.kabum.com.br/produto/42", "KaBuM")
        bot.send_message.assert_awaited_once()

    asyncio.run(run())
