from .kabum import KabumCategories
from .pichau import PichauCategories
from .terabyte import TerabyteCategories
from .amazon import AmazonCategories
from .mercadolivre import MercadoLivreCategories
from .chairs import SensetupCategories, ElementsCategories, FlexformCategories
from .appliances import ShopeeCategories, MagaluCategories, FrigelarCategories

ADAPTERS = {a.domain: a() for a in (KabumCategories, PichauCategories, TerabyteCategories, AmazonCategories, MercadoLivreCategories, SensetupCategories, ElementsCategories, FlexformCategories, ShopeeCategories, MagaluCategories, FrigelarCategories)}
from ..catalog import CategoryCatalog

_catalog = CategoryCatalog()
CATEGORIES = {key: category.path for key, category in _catalog.items.items()}
for _key, _category in _catalog.items.items():
    for _domain, _url in _category.urls.items():
        if _domain in ADAPTERS:
            ADAPTERS[_domain].categories[_key] = _url
