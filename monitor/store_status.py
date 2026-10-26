"""Explain access state without treating HTTP success as verified pricing."""
import math
import time
from .adapters import adapter


def store_status(fetcher, domains):
    lines = ['🏪 Acesso às lojas', '']
    now = time.monotonic()
    for domain in domains:
        pause = max(fetcher.access_paused.get(domain, 0), fetcher.rate_paused.get(domain, 0))
        attempt = fetcher.page_access.get(domain, {})
        status = attempt.get('http_status')
        if pause > now:
            label = f'em pausa após bloqueio/limite; nova tentativa em {math.ceil((pause - now) / 60)} min'
        elif status == 200:
            label = 'última página acessada; preço depende dos dados do produto'
        elif status:
            label = f'última tentativa sem acesso (HTTP {status})'
        elif attempt:
            label = 'última tentativa sem resposta da loja'
        else:
            label = 'sem página consultada nesta execução'
        lines.append(adapter(domain).name + ': ' + label + '.')
    return '\n'.join(lines)
