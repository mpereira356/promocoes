from .shopify import ShopifyAdapter


class SensetupAdapter(ShopifyAdapter):
    name = 'Sensetup'
    domain = 'sensetup.com.br'
    sitemap_urls = ('https://sensetup.com.br/sitemap.xml',)
    product_selector = 'script#swishlist-bootstrap-data[type="application/json"]'
