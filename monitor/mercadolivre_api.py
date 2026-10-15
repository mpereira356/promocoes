"""API oficial apenas para descobrir links; precos/estoque nao sao importados."""
import asyncio
import httpx
from .adapters.base import ReadError
from .adapters.mercadolivre import MercadoLivreAdapter
from .discovery import LinkCandidate


async def discover(query, token, fetcher, client=None):
    if not token.strip():
        raise ReadError('mercadolivre_api_token_missing')
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=30, follow_redirects=False)
    try:
        for attempt in range(3):
            try:
                response = await client.get(
                    'https://api.mercadolibre.com/sites/MLB/search',
                    params={'q': query, 'limit': 20},
                    headers={'Authorization': 'Bearer ' + token.strip()},
                )
            except httpx.RequestError:
                response = None
            if response is not None:
                if response.status_code == 401:
                    raise ReadError('mercadolivre_api_token_expired')
                if response.status_code == 403:
                    raise ReadError('mercadolivre_api_access_denied')
                if response.status_code == 200:
                    break
                if response.status_code not in (429, 500, 502, 503, 504):
                    raise ReadError('mercadolivre_api_failed')
            if attempt == 2:
                raise ReadError('mercadolivre_api_failed')
            wait = 2 ** (attempt + 1)
            if response is not None:
                retry = response.headers.get('Retry-After', '')
                if retry and (not retry.isdigit() or int(retry) > 60):
                    raise ReadError('rate_limit_deferred')
                wait = max(wait, int(retry or 0))
            await asyncio.sleep(wait)
        try:
            items = response.json()['results']
            if not isinstance(items, list):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ReadError('mercadolivre_api_failed') from None
        result, seen = [], set()
        adapter = MercadoLivreAdapter()
        for item in items:
            if not isinstance(item, dict):
                continue
            url, title = item.get('permalink'), item.get('title')
            if not isinstance(url, str) or not isinstance(title, str) or not title.strip():
                continue
            try:
                url, domain = fetcher.canonical(url)
            except (ValueError, ReadError):
                continue
            if domain == 'mercadolivre.com.br' and adapter.is_product_url(url) and url not in seen:
                seen.add(url)
                result.append(LinkCandidate(url, title))
        return result
    finally:
        if owns_client:
            await client.aclose()
