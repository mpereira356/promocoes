"""Entrega de buscas com resumo final, sem transformar erros em ofertas."""
import logging
import httpx
from .adapters import adapter
from .adapters.base import ReadError
from .discovery import REASONS, relevance, SearchLinks
from .presentation import rank_offers, send_offer
from .search import search_error_message


async def deliver_search(monitor, fetcher, db, bot, chat, query, send, marketplace_only=False):
    sent = failed = unverified = priced = rejected = 0
    notices = []
    unverified_links, failures = [], []
    paused = {}
    skipped = 0
    interrupted = False
    try:
        if marketplace_only:
            urls = await monitor.search.marketplace_links(query)
        else:
            urls = [query] if query.startswith('https://') else await monitor.search.links(query)
        notices = list(getattr(urls, 'notices', []))
        limited_stores = {n.split(':', 1)[0] for n in notices if 'limite da busca externa' in n.casefold()}
        if limited_stores and db is not None and callable(getattr(db, 'rows', None)):
            known, per_store, seen = [], {}, set(urls)
            for row in db.rows('SELECT url,title,store FROM ads ORDER BY observed_at DESC LIMIT 100'):
                store = row['store']
                if store in limited_stores and per_store.get(store, 0) < 3 and row['url'] not in seen and relevance(query, row['title']):
                    known.append(row['url'])
                    seen.add(row['url'])
                    per_store[store] = per_store.get(store, 0) + 1
            if known:
                urls = SearchLinks(list(urls) + known, candidates=getattr(urls, 'candidates', {}))
                notices.append(f'Reutilizados {len(known)} links de anúncios já consultados e salvos no SQLite. Preço e estoque serão lidos novamente nas lojas.')
        if not urls:
            await send('Não encontramos ofertas nesta consulta.')
        offers = []
        for url in urls:
            candidate = getattr(urls, 'candidates', {}).get(url)
            from urllib.parse import urlsplit
            domain_key = (urlsplit(url).hostname or '').removeprefix('www.')
            if domain_key in ('produto.mercadolivre.com.br', 'lista.mercadolivre.com.br'):
                domain_key = 'mercadolivre.com.br'
            if domain_key in paused:
                paused[domain_key]['skipped'] += 1
                skipped += 1
                continue
            external = candidate is not None and candidate.source == 'Tavily Search'
            if external:
                _, domain = fetcher.canonical(url)
                if domain == 'mercadolivre.com.br' and not adapter(domain).is_product_url(url):
                    unverified_links.append((candidate, 'Catálogo com vários vendedores; nenhuma oferta individual confirmada'))
                    unverified += 1
                    continue
            try:
                readings = await monitor.read(url)
                if not readings:
                    raise ReadError('structured_product_missing_or_ambiguous')
                if not query.startswith('https://') and any(not relevance(query, r.title) for r in readings):
                    raise ReadError('different_model')
                _, domain = fetcher.canonical(url)
                offers.extend((r, url, adapter(domain).name) for r in readings)
            except Exception as exc:
                if isinstance(exc, ReadError) and str(exc) == 'different_model':
                    rejected += 1
                    continue
                failed += 1
                if isinstance(exc, ReadError):
                    reason = REASONS.get(str(exc), 'A página não possui uma oferta que o leitor consiga validar')
                elif isinstance(exc, (OSError, httpx.RequestError)):
                    reason = 'A conexão com a loja falhou por rede ou DNS'
                else:
                    reason = 'O leitor encontrou um erro interno; consulte o tipo registrado nos logs do serviço'
                logging.getLogger(__name__).critical('search_offer_failed type=%s', type(exc).__name__)
                if isinstance(exc, ReadError) and str(exc) in ('blocked_no_bypass', 'captcha_no_bypass', 'domain_access_cooldown'):
                    paused[domain_key] = {'reason': reason, 'url': url, 'skipped': 0}
                    continue
                if external:
                    unverified_links.append((candidate, reason))
                    unverified += 1
                else:
                    failures.append((url, reason))
        for r, url, store, rank, provisional in rank_offers(offers):
            ad = db.save_ad(url, store, r)
            await send_offer(bot, chat, r, url, store, rank, provisional, ad['id'])
            sent += 1
            priced += int(getattr(r, 'price', None) is not None and getattr(r, 'price', 0) > 0)
        if failures:
            await send('⚠️ Ofertas não verificadas\n\n' + '\n\n'.join(
                reason + '.\n' + url for url, reason in failures))
        for domain, item in paused.items():
            store = adapter(domain).name
            await send(f'⚠️ {store} — acesso suspenso\n\n{item["reason"]}.\n'
                f'Outros links não consultados nesta busca: {item["skipped"]}. As demais lojas continuam.\n{item["url"]}')
        for text in grouped_unverified(unverified_links):
            await send(text)
        if notices:
            limited = [n for n in notices if 'limite da busca externa' in n.casefold()]
            if limited:
                stores = ', '.join(dict.fromkeys(n.split(':', 1)[0] for n in limited))
                notices = [n for n in notices if n not in limited and 'Mercado Livre: a descoberta falhou' not in n]
                notices.append(f'Índice externo temporariamente limitado. Lojas afetadas: {stores}. Consultas à fonte foram suspensas respeitando o limite. Links conhecidos podem ser consultados diretamente; não há descoberta nova garantida durante a pausa.')
            await send('⚠️ Avisos da pesquisa\n\n' + '\n'.join(notices))
    except ReadError as exc:
        interrupted = True
        await send(search_error_message(str(exc)))
    except Exception:
        interrupted = True
        await send('⚠️ A busca foi interrompida por uma falha. Tente novamente mais tarde.')
    finally:
        status = ('⚠️ Pesquisa encerrada com falha' if interrupted else
            '⚠️ Pesquisa concluída com limitações' if failed or unverified or notices or (sent and not priced) else '✅ Pesquisa concluída')
        await send(f'{status}\n\nOfertas enviadas: {sent}\nLinks com falha de leitura: {failed}\nAvisos das lojas: {len(notices)}\nLinks para conferência: {unverified}\nPreços lidos nas ofertas enviadas: {priced}\nCandidatos descartados por incompatibilidade: {rejected}\nLinks não consultados por bloqueio da loja: {skipped}')


