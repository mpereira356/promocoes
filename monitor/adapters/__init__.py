from .lacoste import LacosteAdapter
from .patoloco import PatolocoAdapter
from .base import StructuredAdapter
from .kabum import KabumAdapter
from .pichau import PichauAdapter
from .terabyte import TerabyteAdapter
from .mercadolivre import MercadoLivreAdapter
from .amazon import AmazonAdapter
from .sensetup import SensetupAdapter
from .elements import ElementsAdapter
from .flexform import FlexformAdapter
from .shopee import ShopeeAdapter
from .magalu import MagaluAdapter
from .frigelar import FrigelarAdapter
from .brastemp import BrastempAdapter

ADAPTERS = {
    "patoloco.com.br": PatolocoAdapter,
    "lacoste.com": LacosteAdapter,
    "kabum.com.br": KabumAdapter,
    "pichau.com.br": PichauAdapter,
    "terabyteshop.com.br": TerabyteAdapter,
    "mercadolivre.com.br": MercadoLivreAdapter,
    "amazon.com.br": AmazonAdapter,
    "sensetup.com.br": SensetupAdapter,
    "loja.elements.com.br": ElementsAdapter,
    "flexform.com.br": FlexformAdapter,
    "shopee.com.br": ShopeeAdapter,
    "magazineluiza.com.br": MagaluAdapter,
    "frigelar.com.br": FrigelarAdapter,
    "brastemp.com.br": BrastempAdapter,
}


def adapter(domain):
    return ADAPTERS.get(domain, StructuredAdapter)()
