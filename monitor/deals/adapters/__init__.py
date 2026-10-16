from .kabum import KabumCategories
from .pichau import PichauCategories
from .terabyte import TerabyteCategories
from .amazon import AmazonCategories
from .mercadolivre import MercadoLivreCategories

ADAPTERS = {a.domain: a() for a in (KabumCategories, PichauCategories, TerabyteCategories, AmazonCategories, MercadoLivreCategories)}
CATEGORIES = {'hardware/placas-mae': ('Hardware', 'Placas-mãe')}
