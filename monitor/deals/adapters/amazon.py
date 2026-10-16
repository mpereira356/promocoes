from .base import CategoryAdapter


class AmazonCategories(CategoryAdapter):
    domain = 'amazon.com.br'
    categories = {'hardware/placas-mae': 'https://www.amazon.com.br/Placas-maes/b?node=16364815011'}
    limitations = ('Categoria limitada a dados estruturados; HTML de categoria e preco anterior por vendedor ainda nao validados.',)
    # Somente ItemList/Product estruturados. Categoria HTML e preco riscado por
    # vendedor ainda nao validados; nao adivinhar seletores nem usar parcelas.