def grouped_unverified(entries):
    from urllib.parse import urlsplit
    groups = {}
    for candidate, reason in entries:
        domain = (urlsplit(candidate.url).hostname or '').removeprefix('www.')
        domain = 'mercadolivre.com.br' if domain == 'produto.mercadolivre.com.br' else domain
        groups.setdefault(domain, []).append((candidate, reason))
    for domain, candidates in groups.items():
        text = (f'🔎 {adapter(domain).name} — links sem preço confirmado\n\n'
            'Fonte: índice externo Tavily Search. Título e oferta ainda não conferidos na página.\n'
            'Preço, estoque, vendedor, condição e pagamento não foram verificados.\n'
            'Este grupo não ativa monitoramento nem alertas.\n\n')
        text += '\n\n'.join(f'{i}. {c.title[:200]}\n{c.url}' for i, (c, _) in enumerate(candidates, 1))
        text += '\n\nLeitura da página: ' + '; '.join(dict.fromkeys(reason for _, reason in candidates)) + '.'
        yield text


def discovered_text(candidate):
    from urllib.parse import urlsplit
    domain = urlsplit(candidate.url).hostname.removeprefix('www.')
    store = adapter('mercadolivre.com.br' if domain == 'produto.mercadolivre.com.br' else domain).name
    return (
        '🔎 ' + store + ' — link encontrado\n\n'
        + candidate.title[:350] + '\n\n'
        + '📌 Fonte: índice externo Tavily Search. O título ainda não foi conferido na página.\n'
        + '❓ Preço, estoque, vendedor, condição e forma de pagamento não foram verificados.\n'
        + '⚠️ Ao abrir, confira o modelo, a oferta e o vendedor. Catálogos podem alternar vendedores.\n'
        + '⏸️ Este resultado não ativa monitoramento nem alertas.\n\n'
        + '🔗 ' + candidate.url
    )
