"""Identidade/busca de monitoramentos: simulacao, sem acesso a lojas."""
import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlsplit
import pytest
from monitor.identity import monitoring_search_terms, same_product
from monitor.models import Reading
from monitor.db import DB
from monitor.service import Monitor
from monitor.adapters.base import ReadError, StructuredAdapter


@pytest.mark.parametrize('title,ids,expected', [
    ('Placa Mae Gigabyte B550 Aorus Elite AX V2, WiFi, DDR4, Socket AM4, ATX, Chipset AMD B550, B550-AORUS-ELITE-AX-V2', {}, 'gigabyte b550 aorus elite ax v2'),
    ('Placa-Mae Gigabyte B550 Aorus Elite Ax V2, Chipset B550, AMD Am4, Atx, DDR4, 9mb55aew2-00-10', {'brand':'gigabyte','mpn':'9mb55aew2 00 10'}, 'gigabyte b550 aorus elite ax v2'),
    ('Gigabyte B550 Aorus Elite V2 AM4', {}, 'gigabyte b550 aorus elite v2'),
    ('Gigabyte B550 Aorus Elite AX V2 rev. 1.2 DDR4', {}, 'gigabyte b550 aorus elite ax v2 rev 1.2'),
    ('Placa Mae Asus ROG STRIX B550-F GAMING WIFI II, AM4, DDR4, HDMI', {}, 'asus rog strix b550 f gaming wifi ii'),
    ('Teclado EPOMAKER HE68 Lite Hall Effect 8K RGB Preto', {}, 'epomaker he68 lite'),
    ('Teclado AJAZZ AK820 Pro RGB Switch Flyfish', {}, 'ajazz ak820 pro'),
    ('Nome de produto desconhecido', {}, 'Nome de produto desconhecido'),
    ('Descricao comprida', {'brand':'kingston','model':'Fury Beast DDR4 3200'}, 'kingston fury beast ddr4 3200'),
    ('Descricao comprida', {'brand':'hoto','model':'4in1 V2'}, 'hoto 4in1 v2'),
    ('Descricao comprida', {'brand':'logitech g','mpn':'920 011902'}, 'logitech 920-011902'),
])
def test_monitoring_query_uses_model_preserving_versions(title,ids,expected):
    before=ids.copy()
    assert monitoring_search_terms(title,ids)==expected
    assert ids==before


def test_structured_model_is_preserved_as_declared_metadata():
    product={'@type':'Product','name':'Kingston memoria','brand':{'name':'Kingston'},'model':'Fury Beast DDR4 3200',
        'offers':{'@type':'Offer','price':'100.00'}}
    r=StructuredAdapter().parse('<script type="application/ld+json">'+json.dumps(product)+'</script>','https://www.pichau.com.br/item')[0]
    assert r.identifiers['model']=='fury beast ddr4 3200'


def test_all_stores_use_short_model_every_cycle_and_keep_original_title():
    async def run():
        db=DB(':memory:')
        title='Placa-Mae Gigabyte B550 Aorus Elite Ax V2, Chipset B550, AMD Am4, Atx, DDR4, 9mb55aew2-00-10'
        r=Reading(title,'KaBuM','NewCondition','Pix',143900,'in_stock',identifiers={'brand':'gigabyte','mpn':'9mb55aew2 00 10'})
        urls=['https://www.kabum.com.br/produto/473028/modelo','https://www.pichau.com.br/modelo',
            'https://www.terabyteshop.com.br/produto/123/modelo','https://produto.mercadolivre.com.br/MLB-1234567890-modelo-_JM',
            'https://www.amazon.com.br/dp/B08KGVH7YC']
        config=SimpleNamespace(minimum=0,percent=0,target=None,interval=18000)
        try:
            ad=db.save_ad(urls[0],'KaBuM',r)
            pid,_=db.subscribe(db.request_scope(ad['id']),'all',config)
            search=SimpleNamespace(links=AsyncMock(return_value=urls))
            def canonical(u):
                host=urlsplit(u).hostname.removeprefix('www.')
                return u,'mercadolivre.com.br' if host=='produto.mercadolivre.com.br' else host
            m=Monitor(db,config,SimpleNamespace(canonical=canonical),search,AsyncMock())
            async def read(url):
                if 'pichau' in url:raise ReadError('blocked_no_bypass')
                return [replace(r,title='Gigabyte B550 AORUS ELITE AX V2 WiFi DDR4 AM4',seller=canonical(url)[1])]
            m.read=AsyncMock(side_effect=read)
            for _ in range(2):await m.check(pid)
            assert [c.args[0] for c in search.links.await_args_list]==['gigabyte b550 aorus elite ax v2']*2
            assert [c.args[0] for c in m.read.await_args_list]==urls*2
            assert db.get_ad(ad['id'])['url']==urls[0]
            assert db.rows('SELECT query FROM products WHERE id=?',(pid,))[0]['query']==title
            assert len(db.rows('SELECT * FROM candidates WHERE product=?',(pid,)))==5
            assert len(db.rows('SELECT * FROM series'))==4
            assert not db.rows('SELECT * FROM alerts')
        finally:db.conn.close()
    asyncio.run(run())


def test_short_query_never_approves_variant_without_identity_evidence():
    seed=Reading('Gigabyte B550 Aorus Elite AX V2','','','',None)
    other=replace(seed,title='Placa Mae Gigabyte B550 Aorus Elite AX V2 DDR4 WiFi')
    assert monitoring_search_terms(seed.title)==monitoring_search_terms(other.title)
    assert same_product(seed,other) is None
    assert same_product(seed,replace(other,title='Gigabyte B550 Aorus Elite V2')) is False
