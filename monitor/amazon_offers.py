"""Selenium normal para o painel publico de ofertas Amazon; nenhum botao de compra e acionado."""
import asyncio
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit
from .adapters.base import ReadError
from .challenges import is_access_challenge


class AmazonOffersReader:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.lock = asyncio.Lock()

    async def html(self, url):
        url, domain = self.fetcher.canonical(url)
        if domain != 'amazon.com.br':
            raise ReadError('url_not_allowed')
        await self.fetcher.allowed_by_robots(url)
        await self.fetcher.public(url)
        origin = 'https://' + urlsplit(url).netloc
        policy = self.fetcher.robots[origin][1]
        async with self.lock:
            async with self.fetcher.locks.setdefault(domain, asyncio.Lock()):
                await asyncio.sleep(max(0, self.fetcher.last.get(domain, 0) + self.fetcher.config.delay - time.monotonic()))
                worker = asyncio.create_task(asyncio.to_thread(self._load, url, policy))
                try:
                    return await asyncio.shield(worker)
                except asyncio.CancelledError:
                    await worker
                    raise
                finally:
                    self.fetcher.last[domain] = time.monotonic()

    def _load(self, url, policy):
        driver = None
        phase = 'amazon_browser_start_failed'
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.support.ui import WebDriverWait
            from scripts.diagnose_selenium import main_response
            os.environ.setdefault('SE_CACHE_PATH', str(Path('data/selenium').resolve()))
            os.environ.setdefault('SE_AVOID_STATS', 'true')
            options = webdriver.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            if os.name == 'posix':
                # /dev/shm é pequeno em muitas VPS; usa arquivos temporários comuns.
                options.add_argument('--disable-dev-shm-usage')
            binary = shutil.which('chromium') or shutil.which('chromium-browser')
            if binary:
                options.binary_location = binary
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            driver_path = shutil.which('chromedriver')
            service = Service(driver_path, log_output=subprocess.DEVNULL) if driver_path else Service(log_output=subprocess.DEVNULL)
            driver = webdriver.Chrome(service=service, options=options)
            phase = 'amazon_browser_navigation_failed'
            driver.set_page_load_timeout(40)
            driver.get(url)
            final, domain = self.fetcher.canonical(driver.current_url)
            if domain != 'amazon.com.br' or not policy.can_fetch('PriceMonitor', final):
                raise ReadError('robots_disallowed')
            expected = re.search(r'/(?:gp/offer-listing|dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(url).path)
            actual = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$)', urlsplit(final).path)
            if not expected or not actual or expected[1] != actual[1]:
                raise ReadError('different_model')
            response = main_response(driver.get_log('performance'), driver.current_url)
            if response['http_status'] != 200:
                raise ReadError('amazon_offers_http_error')
            def ready(d):
                if is_access_challenge(d.page_source):
                    raise ReadError('captcha_no_bypass')
                return bool(d.find_elements('css selector', '#aod-offer-list #aod-offer'))
            phase = 'amazon_offers_panel_timeout'
            WebDriverWait(driver, 20).until(ready)
            return driver.page_source
        except ReadError:
            raise
        except ImportError:
            raise ReadError('selenium_not_installed') from None
        except Exception as exc:
            raise ReadError(browser_error(exc, phase)) from None
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass


def browser_error(exc, phase):
    """Classifica sem expor mensagem, URL, cookies ou configuração do navegador."""
    text = str(exc).lower()
    if 'tab crashed' in text or 'chrome not reachable' in text or 'disconnected' in text:
        return 'amazon_browser_crashed'
    if re.search(r'net::err_(?:connection|name_not_resolved|proxy|tunnel|timed_out)', text):
        return 'amazon_browser_connection_failed'
    return phase
