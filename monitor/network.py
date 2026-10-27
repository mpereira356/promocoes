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
        self.rate_paused = {}
        self.page_access = {}
        self.grocery_prices = None
        from .network_state import BackoffState
        self.backoff = BackoffState(config)
        self.access_paused.update(self.backoff.restore('access'))
        self.rate_paused.update(self.backoff.restore('rate'))

    def pause_access(self, domain):
        self.access_paused[domain] = time.monotonic() + 900
        self.backoff.pause('access', domain, 900)

    def pause_rate(self, domain, seconds):
        self.rate_paused[domain] = time.monotonic() + seconds
        self.backoff.pause('rate', domain, seconds)

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
        mobile_magalu = host == 'm.magazineluiza.com.br'
        if mobile_magalu:
            domain = 'magazineluiza.com.br'
        if (
            p.scheme != "https"
            or p.username
            or p.password
            or p.port not in (None, 443)
            or domain not in self.config.domains
            or (host not in (domain, "www." + domain) and not marketplace_host and not mobile_magalu)
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

    async def request(self, url, check_robots=False, client=None, *, public_post=None, fresh=False):
        if public_post is not None:
            # Only observed anonymous regional selection / isolated simulation.
            # No endpoint for adding items, ordering, paying or customer accounts.
            _, post_domain = self.canonical(url)
            path = urlsplit(url).path
            allowed = (
                post_domain == 'atacadao.com.br' and path == '/api/checkout/pub/orderForms/simulation'
                or post_domain == 'mercado.carrefour.com.br' and path == '/action/set-regionalization'
                or post_domain == 'boasupermercados.com.br' and path == '/api/graphql'
                and public_post.get('operationName') == 'ValidateSession'
                or post_domain == 'api.vendas.gpa.digital' and path == '/ex/search/search')
            if not allowed or self.uses_browser(post_domain):
                raise ReadError('regional_request_not_allowed')
            check_robots = True
        for redirect in range(5):
            url, domain = self.canonical(url)
            if self.access_paused.get(domain, 0) > time.monotonic():
                raise ReadError('domain_access_cooldown')
            if self.rate_paused.get(domain, 0) > time.monotonic():
                raise ReadError('store_rate_cooldown')
            if check_robots:
                await self.allowed_by_robots(url)
            await self.public(url)
            lock = self.locks.setdefault(domain, asyncio.Lock())
            attempts = []
            retry_reason = 'network_connection_failure'
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
                    response = None
                    error_type = None
                    try:
                        if self.uses_browser(domain):
                            response = await self.chromium().get(url)
                        else:
                            if public_post is None:
                                if fresh:
                                    response = await (client or self.client).get(url, headers={'Cache-Control': 'no-cache'})
                                else:
                                    response = await (client or self.client).get(url)
                            elif domain == 'mercado.carrefour.com.br':
                                response = await (client or self.client).post(url, data=public_post)
                            else:
                                response = await (client or self.client).post(url, json=public_post)
                    except ReadError as exc:
                        error_type = type(exc).__name__
                        retry_reason = ('network_timeout' if str(exc) == 'browser_navigation_failed_TimeoutError'
                                        else 'network_connection_failure')
                        if str(exc) in ('blocked_no_bypass', 'captcha_no_bypass'):
                            self.pause_access(domain)
                        if str(exc) not in (
                            "browser_navigation_failed_TimeoutError",
                            "browser_connection_failed",
                        ):
                            raise
                        response = None
                    except httpx.RequestError as exc:
                        error_type = type(exc).__name__
                        retry_reason = 'network_timeout' if isinstance(exc, httpx.TimeoutException) else 'network_connection_failure'
                        response = None
                    finally:
                        self.last[domain] = time.monotonic()
                        attempts.append({'attempt': attempt + 1,
                                         'http_status': response.status_code if response is not None else None,
                                         'error_type': error_type})
                        if urlsplit(url).path != '/robots.txt':
                            self.page_access[domain] = {
                                'http_status': attempts[-1]['http_status'],
                                'transport': 'chromium' if self.uses_browser(domain) else 'http',
                                'attempts': list(attempts),
                            }
                if response is not None and response.status_code not in (
                    429,
                    500,
                    502,
                    503,
                    504,
                ):
                    break
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
                    if response is not None and response.status_code == 429:
                        self.pause_rate(domain, wait)
                    raise ReadError('rate_limit_deferred' if response is not None and response.status_code == 429
                                    else 'store_retry_deferred')
                if attempt == 2:
                    if response is not None:
                        retry_reason = ('rate_limit_deferred' if response.status_code == 429
                                        else 'store_temporarily_unavailable')
                        if response.status_code == 429:
                            self.pause_rate(domain, max(60, wait))
                    raise ReadError(retry_reason)
                await asyncio.sleep(wait)
            if urlsplit(url).path == '/robots.txt':
                origin = 'https://' + urlsplit(url).netloc
                self.robots_diagnostics.setdefault(origin, {})['http_status'] = response.status_code
            else:
                self.page_access[domain].update(http_status=response.status_code)
            if response.status_code in (301, 302, 303, 307, 308):
                if public_post is not None:
                    raise ReadError('regional_selection_redirect')
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
        if self.grocery_prices is not None:
            await self.grocery_prices.close()
        if self.browser_transport is not None:
            await self.browser_transport.close()
        await self.client.aclose()
