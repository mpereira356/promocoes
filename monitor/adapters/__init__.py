from .base import StructuredAdapter
from .kabum import KabumAdapter
from .pichau import PichauAdapter
from .terabyte import TerabyteAdapter
from .mercadolivre import MercadoLivreAdapter
from .amazon import AmazonAdapter
from .sensetup import SensetupAdapter
from .elements import ElementsAdapter
from .flexform import FlexformAdapter

ADAPTERS = {
    "kabum.com.br": KabumAdapter,
    "pichau.com.br": PichauAdapter,
    "terabyteshop.com.br": TerabyteAdapter,
    "mercadolivre.com.br": MercadoLivreAdapter,
    "amazon.com.br": AmazonAdapter,
    "sensetup.com.br": SensetupAdapter,
    "loja.elements.com.br": ElementsAdapter,
    "flexform.com.br": FlexformAdapter,
}


def adapter(domain):
    return ADAPTERS.get(domain, StructuredAdapter)()
