import json
import pytest
from scripts.diagnose_selenium import validate_url, main_response


@pytest.mark.parametrize('url', ['http://www.mercadolivre.com.br/', 'https://localhost/', 'https://www.mercadolivre.com.br.evil.org/', 'https://user:password@www.mercadolivre.com.br/'])
def test_diagnostic_rejects_untrusted_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_network_log_extracts_only_main_document_status():
    def entry(kind, url, status):
        return {'message': json.dumps({'message': {'method': 'Network.responseReceived', 'params': {'type': kind, 'response': {'url': url, 'status': status, 'mimeType': 'text/html', 'headers': {'secret': 'not-for-report'}}}}})}
    url = 'https://www.mercadolivre.com.br/robots.txt'
    result = main_response([entry('Document', url, 403), entry('Stylesheet', 'https://example.org/style.css', 200)], url)
    assert result == {'http_status': 403, 'content_type': 'text/html'}
    assert 'secret' not in str(result)
