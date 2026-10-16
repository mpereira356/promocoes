import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.adapters.amazon import AmazonAdapter
from monitor.adapters.base import ReadError
from monitor.service import Monitor
from monitor.amazon_offers import AmazonOffersReader
from monitor.amazon_offers import browser_error

URL = 'https://www.amazon.com.br/Gigabyte-B550-AORUS-ELITE-AX/dp/B08KGVH7YC'
HTML = Path('tests/fixtures/amazon_aod_real.html').read_text(encoding='utf-8')


def test_real_aod_price_is_bound_to_seller_condition_and_product():
    r = AmazonAdapter().parse(HTML, URL)[0]
    assert r.price == 172711
    assert r.seller == 'Amazon Global (ID A2EB9PYM83FCP9)'
    assert r.condition == 'NewCondition'
    assert not r.payment and r.stock == 'unknown' and not r.comparable


def test_shipping_or_coupon_cannot_replace_main_offer_price():
    html = HTML.replace('</div></div>', '<span>Entrega R$ 8,90. Cupom R$ 20,00</span></div></div>')
    assert AmazonAdapter().parse(html, URL)[0].price == 172711
    assert AmazonAdapter().parse(HTML.replace('1.727,11', '000,00'), URL)[0].price is None


def test_segmented_price_is_read_and_conflicting_representations_are_refused():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(HTML, 'html.parser')
    label = soup.select_one('.apex-pricetopay-accessibility-label')
    label.decompose()
    assert AmazonAdapter().parse(str(soup), URL)[0].price == 172711
    soup = BeautifulSoup(HTML, 'html.parser')
    soup.select_one('.apex-pricetopay-accessibility-label').string = 'R$ 2.000,00'
    assert AmazonAdapter().parse(str(soup), URL)[0].price is None


def test_hidden_price_layout_uses_only_same_asin_public_panel():
    html = '<span id="productTitle">Produto real</span><div id="priceNotAvailable_feature_div">Preco oculto</div>'
    a = AmazonAdapter()
    assert a.hidden_price_panel_url(html, URL) == 'https://www.amazon.com.br/dp/B08KGVH7YC/ref=olp-opf-redir?aod=1'
    assert a.hidden_price_panel_url(html, 'https://evil.org/dp/B08KGVH7YC') is None
    assert a.hidden_price_panel_url('<span id="productTitle">Sem painel</span>', URL) is None


def test_aod_from_another_product_is_rejected():
    html = HTML.replace('id="aod-asin-title-text"', 'id="different-title"')
    with pytest.raises(ReadError, match='conflicting_product_title'):
        AmazonAdapter().parse(html, URL)


def test_buying_options_link_must_be_declared_for_same_asin():
    a = AmazonAdapter()
    html = '<div id="buybox-see-all-buying-choices"><a href="/gp/offer-listing/B08KGVH7YC/ref=dp_olp_unknown_mbc">Ver ofertas</a></div>'
    assert a.buying_options_url(html, URL).startswith('https://www.amazon.com.br/gp/offer-listing/B08KGVH7YC/')
    assert a.buying_options_url(html.replace('B08KGVH7YC', 'B08MPZ14FY'), URL) is None
    assert a.buying_options_url(html.replace('/gp/offer-listing/', 'https://evil.org/gp/offer-listing/'), URL) is None


def test_monitor_uses_browser_only_for_declared_options_when_price_missing():
    async def run():
        main = '<span id="productTitle">Gigabyte B550 AORUS ELITE AX V2</span><div id="buybox-see-all-buying-choices"><a href="/gp/offer-listing/B08KGVH7YC/ref=dp_olp_unknown_mbc">Ver ofertas</a></div>'
        f = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), html=AsyncMock(return_value=(main, URL)))
        m = Monitor(None, SimpleNamespace(browser=True), f, None, None)
        m.amazon_offers = SimpleNamespace(html=AsyncMock(return_value=HTML))
        r = await m.read(URL)
        assert r[0].price == 172711
        m.amazon_offers.html.assert_awaited_once()
    asyncio.run(run())


def test_robots_restriction_stops_selenium_before_start(monkeypatch):
    async def run():
        f = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), allowed_by_robots=AsyncMock(side_effect=ReadError('robots_disallowed')))
        reader = AmazonOffersReader(f)
        load = AsyncMock()
        monkeypatch.setattr(reader, '_load', load)
        with pytest.raises(ReadError, match='robots_disallowed'):
            await reader.html('https://www.amazon.com.br/gp/offer-listing/B08KGVH7YC/ref=test')
        load.assert_not_called()
    asyncio.run(run())


