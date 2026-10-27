"""Restrict explicit butcher queries to relevant stores before using search quotas."""
from .models import normalize

GROCERY_DOMAINS = (
    'atacadao.com.br', 'extramercado.com.br',
    'mercado.carrefour.com.br', 'boasupermercados.com.br',
)
GENERAL_MARKETS = (
    'mercadolivre.com.br', 'amazon.com.br', 'shopee.com.br', 'magazineluiza.com.br',
)


def is_meat_query(query):
    words = set(normalize(query).split())
    # Product types only: do not reroute a meat grinder or a barbecue utensil.
    if words & {'moedor', 'amaciador', 'faca', 'garfo', 'tabua', 'churrasqueira',
                'termometro', 'grelha', 'espeto', 'panela', 'chapa', 'livro'}:
        return False
    return bool(words & {'picanha', 'picanhas', 'maturatta', 'alcatra', 'fraldinha',
                         'contrafile', 'costela', 'maminha', 'acougue'})


def search_domains(query, domains):
    if not is_meat_query(query):
        return tuple(domains)
    # Groceries first: unrelated hardware calls must not consume the shared quota.
    return tuple(d for d in (*GROCERY_DOMAINS, *GENERAL_MARKETS) if d in domains)
