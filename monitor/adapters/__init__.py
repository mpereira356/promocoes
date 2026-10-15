from .base import StructuredAdapter
from .kabum import KabumAdapter
from .pichau import PichauAdapter
from .terabyte import TerabyteAdapter
from .mercadolivre import MercadoLivreAdapter

ADAPTERS = {
    "kabum.com.br": KabumAdapter,
    "pichau.com.br": PichauAdapter,
    "terabyteshop.com.br": TerabyteAdapter,
    "mercadolivre.com.br": MercadoLivreAdapter,
}


def adapter(domain):
    return ADAPTERS.get(domain, StructuredAdapter)()
