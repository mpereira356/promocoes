from pathlib import Path

import pytest

from monitor.adapters.base import ReadError
from monitor.adapters.pichau import PichauAdapter


URL = 'https://www.pichau.com.br/placa-mae-gigabyte-b550-aorus-elite-ax-v2'
DOM = Path(__file__).with_name('fixtures').joinpath('pichau_user_dom_pix.html').read_text(encoding='utf-8')


def test_supplied_dom_without_product_schema_reads_total_pix_price():
    reading, = PichauAdapter().parse(DOM, URL)
    assert reading.price == 124999
    assert reading.payment == 'Pix'
    assert 'AX V2' in reading.title
    assert reading.stock == 'unknown'
    assert reading.seller == reading.condition == ''
    assert not reading.comparable


@pytest.mark.parametrize('html', [
    DOM.replace('no PIX', 'no boleto'),
    DOM.replace('product-page-title', 'recommendation-title'),
    DOM + '<h1>Outro produto</h1>',
    DOM + '<script type="application/ld+json">{"@type":"Product"}</script>',
    DOM + '<script type="application/ld+json">{invalid}</script>',
])
def test_incomplete_or_ambiguous_dom_is_not_a_valid_price(html):
    with pytest.raises(ReadError):
        PichauAdapter().parse(html, URL)


def test_dom_fallback_does_not_accept_a_category_or_other_store():
    for url in ('https://www.pichau.com.br/hardware/placa-mae',
                'https://example.com/placa-mae-gigabyte'):
        with pytest.raises(ReadError):
            PichauAdapter().parse(DOM, url)
