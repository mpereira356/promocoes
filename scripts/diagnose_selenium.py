"""Teste isolado de Selenium comum; sem login, stealth ou interacao com desafios."""
import argparse
import json
import os
import time
from urllib.parse import urlsplit
from pathlib import Path
from monitor.robots import RobotsPolicy
from monitor.challenges import is_access_challenge

HOSTS = {'www.mercadolivre.com.br', 'mercadolivre.com.br',
         'produto.mercadolivre.com.br', 'lista.mercadolivre.com.br'}


def validate_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.port not in (None, 443) or p.username or p.password:
        raise ValueError('Use um link HTTPS do Mercado Livre sem credenciais.')
    return p


def main_response(entries, url):
    """Extrair apenas status e Content-Type; nunca imprimir o log de rede bruto."""
    result = {'http_status': None, 'content_type': ''}
    for entry in entries:
        try:
            msg = json.loads(entry['message'])['message']
            params = msg.get('params', {})
            response = params.get('response', {})
            if msg.get('method') == 'Network.responseReceived' and params.get('type') == 'Document' and response.get('url') == url:
                result = {'http_status': int(response['status']),
                          'content_type': str(response.get('mimeType', ''))}
        except (KeyError, ValueError, TypeError):
            continue
    return result


def diagnose(url, headed=False, binary=None, driver_path=None):
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    p = validate_url(url)
    os.environ.setdefault('SE_CACHE_PATH', str(Path('data/selenium').resolve()))
    os.environ.setdefault('SE_AVOID_STATS', 'true')
    options = webdriver.ChromeOptions()
    if not headed:
        options.add_argument('--headless=new')
    if binary:
        options.binary_location = binary
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    driver = None
    report = {'engine': 'Selenium / Chrome', 'mode': 'headed' if headed else 'headless',
              'price_verified': False, 'product_page_requested': False}
    try:
        driver = webdriver.Chrome(service=Service(driver_path) if driver_path else Service(), options=options)
        driver.set_page_load_timeout(40)
        origin = 'https://' + p.netloc
        driver.get(origin + '/robots.txt')
        validate_url(driver.current_url)
        info = main_response(driver.get_log('performance'), driver.current_url)
        report['robots'] = info
        if info['http_status'] == 404:
            policy = RobotsPolicy('')
        elif info['http_status'] == 200 and info['content_type'].startswith('text/plain'):
            policy = RobotsPolicy(driver.find_element(By.TAG_NAME, 'body').text)
        else:
            report['result'] = 'robots_unavailable; pagina do produto nao solicitada'
            return report
        if not policy.can_fetch('PriceMonitor', url):
            report['result'] = 'robots_disallowed; pagina do produto nao solicitada'
            return report
        report['product_page_requested'] = True
        time.sleep(max(3, policy.crawl_delay('PriceMonitor') or policy.crawl_delay('*') or 0))
        driver.get(url)
        validate_url(driver.current_url)
        report['page'] = main_response(driver.get_log('performance'), driver.current_url)
        if report['page']['http_status'] != 200:
            report['result'] = 'product_page_http_error'
        elif is_access_challenge(driver.page_source):
            report['result'] = 'captcha_or_challenge; nenhuma interacao realizada'
        else:
            from monitor.adapters.mercadolivre import MercadoLivreAdapter
            try:
                readings = MercadoLivreAdapter().parse(driver.page_source, driver.current_url)
                report['readings'] = [vars(r) | {'comparable': r.comparable} for r in readings]
                report['price_verified'] = any(r.comparable for r in readings)
                report['result'] = 'page_read'
            except Exception:
                report['result'] = 'page_accessible_but_offer_not_validated'
        return report
    except Exception as exc:
        report['result'] = 'selenium_error_' + type(exc).__name__
        return report
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='https://www.mercadolivre.com.br/placa-mae-gigabyte-b550-aorus-elite-v2-12-ddr4-am4-atx/p/MLB22450130')
    parser.add_argument('--headed', action='store_true', help='Janela visivel; exige ambiente grafico.')
    parser.add_argument('--binary', help='Caminho local do Chrome/Chromium.')
    parser.add_argument('--driver', help='Caminho local do chromedriver, opcional.')
    args = parser.parse_args()
    try:
        report = diagnose(args.url, args.headed, args.binary, args.driver)
    except (ValueError, ImportError):
        report = {'result': 'configuracao invalida ou Selenium nao instalado', 'price_verified': False}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
