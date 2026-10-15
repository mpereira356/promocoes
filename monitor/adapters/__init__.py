from .base import StructuredAdapter
from .kabum import KabumAdapter
from .pichau import PichauAdapter
from .terabyte import TerabyteAdapter

ADAPTERS = {
    "kabum.com.br": KabumAdapter,
    "pichau.com.br": PichauAdapter,
    "terabyteshop.com.br": TerabyteAdapter,
}


def adapter(domain):
    return ADAPTERS.get(domain, StructuredAdapter)()