@pytest.mark.parametrize('message,expected', [
    ('tab crashed; private details', 'amazon_browser_crashed'),
    ('net::ERR_NAME_NOT_RESOLVED secret', 'amazon_browser_connection_failed'),
    ('net::ERR_TUNNEL_CONNECTION_FAILED secret', 'amazon_browser_connection_failed'),
    ('private unrelated details', 'amazon_browser_start_failed'),
])
def test_browser_failure_is_classified_without_private_details(message, expected):
    assert browser_error(RuntimeError(message), 'amazon_browser_start_failed') == expected


def test_real_cart_price_requirement_stops_before_selenium():
    async def run():
        html = Path('tests/fixtures/amazon_ak820_cart_price_real.html').read_text(encoding='utf-8')
        url = 'https://www.amazon.com.br/dp/B0H9BWD7NP'
        assert AmazonAdapter().price_requires_cart(html)
        assert not AmazonAdapter().price_requires_cart('<aside>adicione este item ao seu carrinho</aside>')
        f = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), html=AsyncMock(return_value=(html, url)))
        monitor = Monitor(None, SimpleNamespace(browser=True), f, None, None)
        monitor.amazon_offers = SimpleNamespace(html=AsyncMock())
        with pytest.raises(ReadError, match='amazon_price_requires_cart'):
            await monitor.read(url)
        monitor.amazon_offers.html.assert_not_called()
    asyncio.run(run())


def test_real_logitech_white_variant_has_different_declared_part_number():
    from monitor.identity import same_product
    from monitor.models import Reading
    html = Path('tests/fixtures/amazon_logitech_white_real.html').read_text(encoding='utf-8')
    adapter = AmazonAdapter()
    white = adapter.parse(html, 'https://www.amazon.com.br/dp/B0BRSQCZLS')[0]
    assert 'Branco' in white.title
    assert white.identifiers == {'brand': 'logitech g', 'mpn': '920 011921'}
    assert white.price is None and adapter.price_requires_cart(html)
    black = Reading('Logitech G PRO X 60 Preto', '', '', '', None,
        identifiers={'brand': 'logitech g', 'mpn': '920 011902'})
    assert same_product(black, white) is False
    # Tabela de outro ASIN ou fora dos detalhes principais não fornece identidade.
    assert not adapter.parse(html.replace('B0BRSQCZLS', 'B08KGVH7YC'), 'https://www.amazon.com.br/dp/B0BRSQCZLS')[0].identifiers
    assert not adapter.parse(html.replace('id="productDetails_feature_div"', 'id="recommendations"'), 'https://www.amazon.com.br/dp/B0BRSQCZLS')[0].identifiers


def test_conflicting_schema_and_details_are_not_merged():
    from monitor.models import Reading
    reading = Reading('Logitech', '', '', '', None, identifiers={'mpn': '920 011902'})
    with pytest.raises(ReadError, match='conflicting_product_identifiers'):
        AmazonAdapter().enrich_identifiers([reading], {'mpn': '920 011921'})


MAIN_URL = 'https://www.amazon.com.br/dp/B0F53JGRLS'


def main_price_fixture():
    return Path('tests/fixtures/amazon_main_price_real.html').read_text(encoding='utf-8')


def test_real_main_price_total_seller_and_explicit_stock():
    reading = AmazonAdapter().parse(main_price_fixture(), MAIN_URL)[0]
    assert reading.price == 24296
    assert reading.seller == 'Amazon Global (ID A2EB9PYM83FCP9)'
    assert reading.stock == 'in_stock'
    assert not reading.payment and not reading.condition and not reading.comparable


def test_main_offer_ignores_installments_shipping_and_recommendations():
    html = main_price_fixture() + '<aside><span class="a-price"><span class="a-offscreen">R$ 1,00</span></span></aside>'
    html += '<div>Frete R$ 8,90. Em 6x de R$ 40,51. Cupom R$ 20,00</div>'
    assert AmazonAdapter().parse(html, MAIN_URL)[0].price == 24296


@pytest.mark.parametrize('replacement', ['R$0,00', 'R$999,99', 'US$242,96'])
def test_conflicting_zero_or_foreign_main_price_is_refused(replacement):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(main_price_fixture(), 'html.parser')
    soup.select_one('.apex-pricetopay-value .a-offscreen').string = replacement
    assert AmazonAdapter().parse(str(soup), MAIN_URL)[0].price is None


