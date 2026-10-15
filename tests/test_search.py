from types import SimpleNamespace
import asyncio
from unittest.mock import patch
import pytest
from monitor.search import Search, search_error_message
from monitor.adapters.base import ReadError


@pytest.mark.parametrize(
    "provider,key,expected",
    [
        ("brave", "", "search_not_configured"),
        ("brave", "   ", "search_not_configured"),
        ("disabled", "", "search_disabled"),
        ("other", "key", "search_provider_invalid"),
        ("brave", "key", None),
    ],
)
def test_search_configuration_diagnosis(provider, key, expected):
    search = Search(SimpleNamespace(provider=provider, key=key), None)
    assert search.configuration_error() == expected


def test_missing_key_never_requests_network():
    search = Search(SimpleNamespace(provider="brave", key=""), None)
    with patch("monitor.search.httpx.AsyncClient") as client:
        with pytest.raises(ReadError, match="search_not_configured"):
            asyncio.run(search.links("placa mae"))
        client.assert_not_called()
    message = search_error_message("search_not_configured")
    assert "SEARCH_API_KEY" in message and "reinicie" in message
