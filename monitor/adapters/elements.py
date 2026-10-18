from .shopify import ShopifyAdapter


class ElementsAdapter(ShopifyAdapter):
    name = 'Elements'
    domain = 'loja.elements.com.br'
    sitemap_urls = ('https://loja.elements.com.br/sitemap.xml',)
    product_selector = 'script[id^="d-product-json-"][type="application/json"]'
