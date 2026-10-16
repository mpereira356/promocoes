from dataclasses import replace
from monitor.models import Reading
from monitor.presentation import rank_offers, offer_text


def sample(price, **kwargs):
    return Reading(
        "Produto simulado", "Loja", "NewCondition", "Pix", price, "in_stock", **kwargs
    )


def test_three_medals_sorted_and_fourth_without_medal():
    offers = [
        (sample(price), f"https://example.org/{i}", "Loja")
        for i, price in enumerate([400, 100, 300, 200])
    ]
    ranked = rank_offers(offers)
    assert [r.price for r, *_ in ranked] == [100, 200, 300, 400]
    assert [rank for *_, rank, provisional in ranked] == [1, 2, 3, 4]
    for item, medal in zip(ranked, ["🥇", "🥈", "🥉", ""]):
        r, url, store, rank, provisional = item
        text = offer_text(r, store, rank, provisional)
        if medal:
            assert medal in text
        else:
            assert all(m not in text for m in ["🥇", "🥈", "🥉"])


def test_ranking_keeps_payment_condition_separate_and_ties_equal():
    r = sample(100)
    offers = [
        (r, "https://example.org/a", "Loja"),
        (r, "https://example.org/b", "Loja"),
        (replace(r, price=200), "https://example.org/c", "Loja"),
        (
            replace(r, payment="Cartao a vista", price=50),
            "https://example.org/d",
            "Loja",
        ),
        (
            replace(r, condition="UsedCondition", price=40),
            "https://example.org/e",
            "Loja",
        ),
    ]
    indexed = {url: rank for _, url, _, rank, _ in rank_offers(offers)}
    assert indexed["https://example.org/a"] == indexed["https://example.org/b"] == 1
    assert indexed["https://example.org/c"] == 2
    assert indexed["https://example.org/d"] == indexed["https://example.org/e"] == 1


def test_unknown_condition_provisional_unknown_payment_stock_price_unranked():
    r = sample(100)
    cases = [
        replace(r, condition=""),
        replace(r, payment=""),
        replace(r, price=None),
        replace(r, stock="out_of_stock"),
        replace(r, stock="unknown"),
    ]
    ranked = rank_offers(
        [(x, f"https://example.org/{i}", "Loja") for i, x in enumerate(cases)]
    )
    assert ranked[0][3:] == (1, True)
    assert "Ranking provisório" in offer_text(ranked[0][0], "Loja", 1, True)
    assert all(item[3] is None for item in ranked[1:])
    assert all(not item[0].comparable for item in ranked[:2])


def test_duplicate_url_same_modality_not_ranked_twice():
    r = sample(100)
    assert len(rank_offers([(r, "https://example.org/a", "Loja")] * 2)) == 1