def test_wrong_asin_cannot_supply_primary_price():
    html = main_price_fixture().replace('value="B0F53JGRLS"', 'value="B0BRSQCZLS"')
    with pytest.raises(ReadError, match='different_model'):
        AmazonAdapter().parse(html, MAIN_URL)


def test_missing_stock_does_not_turn_price_into_stock_confirmation():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(main_price_fixture(), 'html.parser')
    for n in soup.select('#availability'):
        n.decompose()
    r = AmazonAdapter().parse(str(soup), MAIN_URL)[0]
    assert r.price == 24296 and r.stock == 'unknown'


def test_monitor_reads_main_price_without_starting_selenium():
    async def run():
        f = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), html=AsyncMock(return_value=(main_price_fixture(), MAIN_URL)))
        monitor = Monitor(None, SimpleNamespace(browser=True), f, None, None)
        monitor.amazon_offers = SimpleNamespace(html=AsyncMock())
        readings = await monitor.read(MAIN_URL)
        assert readings[0].price == 24296
        monitor.amazon_offers.html.assert_not_called()
    asyncio.run(run())


def test_search_delivers_primary_price_through_actual_formatter():
    from monitor.search_results import deliver_search
    async def run():
        fetcher = SimpleNamespace(canonical=lambda u: (u, 'amazon.com.br'), html=AsyncMock(return_value=(main_price_fixture(), MAIN_URL)))
        db = SimpleNamespace(save_ad=lambda *args: {'id': 77})
        search = SimpleNamespace(links=AsyncMock(return_value=[MAIN_URL]))
        monitor = Monitor(db, SimpleNamespace(browser=True), fetcher, search, None)
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        send = AsyncMock()
        await deliver_search(monitor, fetcher, db, bot, 0, 'Aspirador portátil', send)
        body = '\n'.join(c.args[1] for c in bot.send_message.await_args_list)
        assert 'R$ 242,96' in body and 'não lido' not in body
        assert 'Ofertas enviadas: 1' in send.await_args_list[-1].args[0]
        assert 'Preços lidos nas ofertas enviadas: 1' in send.await_args_list[-1].args[0]
    asyncio.run(run())


@pytest.mark.parametrize('asin,cents', [('B004PS7O9I',23406), ('B0BT23S5MF',14590)])
def test_real_other_offers_minimum_is_separate_from_individual_price(asin,cents):
    from monitor.presentation import offer_text,rank_offers
    html=Path('tests/fixtures/amazon_starting_'+asin+'.html').read_text(encoding='utf-8')
    url='https://www.amazon.com.br/dp/'+asin
    r=AmazonAdapter().parse(html,url)[0]
    assert r.starting_price == cents and '/gp/offer-listing/'+asin in r.starting_price_url
    assert r.price is None and not r.comparable and r.stock == 'unknown'
    assert rank_offers([(r,url,'Amazon')])[0][3] is None
    text=offer_text(r,'Amazon')
    assert 'Outras ofertas a partir de: R$ ' in text
    assert 'vendedor, pagamento e estoque' in text
    async def run():
        f=SimpleNamespace(canonical=lambda u:(u,'amazon.com.br'),html=AsyncMock(return_value=(html,url)))
        m=Monitor(None,SimpleNamespace(browser=True),f,None,None)
        m.amazon_offers=SimpleNamespace(html=AsyncMock())
        assert (await m.read(url))[0].starting_price == cents
        m.amazon_offers.html.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('change', ['asin','host','zero','currency','ambiguous','unscoped'])
def test_other_offers_minimum_rejects_wrong_or_ambiguous_reference(change):
    from bs4 import BeautifulSoup
    asin='B0BT23S5MF'
    url='https://www.amazon.com.br/dp/'+asin
    soup=BeautifulSoup(Path('tests/fixtures/amazon_starting_'+asin+'.html').read_text(encoding='utf-8'),'html.parser')
    link=soup.select_one('#aod-ingress-link')
    if change=='asin':link['href']=link['href'].replace(asin,'B004PS7O9I')
    elif change=='host':link['href']='https://evil.org'+link['href']
    elif change=='zero':link.select_one('.a-offscreen').string='R$0,00'
    elif change=='currency':link.select_one('.a-offscreen').string='US$145,90'
    elif change=='ambiguous':link.append(BeautifulSoup('<span class="a-price"><span class="a-offscreen">R$10,00</span></span>','html.parser'))
    elif change=='unscoped':soup.select_one('#olpLinkWidget_feature_div')['id']='recommendations'
    assert AmazonAdapter().starting_offer(soup,url) == (None,'')


