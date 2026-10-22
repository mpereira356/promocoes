"""Catalogo extensivel: links observados nas lojas, sem fabricar rotas por slug."""
import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from ..models import normalize
from ..adapters.base import ReadError

SEED = Path(__file__).with_name('category_seed.json')
ROOT_LABELS = {
    'hardware': 'Hardware', 'perifericos': 'Periféricos', 'computadores': 'Computadores',
    'pc-gamer': 'PC Gamer', 'monitores': 'Monitores', 'notebooks': 'Notebooks',
    'cadeira': 'Cadeiras', 'cadeiras': 'Cadeiras', 'gabinetes': 'Gabinetes',
    'fontes': 'Fontes', 'refrigeracao': 'Refrigeração', 'games': 'Games e Consoles',
    'video-games': 'Games e Consoles', 'rede': 'Redes e Wi-Fi', 'redes-wireless': 'Redes e Wi-Fi',
    'casa-e-lazer': 'Casa e Lazer', 'home-e-eletro': 'Casa e Eletro', 'pets': 'Pets',
    'casa-inteligente': 'Casa Inteligente', 'eletronicos': 'Eletrônicos',
    'impressao3D': 'Impressão 3D', 'mesa-gamer': 'Mesas', 'tv': 'TVs',
    'mochilas': 'Mochilas', 'vestuario': 'Vestuário', 'esporte': 'Esportes',
    'kit-upgrade': 'Kit Upgrade', 'lifestyle': 'Lifestyle', 'seguranca': 'Segurança',
    'geek': 'Geek', 'diversos': 'Diversos', 'inteligencia-artificial': 'Inteligência Artificial',
    'open-box': 'Open Box', 'openbox': 'Open Box', 'energetico': 'Energéticos',
}
BLOCKED = {'produto', 'produtos', 'busca', 'cart', 'carrinho', 'account', 'customer',
    'login', 'cadastro', 'cadastro.obj', 'central.obj', 'faleconosco.obj', 'lista-desejos',
    'hotsite', 'promocao', 'promocoes', 'frete-gratis', 'cdn-cgi', 'quem-somos',
    'termos-de-aceite', 'politica-de-privacidade', 'atendimento', 'monte-seu-pc', 'mundos'}


@dataclass
class Category:
    key: str
    path: tuple[str, ...]
    urls: dict[str, str] = field(default_factory=dict)
    query: str = ''
    children: tuple['Category', ...] = ()

    @property
    def title(self):
        return ' > '.join(self.path)

    @property
    def memory_type(self):
        import re
        match = re.search(r'\bddr[345]\b', normalize(self.title))
        return match[0] if match and 'memoria' in normalize(self.title) else ''

    @property
    def search_query(self):
        return self.query or ('memória RAM ' + self.memory_type.upper() if self.memory_type else
            (self.path[-1] if self.path[-1] != 'Todas as subcategorias' else self.path[0]))

    def accepts_title(self, title):
        if not self.memory_type:
            return True
        import re
        text = normalize(title)
        return (set(re.findall(r'\bddr[345]\b', text)) == {self.memory_type}
                and not any(word in text.split() for word in
                    ('adaptador', 'adaptadora', 'testador', 'conversor', 'placa', 'computador')))

    def accepts_parent_title(self, title):
        from ..discovery import relevance
        text = normalize(title)
        if self.key.startswith('hardware/placas-mae') and text.startswith(('kit ', 'combo ')):
            return False
        if self.key == 'perifericos/mouse' and ('mouse pad' in text or 'mousepad' in text):
            return False
        return self.accepts_title(title) and bool(relevance(self.search_query, title))


def category_links(html, base, domain):
    """Links de navegacao observados, nunca anchors de anuncios/recomendacoes."""
    soup = BeautifulSoup(html, 'html.parser')
    if domain == 'terabyteshop.com.br':
        candidates = soup.select('.header-mega-menu a[href], .header-mega-menu-container a[href], #menuDepartamento a[href]')
    elif domain == 'pichau.com.br':
        candidates = soup.select('.embla__slide a[title][href]')
    else:
        candidates = soup.select('nav a[href], header a[href]')
    labels = {}
    for a in soup.find_all('a', href=True):
        label = a.get_text(' ', strip=True)
        if label and normalize(label) not in ('ver todos', 'ver mais') and len(label) <= 70:
            labels.setdefault(urljoin(base, a['href'].strip()), label)
    result = []
    seen = set()
    for a in candidates:
        url = urljoin(base, a['href'].strip())
        p = urlsplit(url)
        segments = p.path.strip('/').split('/')
        label = labels.get(url) or a.get('title') or a.get_text(' ', strip=True)
        if (p.scheme != 'https' or p.username or p.password or p.port not in (None, 443)
                or (p.hostname or '').removeprefix('www.') != domain or p.query or p.fragment
                or not segments[0] or segments[0].lower() in BLOCKED or '.' in segments[0]
                or a.has_attr('data-cy') or len(label) > 70 or not label
                or normalize(label) in ('ver todos', 'ver mais') or url in seen):
            continue
        seen.add(url)
        result.append({'domain': domain, 'title': label, 'url': url})
    return result


