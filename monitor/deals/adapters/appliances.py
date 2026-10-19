"""Consulta por termo e links de categoria explícitos; sem rotas presumidas."""
from .base import CategoryAdapter


class ShopeeCategories(CategoryAdapter):
    domain = 'shopee.com.br'
    categories = {}
    limitations = ('Somente ofertas individuais estruturadas; cupons e preços de membros não são inferidos.',)


class MagaluCategories(CategoryAdapter):
    domain = 'magazineluiza.com.br'
    categories = {}
    limitations = ('Somente dados estruturados; preço anterior e modalidade por vendedor não validados em página real.',)


class FrigelarCategories(CategoryAdapter):
    domain = 'frigelar.com.br'
    categories = {}
    limitations = ('Preço anterior ausente não qualifica no filtro percentual; frete não cotado.',)
