"""Entrega de buscas com resumo final, sem transformar erros em ofertas."""
import logging
import httpx
from .adapters import adapter
from .adapters.base import ReadError
from .discovery import REASONS, relevance
from .presentation import rank_offers, send_offer
from .search import search_error_message


async def deliver_search(monitor, fetcher, db, bot, chat, query, send, marketplace_only=False):
    sent = failed = unverified = priced = 0
    notices = []
    interrupted = False
    try:
        if marketplace_only:
            urls = await monitor.search.marketplace_links(query)
        else:
            urls = [query] if query.startswith('https://') else await monitor.search.links(query)
        notices = getattr(urls, 'notices', [])
        if not urls:
            await send('Não encontramos ofertas nesta consulta.')
        offers = []
        for url in urls:
            candidate = getattr(urls, 'candidates', {}).get(url)
            external = candidate is not None and candidate.source == 'Tavily Search'
            if external:
                _, domain = fetcher.canonical(url)
                if domain == 'mercadolivre.com.br' and not adapter(domain).is_product_url(url):
                    await send(discovered_text(candidate))
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
                failed += 1
                if isinstance(exc, ReadError):
                    reason = REASONS.get(str(exc), 'A página não possui uma oferta que o leitor consiga validar')
                elif isinstance(exc, (OSError, httpx.RequestError)):
                    reason = 'A conexão com a loja falhou por rede ou DNS'
                else:
                    reason = 'O leitor encontrou um erro interno; consulte o tipo registrado nos logs do serviço'
                logging.getLogger(__name__).critical('search_offer_failed type=%s', type(exc).__name__)
                if external:
                    await send(discovered_text(candidate) + '\n⚠️ Leitura da página: ' + reason + '.')
                    unverified += 1
                else:
                    await send('⚠️ Não foi possível ler esta oferta. Motivo: ' + reason + '.\n' + url)
        for r, url, store, rank, provisional in rank_offers(offers):
            ad = db.save_ad(url, store, r)
            await send_offer(bot, chat, r, url, store, rank, provisional, ad['id'])
            sent += 1
            priced += int(getattr(r, 'price', None) is not None and getattr(r, 'price', 0) > 0)
        if notices:
            await send('⚠️ Avisos da pesquisa\n\n' + '\n'.join(notices))
    except ReadError as exc:
        interrupted = True
        await send(search_error_message(str(exc)))
    except Exception:
        interrupted = True
        await send('⚠️ A busca foi interrompida por uma falha. Tente novamente mais tarde.')
    finally:
        status = ('⚠️ Pesquisa encerrada com falha' if interrupted else
            '⚠️ Pesquisa concluída com limitações' if failed or (sent and not priced) else '✅ Pesquisa concluída')
        await send(f'{status}\n\nOfertas enviadas: {sent}\nLinks com falha de leitura: {failed}\nAvisos das lojas: {len(notices)}\nLinks para conferência: {unverified}\nPreços lidos nas ofertas enviadas: {priced}')


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
