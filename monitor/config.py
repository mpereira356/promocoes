import os
from dataclasses import dataclass
from decimal import Decimal
from dotenv import load_dotenv
import re


def normalize_domains(value):
    domains = []
    for item in value.split(","):
        domain = item.strip().lower().removeprefix("www.").rstrip(".")
        if not domain:
            continue
        if (
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain)
            or "." not in domain
        ):
            raise ValueError(
                "ALLOWED_DOMAINS deve conter dominios, sem https:// ou caminhos."
            )
        if domain not in domains:
            domains.append(domain)
    return tuple(domains)


@dataclass
class Config:
    token: str
    chat: int
    user: int
    domains: tuple
    db: str
    provider: str
    key: str
    interval: float
    delay: float
    minimum: int
    percent: Decimal
    target: int | None
    browser: bool
    mercadolivre_token: str = ''
    mercadolivre_discovery: str = 'external'

    @classmethod
    def load(cls):
        load_dotenv()

        def cents(key):
            value = Decimal(os.getenv(key, "0") or "0")
            if not value.is_finite() or value < 0:
                raise ValueError("Valor monetario invalido")
            return int(value * 100)

        c = cls(
            os.environ["TELEGRAM_BOT_TOKEN"],
            int(os.environ["TELEGRAM_CHAT_ID"]),
            int(os.environ["TELEGRAM_USER_ID"]),
            normalize_domains(
                os.getenv(
                    "ALLOWED_DOMAINS", "kabum.com.br,pichau.com.br,terabyteshop.com.br,mercadolivre.com.br"
                )
            ),
            os.getenv("DATABASE_PATH", "data/monitor.sqlite3"),
            os.getenv("SEARCH_PROVIDER", "direct").strip().lower(),
            os.getenv("SEARCH_API_KEY", ""),
            float(os.getenv("INTERVAL_HOURS", "5")) * 3600,
            float(os.getenv("REQUEST_DELAY", "3")),
            cents("MIN_DROP_BRL"),
            Decimal(os.getenv("MIN_DROP_PERCENT", "0")),
            cents("TARGET_PRICE") if os.getenv("TARGET_PRICE") else None,
            os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true",
            os.getenv('MERCADOLIVRE_ACCESS_TOKEN', '').strip(),
            os.getenv('MERCADOLIVRE_DISCOVERY', 'external').strip().lower(),
        )
        if (
            c.mercadolivre_discovery not in ('external', 'site')
            or c.user <= 0
            or c.interval <= 0
            or c.delay < 1
            or not c.percent.is_finite()
            or c.percent < 0
        ):
            raise ValueError("Configuracao invalida")
        return c