def entry(row):
    p = urlsplit(row['url'])
    segments = p.path.strip('/').split('/')
    root = ROOT_LABELS.get(segments[0], segments[0].replace('-', ' ').title())
    # Equivalencias explicitas, nao similaridade livre entre categorias.
    aliases = {'placa-m-e': 'placas-mae', 'placa-de-video': 'placas-de-video',
               'memorias': 'memoria-ram', 'cadeira': 'cadeiras', 'video-games': 'games',
               'redes-wireless': 'rede', 'openbox': 'open-box'}
    key = '/'.join(aliases.get(s, s) for s in segments)
    if key == 'hardware/hard-disk/ssd':
        key = 'hardware/ssd'
    title = row['title'].strip()
    if len(segments) == 1:
        path = (root, 'Todas as subcategorias')
    else:
        path = (root, title)
        if len(segments) > 2:
            path = (root, segments[-2].replace('-', ' ').title(), title)
    if key == 'hardware/placas-mae':
        path = ('Hardware', 'Placas-mãe')
    return Category(row.get('key', key), tuple(row.get('path', path)), {row['domain']: row['url']})


class CategoryCatalog:
    def __init__(self):
        self.items = {}
        self.lock = asyncio.Lock()
        self.refreshed_at = 0
        self.refresh_notices = []
        if SEED.exists():
            for row in json.loads(SEED.read_text(encoding='utf-8'))['links']:
                self.add(entry(row))

    def add(self, category):
        if category.key in self.items:
            self.items[category.key].urls.update(category.urls)
        else:
            self.items[category.key] = category

    def parent_urls(self, category):
        """Use a mapped parent only with a title filter for the requested child."""
        if '/' not in category.key:
            return {}
        result = {}
        key = category.key.rsplit('/', 1)[0]
        while key:
            parent = self.items.get(key)
            for domain, url in parent.urls.items() if parent else []:
                if domain not in category.urls:
                    result.setdefault(domain, url)
            key = key.rsplit('/', 1)[0] if '/' in key else ''
        return result

    def available(self, domains):
        return [c for c in self.items.values() if set(c.urls) & set(domains)]

    def navigation_path(self, category):
        """Navigation groups related departments without inventing store URLs."""
        keys = category.key.split('/')
        labels = []
        for index in range(len(keys)):
            ancestor = self.items.get('/'.join(keys[:index + 1]))
            label = ancestor.path[-1] if ancestor else keys[index].replace('-', ' ').title()
            if label == 'Todas as subcategorias':
                label = ancestor.path[0]
            labels.append(label)
        computer_roots = {'hardware', 'perifericos', 'computadores', 'pc-gamer', 'monitores',
                          'notebooks', 'gabinetes', 'fontes', 'refrigeracao', 'kit-upgrade'}
        if keys[0] in computer_roots:
            if keys[0] in ('hardware', 'perifericos') and len(keys) > 1:
                return ('Computadores', *labels[1:])
            if keys[0] == 'computadores':
                labels[0] = 'Computadores prontos'
            return ('Computadores', *labels)
        return tuple(labels)

    def navigation_groups(self, domains):
        return sorted({self.navigation_path(c)[0] for c in self.available(domains)})

    def descendants(self, path, domains):
        enabled = set(domains)
        return [c for c in self.items.values()
                if (set(c.urls) | set(self.parent_urls(c))) & enabled
                and self.navigation_path(c)[:len(path)] == path]

    def branches(self, path, domains):
        branches = {self.navigation_path(c)[:len(path) + 1]
                    for c in self.descendants(path, domains) if len(self.navigation_path(c)) > len(path)}
        priorities = ['placas mae', 'mouse', 'teclado', 'processadores', 'memoria ram', 'ssd',
                      'placa de video', 'computadores prontos', 'notebooks', 'monitores']
        def order(branch):
            label = normalize(branch[-1])
            rank = priorities.index(label) if path == ('Computadores',) and label in priorities else len(priorities)
            return rank, branch
        return sorted(branches, key=order)

    def scope(self, path, domains):
        children = self.descendants(path, domains)
        if not children:
            raise ValueError('Nenhuma categoria mapeada neste grupo para as lojas habilitadas.')
        if len(children) == 1:
            return children[0]
        digest = hashlib.sha256('/'.join(path).encode()).hexdigest()[:16]
        return Category('grupo/' + digest, (*path, 'Tudo'), children=tuple(children))

    def sources(self, category, domain):
        """Minimal observed category URLs, preserving different store hierarchies."""
        if not category.children:
            url = category.urls.get(domain) or self.parent_urls(category).get(domain)
            return [(category, url)] if url else []
        candidates = []
        for child in category.children:
            candidates.extend(self.sources(child, domain))
        candidates.sort(key=lambda item: (len(urlsplit(item[1]).path), item[1],
                                           domain not in item[0].urls, len(item[0].key)))
        result = []
        for child, url in candidates:
            target = urlsplit(url)
            if any((urlsplit(old).hostname or '').removeprefix('www.') == (target.hostname or '').removeprefix('www.')
                   and (target.path.rstrip('/') == urlsplit(old).path.rstrip('/') or
                        target.path.startswith(urlsplit(old).path.rstrip('/') + '/'))
                   and target.query == urlsplit(old).query for _, old in result):
                continue
            result.append((child, url))
        return result

    def stores_for(self, category, domains):
        if category.query:
            return list(domains)
        return [d for d in domains if self.sources(category, d)]

    def find(self, query, domains):
        query = normalize(query)
        aliases = {'celulares': 'smartphone', 'placa mae': 'placas mae', 'placas de video': 'placa de video',
                   'memoria ram': 'memoria', 'televisao': 'tv', 'notebook': 'notebooks',
                   'mouse': 'mouses', 'teclado': 'teclados'}
        words = set(aliases.get(query, query).split())
        def score(c):
            text = normalize(c.title + ' ' + c.key)
            if {query, aliases.get(query, query)} & {normalize(c.title), normalize(c.path[-1])}:
                return 100
            return sum(any(w == t or (len(w) >= 4 and t.startswith(w.rstrip('s'))) for t in text.split()) for w in words) / max(len(words), 1)
        enabled = set(domains)
        candidates = (c for c in self.items.values() if (set(c.urls) | set(self.parent_urls(c))) & enabled)
        return sorted((c for c in candidates if score(c) >= 1), key=lambda c: (-score(c), len(c.key.split('/')), c.title))

    def request(self, text, fetcher):
        text = text.strip()
        if not text or len(text) > 600:
            raise ValueError('Informe uma categoria ou link com até 600 caracteres.')
        digest = hashlib.sha256(text.encode()).hexdigest()[:16]
        if text.startswith('https://'):
            url, domain = fetcher.canonical(text)
            from .adapters import ADAPTERS
            if domain not in ADAPTERS:
                raise ValueError('A loja deste link não tem adaptador de categorias.')
            return Category('link/' + digest, ('Página de categoria informada', urlsplit(url).path), {domain: url})
        if '://' in text:
            raise ValueError('Use um link HTTPS de uma loja autorizada.')
        query = {'celulares': 'smartphone', 'smartphones': 'smartphone', 'brinquedos': 'brinquedo',
                 'televisores': 'tv', 'geladeiras': 'geladeira', 'teclados': 'teclado',
                 'mouses': 'mouse', 'notebooks': 'notebook'}.get(normalize(text), text)
        return Category('termo/' + digest, ('Categoria por termo', text), query=query)

    async def refresh(self, fetcher, domains):
        if self.lock.locked():
            raise ValueError('A atualização das categorias já está em andamento.')
        async with self.lock:
            if self.refreshed_at and time.monotonic() - self.refreshed_at < 3600:
                return self.refresh_notices + ['Catálogo em cache: atualização disponível após uma hora.']
            notices = []
            for domain in domains:
                if domain not in ('pichau.com.br', 'terabyteshop.com.br', 'kabum.com.br'):
                    notices.append(domain + ': descoberta automática do menu ainda não validada.')
                    continue
                try:
                    html, final = await fetcher.html('https://www.' + domain + '/')
                    if fetcher.canonical(final)[1] != domain:
                        raise ReadError('redirect_changed_store')
                    rows = category_links(html, final, domain)
                    for row in rows:
                        self.add(entry(row))
                    notices.append(f'{domain}: {len(rows)} links de navegação extraídos de 1 página; cobertura parcial.')
                except ReadError as exc:
                    notices.append(f'{domain}: menu não atualizado ({exc}); catálogo anterior preservado.')
            self.refreshed_at = time.monotonic()
            self.refresh_notices = notices
            return notices
