from .base import CategoryAdapter


class MercadoLivreCategories(CategoryAdapter):
    domain = 'mercadolivre.com.br'
    categories = {'hardware/placas-mae': 'https://lista.mercadolivre.com.br/informatica/componentes-pc/placas/placas-mae/'}
    limitations = ('Categoria limitada a dados estruturados; acesso real pode ser bloqueado. Catalogos com varios vendedores nao qualificam como oferta individual.',)
    # Bloqueios sao reportados. Nao substituir categoria por precos de snippets.
