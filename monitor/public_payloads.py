"""Decode the public router's serialized JSON graph, without evaluating JavaScript."""
import json
import re
from bs4 import BeautifulSoup
from .adapters.base import ReadError


def router_data(html):
    for script in BeautifulSoup(html, 'html.parser').select('script'):
        text = script.get_text()
        match = re.search(r'\.enqueue\(', text)
        if not match:
            continue
        try:
            serialized, _ = json.JSONDecoder().raw_decode(text[match.end():].lstrip())
            graph = json.loads(serialized)
            if not isinstance(graph, list) or not graph or len(graph) > 20000:
                continue
            cache = {}

            def decode(index, depth=0):
                if type(index) is not int or index < 0:
                    return None
                if index >= len(graph) or depth > 80:
                    raise ValueError('invalid graph reference')
                if index in cache:
                    return cache[index]
                value = graph[index]
                cache[index] = None
                if isinstance(value, dict):
                    result = {}
                    for key, ref in value.items():
                        if not re.fullmatch(r'_[0-9]+', key):
                            raise ValueError('invalid graph key')
                        decoded_key = decode(int(key[1:]), depth + 1)
                        if not isinstance(decoded_key, str):
                            raise ValueError('invalid graph key')
                        result[decoded_key] = decode(ref, depth + 1)
                elif isinstance(value, list):
                    if len(value) == 2 and value[0] == 'SingleFetchClassInstance':
                        result = decode(value[1], depth + 1)
                    else:
                        result = [decode(ref, depth + 1) if type(ref) is int else ref for ref in value]
                else:
                    result = value
                cache[index] = result
                return result

            result = decode(0)
            if isinstance(result, dict) and isinstance(result.get('loaderData'), dict):
                return result['loaderData']
        except (ValueError, TypeError, RecursionError):
            continue
    raise ReadError('regional_response_invalid')
