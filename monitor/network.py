import asyncio
import ipaddress
import socket
import time
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qsl, urlencode
from .robots import RobotsPolicy
import httpx
from .adapters.base import ReadError
from .challenges import is_access_challenge


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
        self.content_types = {}
        self.browser_transport = None

    def uses_browser(self, domain):
        return getattr(self.config, "browser", False) and domain in (
            "pichau.com.br",
            "terabyteshop.com.br",
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
        if (
            p.scheme != "https"
            or p.username
            or p.password
            or p.port not in (None, 443)
            or domain not in self.config.domains
            or host not in (domain, "www." + domain)
        ):
            raise ReadError("url_not_allowed")
        query = urlencode(
            [
                (k, v)
                for k, v in parse_qsl(p.query, keep_blank_values=True)
                if not k.lower().startswith("utm_")
                and k.lower() not in ("msockid", "gclid", "fbclid")
            ]
        )
        return urlunsplit(("https", host, p.path or "/", query, "")), domain

    async def public(self, url):
        host = urlsplit(url).hostname
        infos = await asyncio.get_running_loop().getaddrinfo(
            host, 443, type=socket.SOCK_STREAM
        )
        if not infos or any(not ipaddress.ip_address(i[4][0]).is_global for i in infos):
            raise ReadError("non_public_address")

    async def request(self, url, check_robots=False):
        for redirect in range(5):
            url, domain = self.canonical(url)
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
                            response = await self.client.get(url)
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
            if response.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, response.headers.get("location", ""))
                continue
            if response.status_code in (403, 401):
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
            # Na duvida, recusar. 404 de robots significa ausencia de regras.
            try:
                text, _ = await self.request(origin + "/robots.txt")
            except ReadError as exc:
                if str(exc) == "page_removed":
                    text = ""
                else:
                    raise ReadError("robots_unavailable") from None
            parser = RobotsPolicy(text)
            self.robots[origin] = (time.time(), parser)
        parser = self.robots[origin][1]
        delay = parser.crawl_delay("PriceMonitor") or parser.crawl_delay("*")
        if delay:
            self.config.delay = max(self.config.delay, delay)
        if not parser.can_fetch("PriceMonitor", url):
            raise ReadError("robots_disallowed")

    async def html(self, url):
        url, _ = self.canonical(url)
        await self.allowed_by_robots(url)
        text, final = await self.request(url, check_robots=True)
        if final != url:
            await self.allowed_by_robots(final)
        if is_access_challenge(text):
            raise ReadError("captcha_no_bypass")
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