def test_search_delivers_real_page_minimum_without_counting_individual_price():
    from monitor.search_results import deliver_search
    async def run():
        asin='B0BT23S5MF'
        url='https://www.amazon.com.br/dp/'+asin
        html=Path('tests/fixtures/amazon_starting_'+asin+'.html').read_text(encoding='utf-8')
        f=SimpleNamespace(canonical=lambda u:(u,'amazon.com.br'),html=AsyncMock(return_value=(html,url)))
        m=Monitor(None,SimpleNamespace(browser=True),f,None,None)
        send=AsyncMock()
        bot=SimpleNamespace(send_message=AsyncMock())
        db=SimpleNamespace(save_ad=lambda *a:{'id':1})
        await deliver_search(m,f,db,bot,1,url,send)
        assert any('145,90' in str(c) and 'Outras ofertas a partir de' in str(c) for c in bot.send_message.await_args_list)
        assert any('a partir de' in c.args[0] for c in send.await_args_list)
        assert 'Pre\u00e7os lidos nas ofertas enviadas: 0' in send.await_args_list[-1].args[0]
    asyncio.run(run())



def test_echo_generation_comes_from_same_asin_technical_table_not_url():
    from monitor.discovery import reading_relevance
    from bs4 import BeautifulSoup
    html=Path('tests/fixtures/amazon_echo_generation_real.html').read_text(encoding='utf-8')
    url='https://www.amazon.com.br/dp/B09B8VGCR8'
    r=AmazonAdapter().parse(html,url)[0]
    assert r.identifiers['generation']=='echo dot 5 geracao 2022'
    assert r.price==58411 and reading_relevance('Echo Dot 5\u00aa gera\u00e7\u00e3o',r)
    assert not reading_relevance('Echo Dot 4\u00aa gera\u00e7\u00e3o',r)
    soup=BeautifulSoup(html,'html.parser');soup.select_one('#tech')['id']='recommendations'
    unknown=AmazonAdapter().parse(str(soup),url)[0]
    assert not reading_relevance('Echo Dot 5\u00aa gera\u00e7\u00e3o',unknown)
    soup=BeautifulSoup(html,'html.parser');soup.select_one('#tech').append(BeautifulSoup('<table><tr><td>Gera\u00e7\u00e3o</td><td>Echo Dot 4\u00aa gera\u00e7\u00e3o (2020)</td></tr></table>','html.parser'))
    with pytest.raises(ReadError,match='conflicting_product_identifiers'):AmazonAdapter().parse(str(soup),url)


@pytest.mark.parametrize('title,slug,expected', [
    ('Echo Dot Geracao mais recente','Echo-Dot-5%C2%AA-geracao',True),
    ('Echo Dot Geracao mais recente','Echo-Dot-4%C2%AA-geracao',False),
    ('Echo Dot Max Geracao mais recente','Echo-Dot-5%C2%AA-geracao',False),
    ('Suporte para Echo Dot 5 Geracao','Echo-Dot-5%C2%AA-geracao',False),
    ('Echo Show 5 Geracao','Echo-Dot-5%C2%AA-geracao',False),
    ('Echo Dot 4 Geracao','Echo-Dot-5%C2%AA-geracao',False),
])
def test_echo_discovery_slug_is_only_provisional_and_variants_stay_separate(title,slug,expected):
    from monitor.discovery import LinkCandidate,candidate_relevance
    c=LinkCandidate('https://www.amazon.com.br/'+slug+'/dp/B09B8VGCR8',title)
    assert bool(candidate_relevance('Echo Dot 5 Geracao',c))==expected



def test_real_echo_alternating_hidden_response_never_reuses_captured_price():
    from monitor.discovery import reading_relevance
    adapter=AmazonAdapter()
    url='https://www.amazon.com.br/dp/B09B8VGCR8'
    visible=Path('tests/fixtures/amazon_echo_generation_real.html').read_text(encoding='utf-8')
    hidden=Path('tests/fixtures/amazon_echo_hidden_real.html').read_text(encoding='utf-8')
    assert adapter.parse(visible,url)[0].price==58411
    r=adapter.parse(hidden,url)[0]
    assert r.price is None and r.stock=='unknown' and not r.comparable
    assert adapter.price_requires_cart(hidden)
    assert reading_relevance('Echo Dot 5 geracao',r)
