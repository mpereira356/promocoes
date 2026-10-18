"""Painel publico AOD: recortes reais reduzidos e transporte simulado."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.adapters.amazon import AmazonAdapter
from monitor.adapters.base import ReadError
from monitor.service import Monitor

URL='https://www.amazon.com.br/dp/B08KGVH7YC'
MAIN=Path('tests/fixtures/amazon_aod_ajax_main_real.html').read_text(encoding='utf-8')
FRAGMENT=Path('tests/fixtures/amazon_aod_ajax_fragment_real.html').read_text(encoding='utf-8')


def test_public_panel_parameters_come_from_same_asin_dom():
    a=AmazonAdapter()
    target=a.public_offers_url(MAIN,URL)
    assert target.startswith('https://www.amazon.com.br/gp/product/ajax/aodAjaxMain?asin=B08KGVH7YC&')
    assert target.endswith('pc=dp')
    assert a.public_offers_url(MAIN.replace('data-asin="B08KGVH7YC"','data-asin="B0CYGT9CWW"'),URL) is None
    assert a.public_offers_url(MAIN,'https://evil.org/dp/B08KGVH7YC') is None
    assert a.public_offers_url(MAIN.replace('all-offers-display-params','recommendations'),URL) is None


def test_public_panel_real_fragment_keeps_row_price_seller_and_condition():
    a=AmazonAdapter();main=a.parse(MAIN,URL)
    readings,_=a.offers_fragment(main,FRAGMENT,URL)
    r=readings[0]
    assert r.price==175322
    assert r.seller=='Amazon Global (ID A2EB9PYM83FCP9)'
    assert r.condition=='NewCondition'
    assert r.stock=='unknown' and not r.payment and not r.comparable


@pytest.mark.parametrize('browser',[False,True])
def test_monitor_reads_public_panel_before_any_browser(browser):
    async def run():
        public=AmazonAdapter().public_offers_url(MAIN,URL)
        f=SimpleNamespace(canonical=lambda u:(u,'amazon.com.br'),html=AsyncMock(side_effect=[(MAIN,URL),(FRAGMENT,public)]))
        m=Monitor(None,SimpleNamespace(browser=browser),f,None,None)
        m.amazon_offers=SimpleNamespace(html=AsyncMock(side_effect=AssertionError('browser unnecessary')))
        assert (await m.read(URL))[0].price==175322
        assert f.html.await_args_list[1].args==(public,)
        assert f.html.await_args_list[1].kwargs=={'isolated':True}
        m.amazon_offers.html.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('reason',['blocked_no_bypass','captcha_no_bypass','robots_disallowed','network_or_rate_limit','rate_limit_deferred'])
def test_public_panel_access_failure_never_turns_into_browser_retry_or_zero(reason):
    async def run():
        f=SimpleNamespace(canonical=lambda u:(u,'amazon.com.br'),html=AsyncMock(side_effect=[(MAIN,URL),ReadError(reason)]))
        m=Monitor(None,SimpleNamespace(browser=True),f,None,None)
        m.amazon_offers=SimpleNamespace(html=AsyncMock())
        with pytest.raises(ReadError,match=reason):await m.read(URL)
        m.amazon_offers.html.assert_not_awaited()
    asyncio.run(run())


def test_wrong_product_header_is_refused_despite_valid_row_price():
    a=AmazonAdapter()
    with pytest.raises(ReadError,match='conflicting_product_title'):
        a.offers_fragment(a.parse(MAIN,URL),FRAGMENT.replace('Gigabyte B550','ASUS B650'),URL)
    with pytest.raises(ReadError,match='amazon_offers_unavailable'):
        a.offers_fragment(a.parse(MAIN,URL),'<p>No offers</p>',URL)



def test_generic_chipset_part_number_neither_rejects_correct_model_nor_confirms_another():
    from monitor.identity import same_product
    from monitor.models import Reading
    a=Reading('Gigabyte B550 Aorus Elite AX V2','','','',None,identifiers={'brand':'gigabyte','mpn':'9mb55aew2 00 10'})
    b=Reading('Placa Mae Gigabyte B550 Aorus Elite AX V2 WiFi DDR4','','','',None,identifiers={'brand':'gigabyte','mpn':'b550'})
    assert same_product(a,b) is None
    other=Reading('Gigabyte B550 Gaming X V2','','','',None,identifiers={'brand':'gigabyte','mpn':'b550'})
    assert same_product(b,other) is None
    wrong=Reading('Gigabyte B650 Aorus Elite AX V2','','','',None,identifiers={'brand':'gigabyte','mpn':'b650'})
    assert same_product(a,wrong) is False
