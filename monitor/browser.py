"""Transporte Chromium comum para paginas publicas permitidas; sem stealth/proxy/CAPTCHA."""

import asyncio
from urllib.parse import urlsplit
import httpx
from .adapters.base import ReadError
from .challenges import is_access_challenge

USER_AGENT = "PriceMonitor/1.0 (+personal price monitoring)"
CAPTCHA_MARKERS = ("cf-chl-", "g-recaptcha", "hcaptcha", "verify you are human")


class ChromiumTransport:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.lock = asyncio.Lock()
        self.engine = None
        self.browser = None

    async def start(self):
        if self.browser is not None:
            return
        try:
            from playwright.async_api import async_playwright

            self.engine = await async_playwright().start()
            self.browser = await self.engine.chromium.launch(headless=True)
        except Exception:
            if self.engine:
                await self.engine.stop()
                self.engine = None
            raise ReadError("browser_not_installed") from None

    async def get(self, url, render=False):
        async with self.lock:
            await self.start()
            _, domain = self.fetcher.canonical(url)
            context = await self.browser.new_context(
                user_agent=USER_AGENT,
                java_script_enabled=render,
                service_workers="block",
                accept_downloads=False,
            )
            failure = []
            assets = 0
            asset_lock = asyncio.Lock()

            async def route(r):
                nonlocal assets
                req = r.request
                try:
                    _, target = self.fetcher.canonical(req.url)
                    if target != domain or req.method not in ("GET", "HEAD"):
                        return await r.abort()
                    path = urlsplit(req.url).path.lower()
                    if any(
                        marker in path for marker in ("captcha", "challenge-platform")
                    ):
                        failure.append("captcha_no_bypass")
                        return await r.abort()
                    if req.resource_type not in ("document", "script", "xhr", "fetch"):
                        return await r.abort()
                    if (
                        req.resource_type == "document"
                        and req.frame.parent_frame is not None
                    ):
                        return await r.abort()
                    await self.fetcher.public(req.url)
                    if path != "/robots.txt":
                        origin = "https://" + urlsplit(req.url).netloc
                        cached = self.fetcher.robots.get(origin)
                        if not cached or not cached[1].can_fetch(
                            "PriceMonitor", req.url
                        ):
                            failure.append("robots_disallowed")
                            return await r.abort()
                    if req.resource_type != "document":
                        assets += 1
                        if assets > 12:
                            return await r.abort()
                        async with asset_lock:
                            await asyncio.sleep(self.fetcher.config.delay)
                            await r.continue_()
                    else:
                        await r.continue_()
                except Exception as exc:
                    # Falha de recurso opcional não pode esconder o motivo da navegação.
                    if req.resource_type == 'document' and req.frame.parent_frame is None:
                        failure.append(str(exc) if isinstance(exc, ReadError) else
                            'browser_connection_failed' if isinstance(exc, OSError) else 'browser_resource_refused')
                    await r.abort()

            try:
                await context.route("**/*", route)
                page = await context.new_page()
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=45000
                )
                if response is None:
                    raise ReadError("browser_empty_response")
                raw = await response.text()
                if is_access_challenge(raw):
                    raise ReadError("captcha_no_bypass")
                if render and response.status == 200:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    raw = await page.content()
                if failure:
                    # Recursos opcionais fora do dominio sao simplesmente descartados;
                    # uma restricao de robots/CAPTCHA nao e ignorada.
                    if "captcha_no_bypass" in failure and is_access_challenge(raw):
                        raise ReadError("captcha_no_bypass")
                return httpx.Response(
                    response.status,
                    headers=httpx.Headers({
                        k: v
                        for k, v in (await response.all_headers()).items()
                        if k.lower()
                        not in (
                            "content-encoding",
                            "content-length",
                            "transfer-encoding",
                        )
                    }, encoding='utf-8'),
                    text=raw,
                    request=httpx.Request("GET", response.url),
                )
            except ReadError:
                raise
            except Exception as exc:
                connection_error = any(
                    marker in str(exc)
                    for marker in (
                        "net::ERR_CONNECTION_RESET", "net::ERR_CONNECTION_CLOSED",
                        "net::ERR_CONNECTION_TIMED_OUT", "net::ERR_TIMED_OUT",
                    )
                )
                raise ReadError(
                    failure[0]
                    if failure
                    else "browser_connection_failed" if connection_error
                    else "browser_navigation_failed_" + type(exc).__name__
                ) from None
            finally:
                await context.close()

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.engine:
            await self.engine.stop()
            self.engine = None
