"""Guard against committing local credentials/data; never print matched secrets."""
from pathlib import Path
import re
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=root
    ).decode('utf-8').split('\0')
    errors = []
    token = re.compile(rb'\b\d{8,12}:[A-Za-z0-9_-]{30,50}\b')
    for name in filter(None, names):
        path = Path(name)
        private = (
            (path.name.startswith('.env') and path.name != '.env.example')
            or path.parts[0] in {'data', 'backups', '.venv', 'venv', 'monitor-precos-kali'}
            or path.suffix in {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.zip', '.gz'}
        )
        if private:
            errors.append(f'{name}: arquivo privado ou gerado')
        full = root / path
        if full.is_file():
            content = full.read_bytes()
            if token.search(content) or re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', content):
                errors.append(f'{name}: possivel credencial; conteudo omitido')
    if errors:
        print('\n'.join(errors))
        return 1
    print('Arquivos rastreados verificados: nenhuma credencial ou dado local detectado pelos filtros.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
