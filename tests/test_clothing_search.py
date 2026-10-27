import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from monitor.discovery import relevance, candidate_relevance, reading_relevance, LinkCandidate, DirectSearch
from monitor.models import Reading
from monitor.config import DEFAULT_DOMAINS
from monitor.network import Fetcher


@pytest.mark.parametrize('title', [
    'Fone Esportivo Condução Óssea Leve Com Microfone Hd Claro',
    'Fone Condução Óssea Esportivo Leve Com Microfone Hd',
])
def test_actual_wrong_headphones_never_match_cap(title):
    assert relevance('Boné Esportivo Leve', title) == 0
    assert reading_relevance('Boné Esportivo Leve', Reading(title, '', '', '', 12990)) == 0


@pytest.mark.parametrize('query,title', [
    ('Boné Esportivo Leve', 'Boné Esportivo Leve Lacoste'),
    ('Bonés Esportivos', 'Boné Esportivo Leve'),
    ('Camisetas leves', 'Camiseta leve'),
])
def test_clothing_plural_category(query, title):
    assert relevance(query, title) > 0


def test_lacoste_brand_can_come_from_official_store_and_product():
    url = 'https://www.lacoste.com/br/lacoste/bones/RK1234.html'
    assert candidate_relevance('Boné Esportivo Leve Lacoste', LinkCandidate(url, 'Boné Esportivo Leve')) > 0
    r = Reading('Boné Esportivo Leve', '', '', '', 20000, identifiers={'brand': 'lacoste'})
    assert reading_relevance('Boné Esportivo Leve Lacoste', r) > 0


@pytest.mark.parametrize('domains,upgraded', [
    (','.join(DEFAULT_DOMAINS.split(',')[:14]), True),
    (','.join(DEFAULT_DOMAINS.split(',')[:14]).replace('amazon.com.br', 'www.amazon.com.br'), True),
    ('kabum.com.br,pichau.com.br,terabyteshop.com.br', True),
    ('amazon.com.br,lacoste.com', False),
    ('amazon.com.br', False),
    (DEFAULT_DOMAINS, False),
    (','.join(DEFAULT_DOMAINS.split(',')[:17]), False),
])
def test_real_installer_migration_preserves_custom_lists(tmp_path, domains, upgraded, monkeypatch):
    script = Path('deploy/install-kali.sh').read_text(encoding='utf-8')
    code = script.split('python3 - "$install_dir/.env" <<\'PY\'\n', 1)[1].split('\nPY\n', 1)[0]
    env = tmp_path / '.env'
    before = 'ALLOWED_DOMAINS=' + domains + '\nDATABASE_PATH=data/monitor.sqlite3\nPRIVATE_VALUE=unchanged\n'
    env.write_text(before, encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['migration', str(env)])
    exec(compile(code, 'installer-migration', 'exec'), {})
    after = env.read_text(encoding='utf-8')
    assert 'DATABASE_PATH=data/monitor.sqlite3\nPRIVATE_VALUE=unchanged' in after
    assert after == (before.replace(domains, DEFAULT_DOMAINS) if upgraded else before)


def test_direct_search_actually_calls_lacoste_and_rejects_headphones():
    async def run():
        config = SimpleNamespace(domains=('lacoste.com',), browser=False)
        fetcher = Fetcher(config)
        url = 'https://www.lacoste.com/br/lacoste/bones/RK1234.html?color=001'
        async def html(search_url):
            assert search_url == 'https://www.lacoste.com/br/sitemap_1-image.xml'
            return (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
                    f'<url><loc>{url.replace("&", "&amp;")}</loc><image:image><image:title>Boné Esportivo Leve</image:title></image:image></url></urlset>'), search_url
        fetcher.html = AsyncMock(side_effect=html)
        try:
            links = await DirectSearch(config, fetcher).links('Boné Esportivo Leve')
            assert links == [url]
            assert fetcher.html.await_count == 1
        finally:
            await fetcher.client.aclose()
    asyncio.run(run())
