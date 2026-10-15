"""Entrega de buscas com resumo final, sem transformar erros em ofertas."""
from .adapters import adapter
from .adapters.base import ReadError
from .discovery import REASONS
from .presentation import rank_offers, send_offer
from .search import search_error_message


async def deliver_search(monitor, fetcher, db, bot, chat, query, send):
    sent = failed = 0
    notices = []
    interrupted = False
    try:
        urls = [query] if query.startswith('https://') else await monitor.search.links(query)
        notices = getattr(urls, 'notices', [])
        if not urls:
            await send('Nenhuma oferta descoberta.')
        offers = []
        for url in urls:
            try:
                readings = await monitor.read(url)
                if not readings:
                    raise ReadError('structured_product_missing_or_ambiguous')
                _, domain = fetcher.canonical(url)
                offers.extend((r, url, adapter(domain).name) for r in readings)
            except Exception as exc:
                failed += 1
                reason = REASONS.get(str(exc), 'falha de leitura nao identificada') if isinstance(exc, ReadError) else 'falha interna de leitura'
                await send('Nao foi possivel ler esta oferta: ' + reason + '.\n' + url)
        for r, url, store, rank, provisional in rank_offers(offers):
            ad = db.save_ad(url, store, r)
            await send_offer(bot, chat, r, url, store, rank, provisional, ad['id'])
            sent += 1
        if notices:
            await send('Resumo das lojas sem resultados nesta consulta:\n' + '\n'.join(notices))
    except ReadError as exc:
        interrupted = True
        await send(search_error_message(str(exc)))
    except Exception:
        interrupted = True
        await send('Busca interrompida por uma falha. Tente novamente mais tarde.')
    finally:
        status = 'Pesquisa encerrada com falha' if interrupted else 'Pesquisa concluida'
        await send(f'{status}. Ofertas enviadas: {sent}. Links com falha de leitura: {failed}. Avisos das lojas: {len(notices)}.')
