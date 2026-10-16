"""Importações isoladas evitam que a ordem da suíte esconda dependências circulares."""
import subprocess
import sys
import pytest


@pytest.mark.parametrize('module', [
    'monitor.discovery', 'monitor.external_market_search',
    'monitor.adapters.mercadolivre', 'monitor.deals.catalog',
    'scripts.diagnose_offers',
])
def test_module_imports_in_fresh_process(module):
    result = subprocess.run([sys.executable, '-c',
        'import importlib, sys; importlib.import_module(sys.argv[1])', module],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
