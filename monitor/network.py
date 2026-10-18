import asyncio
import ipaddress
import socket
import time
from contextvars import ContextVar
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qsl, urlencode
from .robots import RobotsPolicy
import httpx
from .adapters.base import ReadError
from .challenges import is_access_challenge

# Escopo por tarefa: diagnósticos manuais nao contam consultas do agendador.
PAGE_AUDIT = ContextVar('price_monitor_page_audit', default=None)


class Fetcher:
    def __init__(self, config):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=30,
            follow_redirects=False,
            headers={"User-Agent": "PriceMonitor/1.0 (+personal price monitoring)"},
        )
        self.locks = {}
        self.last = {}
        self.robots = {}
        self.robots_diagnostics = {}
        self.content_types = {}
        self.browser_transport = None
        self.access_paused = {}
        self.page_access = {}

    def pause_access(self, domain):
        self.access_paused[domain] = time.monotonic() + 900

    def uses_browser(self, domain):
        return getattr(self.config, "browser", False) and domain in (
            "pichau.com.br",
            "terabyteshop.com.br",
            "mercadolivre.com.br",
        )

    def chromium(self):
        if self.browser_transport is None:
            from .browser import ChromiumTransport

            self.browser_transport = ChromiumTransport(self)
        return self.browser_transport

    def canonical(self, url):
        p = urlsplit(url)
        host = (p.hostname or "").lower()
        domain = host.removeprefix("www.")
        marketplace_host = host in (
            'lista.mercadolivre.com.br', 'produto.mercadolivre.com.br'
        )
        if marketplace_host:
            domain = 'mercadolivre.com.br'
        if (
            p.scheme != "https"
            or p.username
            or p.password
            or p.port not in (None, 443)
            or domain not in self.config.domains
            or (host not in (domain, "www." + domain) and not marketplace_host)
        ):
            raise ReadError("url_not_allowed")
        query = urlencode(
            [
                (k, v)
                for k, v in parse_qsl(p.query, keep_blank_values=True)
                if not k.lower().startswith("utm_")
                and k.lower() not in ("msockid", "gclid", "fbclid", "gad_source", "gad_campaignid", "gbraid", "wbraid", "srsltid")
            ]
        )
        return urlunsplit(("https", host, p.path or "/", query, "")), domain

    async def public(self, url):
        host = urlsplit(url).hostname
        for attempt in range(3):
            try:
                infos = await asyncio.get_running_loop().getaddrinfo(
                    host, 443, type=socket.SOCK_STREAM
                )
                break
            except OSError:
                if attempt == 2:
                    raise ReadError('network_dns_failure') from None
                await asyncio.sleep(2 ** (attempt + 1))
        if not infos or any(not ipaddress.ip_address(i[4][0]).is_global for i in infos):
            raise ReadError("non_public_address")

    async def request(self, url, check_robots=False, client=None):
        for redirect in range(5):
            url, domain = self.canonical(url)
            if self.access_paused.get(domain, 0) > time.monotonic():
                raise ReadError('domain_access_cooldown')
            if check_robots:
                await self.allowed_by_robots(url)
            await self.public(url)
            lock = self.locks.setdefault(domain, asyncio.Lock())
            for attempt in range(3):
                async with lock:
                    await asyncio.sleep(
                        max(
                            0,
                            self.last.get(domain, 0)
                            + self.config.delay
                            - time.monotonic(),
                        )
                    )
                    try:
                        if self.uses_browser(domain):
                            response = await self.chromium().get(url)
                        else:
                            response = await (client or self.client).get(url)
                    except ReadError as exc:
                        if str(exc) in ('blocked_no_bypass', 'captcha_no_bypass'):
                            self.pause_access(domain)
                        if str(exc) not in (
                            "browser_navigation_failed_TimeoutError",
                            "browser_connection_failed",
                        ):
                            raise
                        response = None
                    except httpx.RequestError:
                        response = None
                    finally:
                        self.last[domain] = time.monotonic()
                if response is not None and response.status_code not in (
                    429,
                    500,
                    502,
                    503,
                    504,
                ):
                    break
                if attempt == 2:
                    raise ReadError("network_or_rate_limit")
                wait = 2 ** (attempt + 1)
                if response is not None:
                    retry = response.headers.get("Retry-After", "")
                    if retry.isdigit():
                        wait = max(wait, int(retry))
                    elif retry:
                        from email.utils import parsedate_to_datetime

                        try:
                            wait = max(
                                wait,
                                parsedate_to_datetime(retry).timestamp() - time.time(),
                            )
                        except (ValueError, TypeError):
                            pass
                if wait > 60:
                    raise ReadError("rate_limit_deferred")
                await asyncio.sleep(wait)
            if urlsplit(url).path == '/robots.txt':
                origin = 'https://' + urlsplit(url).netloc
                self.robots_diagnostics.setdefault(origin, {})['http_status'] = response.status_code
            else:
                self.page_access[domain] = {'http_status': response.status_code,
                    'transport': 'chromium' if self.uses_browser(domain) else 'http'}
            if response.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, response.headers.get("location", ""))
                continue
            if response.status_code in (403, 401):
                self.pause_access(domain)
                if any(
                    m in response.text.lower()
                    for m in (
                        "cf-chl-",
                        "g-recaptcha",
                        "hcaptcha",
                        "verify you are human",
                    )
                ):
                    raise ReadError("captcha_no_bypass")
                raise ReadError("blocked_no_bypass")
            if response.status_code in (404, 410):
                raise ReadError("page_removed")
            if response.status_code != 200:
                raise ReadError("http_error")
            if len(response.content) > 8_000_000:
                raise ReadError("page_too_large")
            url, final_domain = self.canonical(str(response.url))
            if final_domain != domain:
                raise ReadError("redirect_changed_store")
            self.content_types[url] = response.headers.get("content-type", "text/html")
            return response.text, url
        raise ReadError("too_many_redirects")

    async def allowed_by_robots(self, url):
        origin = "https://" + urlsplit(url).netloc
        if origin not in self.robots or self.robots[origin][0] < time.time() - 86400:
            self.robots_diagnostics[origin] = {'http_status': None}
            # Na duvida, recusar. 404 de robots significa ausencia de regras.
            try:
                text, _ = await self.request(origin + "/robots.txt")
            except ReadError as exc:
                if str(exc) == "page_removed":
                    text = ""
                else:
                    self.robots_diagnostics[origin]['reason'] = str(exc)
                    raise ReadError("robots_unavailable") from None
            parser = RobotsPolicy(text)
            self.robots[origin] = (time.time(), parser)
            self.robots_diagnostics[origin]['reason'] = 'rules_loaded'
        parser = self.robots[origin][1]
        delay = parser.crawl_delay("PriceMonitor") or parser.crawl_delay("*")
        if delay:
            self.config.delay = max(self.config.delay, delay)
        if not parser.can_fetch("PriceMonitor", url):
            raise ReadError("robots_disallowed")

    async def html(self, url, *, isolated=False):
        url, domain = self.canonical(url)
        audit = PAGE_AUDIT.get()
        entry = {'domain': domain, 'url': url, 'ok': False}
        if audit is not None:
            audit.append(entry)
        await self.allowed_by_robots(url)
        if isolated:
            async with httpx.AsyncClient(timeout=30, follow_redirects=False,
                    headers={'User-Agent': 'PriceMonitor/1.0 (+personal price monitoring)'}) as client:
                text, final = await self.request(url, check_robots=True, client=client)
        else:
            text, final = await self.request(url, check_robots=True)
        if final != url:
            await self.allowed_by_robots(final)
        if is_access_challenge(text):
            self.pause_access(domain)
            raise ReadError("captcha_no_bypass")
        entry['ok'] = True
        return text, final

    async def render(self, url):
        url, domain = self.canonical(url)
        await self.allowed_by_robots(url)
        lock = self.locks.setdefault(domain, asyncio.Lock())
        async with lock:
            await asyncio.sleep(
                max(0, self.last.get(domain, 0) + self.config.delay - time.monotonic())
            )
            try:
                response = await self.chromium().get(url, render=True)
            finally:
                self.last[domain] = time.monotonic()
        if response.status_code != 200:
            raise ReadError("browser_http_error")
        return response.text

    async def close(self):
        if self.browser_transport is not None:
            await self.browser_transport.close()
        await self.client.aclose()
