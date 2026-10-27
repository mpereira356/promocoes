"""Explain access state without treating HTTP success as verified pricing."""
import math
import time
from .adapters import adapter


def store_status(fetcher, domains):
    lines = ['🏪 Acesso às lojas', '']
    cep = getattr(getattr(fetcher, 'config', None), 'grocery_postal_code', '')
    if cep:
        lines += ['CEP dos supermercados: ' + cep[:5] + '-' + cep[5:] + '.', '']
        if getattr(getattr(fetcher, 'config', None), 'grocery_mode', 'delivery') == 'visit':
            lines += ['Modo Posso ir à loja: entrega não exigida; estoque físico precisa de confirmação.', '']
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
        reader = getattr(fetcher, 'grocery_prices', None)
        region = reader.status.get(domain) if reader else None
        if region and region.get('postal_code') == cep:
            if region.get('store'):
                lines.append('  Loja regional: ' + region['store'] + '. Último produto: ' + region.get('stock', 'unknown') + '.')
            elif region.get('stock') == 'unverified_delivery_or_stock':
                lines.append('  Último produto sem estoque e entrega confirmados nas lojas consultadas para o CEP.')
    return '\n'.join(lines)
