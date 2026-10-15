#!/usr/bin/env bash
# Instala o projeto local em Kali/Debian com systemd. Sem credenciais embutidas.
set +x
set -Eeuo pipefail
umask 077

fail() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }
trap 'printf "Instalacao interrompida. O servico nao foi confirmado como pronto.\n" >&2' ERR

[[ ${EUID} -eq 0 ]] || fail 'Execute com sudo bash deploy/install-kali.sh'
command -v apt-get >/dev/null || fail 'Este instalador requer Kali/Debian com apt-get.'
[[ -d /run/systemd/system ]] || fail 'systemd nao esta ativo. Consulte LEIA-ME-KALI.md para execucao manual.'

source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
install_dir='/opt/price-monitor'
restore_file=''
with_browser=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-browser) with_browser=1; shift ;;
        --restore) [[ $# -ge 2 ]] || fail 'Informe o caminho do backup.'; restore_file="$(realpath -e -- "$2")"; shift 2 ;;
        *) fail 'Uso: install-kali.sh [--with-browser] [--restore /caminho/backup.sqlite3]' ;;
    esac
done
if [[ -n "$restore_file" ]]; then
    [[ -f "$restore_file" ]] || fail 'Backup nao encontrado.'
    [[ ! -e "$install_dir/data/monitor.sqlite3" ]] || fail 'Ja existe banco no servidor. A restauracao automatica so e permitida em instalacao nova.'
fi
for required in monitor/__main__.py requirements-server.txt .env.example deploy/price-monitor.service; do
    [[ -f "$source_dir/$required" ]] || fail "Arquivo ausente no pacote: $required"
done

printf 'Instalando dependencias do sistema e ambiente Python isolado...\n'
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip ca-certificates tzdata nano
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' || fail 'Python 3.11 ou mais recente e necessario.'
getent group pricebot >/dev/null || groupadd --system pricebot
if ! id pricebot >/dev/null 2>&1; then
    useradd --system --gid pricebot --home-dir "$install_dir" --shell /usr/sbin/nologin pricebot
fi
[[ "$(id -u pricebot)" != '0' ]] || fail 'A conta pricebot existente nao pode ser root.'
[[ "$(id -gn pricebot)" == 'pricebot' ]] || fail 'A conta pricebot existente tem outro grupo primario; revise antes de instalar.'
install -d -m 0750 -o root -g pricebot "$install_dir"
install -d -m 0750 -o pricebot -g pricebot "$install_dir/data"

# Perguntar antes de interromper uma instalacao anterior.
if [[ ! -f "$install_dir/.env" ]]; then
    [[ -r /dev/tty ]] || fail 'Abra uma sessao SSH interativa para preencher a configuracao.'
    printf '\nConfiguracao inicial. O token nao sera mostrado.\n'
    read -r -s -p 'Token do bot Telegram: ' telegram_token </dev/tty
    printf '\n'
    [[ "$telegram_token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]] || fail 'Formato de token invalido.'
    read -r -p 'ID numerico do grupo Telegram: ' telegram_chat </dev/tty
    [[ "$telegram_chat" =~ ^-?[0-9]+$ ]] || fail 'ID do grupo invalido.'
    read -r -p 'Seu ID pessoal numerico (positivo): ' telegram_user </dev/tty
    [[ "$telegram_user" =~ ^[1-9][0-9]*$ ]] || fail 'Informe seu ID pessoal positivo, nao o ID do grupo.'
    {
        printf 'TELEGRAM_BOT_TOKEN=%s\n' "$telegram_token"
        printf 'TELEGRAM_CHAT_ID=%s\n' "$telegram_chat"
        printf 'TELEGRAM_USER_ID=%s\n' "$telegram_user"
        printf 'SEARCH_PROVIDER=direct\nSEARCH_API_KEY=\n'
        printf 'ALLOWED_DOMAINS=kabum.com.br,pichau.com.br,terabyteshop.com.br\n'
        printf 'DATABASE_PATH=data/monitor.sqlite3\nINTERVAL_HOURS=5\nREQUEST_DELAY=3\n'
        printf 'MIN_DROP_BRL=0\nMIN_DROP_PERCENT=0\nTARGET_PRICE=\nPLAYWRIGHT_ENABLED=false\n'
    } > "$install_dir/.env"
    unset telegram_token telegram_chat telegram_user
fi
chown root:pricebot "$install_dir/.env"
chmod 0640 "$install_dir/.env"

if [[ -n "$restore_file" ]]; then
    grep -Eq '^DATABASE_PATH=(data/monitor\.sqlite3|/opt/price-monitor/data/monitor\.sqlite3)$' "$install_dir/.env" || fail 'Para restauracao inicial, use DATABASE_PATH=data/monitor.sqlite3 no .env do servidor.'
    python3 - "$restore_file" <<'PY'
import sqlite3,sys
from pathlib import Path
source=Path(sys.argv[1]).resolve()
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as db:
    if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
        raise SystemExit('Backup SQLite invalido.')
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'products','candidates','checks'} <= tables:
        raise SystemExit('Arquivo nao corresponde ao banco deste projeto.')
PY
    install -m 0600 -o pricebot -g pricebot "$restore_file" "$install_dir/data/monitor.sqlite3"
fi

if systemctl is-active --quiet price-monitor; then
    systemctl stop price-monitor
fi
# Lista explicita: nunca sobrescrever .env, data ou copiar .venv do Windows.
if [[ "$source_dir" != "$install_dir" ]]; then
    for folder in monitor deploy scripts; do
        cp -R -- "$source_dir/$folder" "$install_dir/"
        chown -R root:pricebot "$install_dir/$folder"
        find "$install_dir/$folder" -type d -exec chmod 0750 {} +
        find "$install_dir/$folder" -type f -exec chmod 0640 {} +
    done
    for filename in requirements-server.txt requirements-browser.txt .env.example README.md LEIA-ME-KALI.md VALIDACAO.md; do
        install -m 0640 -o root -g pricebot "$source_dir/$filename" "$install_dir/$filename"
    done
fi
if [[ ! -x "$install_dir/.venv/bin/python" ]]; then
    python3 -m venv "$install_dir/.venv"
fi
"$install_dir/.venv/bin/python" -m pip install --disable-pip-version-check -r "$install_dir/requirements-server.txt"
if [[ $with_browser -eq 1 ]]; then
    # Chromium do Kali/Debian fornece as bibliotecas nativas; o Playwright usa seu binario compativel.
    DEBIAN_FRONTEND=noninteractive apt-get install -y chromium
    "$install_dir/.venv/bin/python" -m pip install --disable-pip-version-check -r "$install_dir/requirements-browser.txt"
    chown -R root:pricebot "$install_dir/.venv"
    chmod -R g+rX,o-rwx "$install_dir/.venv"
    install -d -m 0750 -o pricebot -g pricebot "$install_dir/data/browsers"
    runuser -u pricebot -- env PLAYWRIGHT_BROWSERS_PATH="$install_dir/data/browsers" \
        "$install_dir/.venv/bin/python" -m playwright install chromium
    "$install_dir/.venv/bin/python" - <<'PY'
from pathlib import Path
p=Path('/opt/price-monitor/.env')
lines=p.read_text(encoding='utf-8-sig').splitlines()
settings={'PLAYWRIGHT_ENABLED':'true',
          'PLAYWRIGHT_BROWSERS_PATH':'/opt/price-monitor/data/browsers',
          'XDG_CACHE_HOME':'/opt/price-monitor/data/browser-cache',
          'XDG_CONFIG_HOME':'/opt/price-monitor/data/browser-config'}
for key,value in settings.items():
    lines=[line for line in lines if not line.startswith(key+'=')]
    lines.append(key+'='+value)
p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
PY
    runuser -u pricebot -- env PLAYWRIGHT_BROWSERS_PATH="$install_dir/data/browsers" \
        "$install_dir/.venv/bin/python" - <<'PY'
import asyncio
from playwright.async_api import async_playwright
async def check():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        print('Chromium iniciou como usuario do servico: '+browser.version)
        await browser.close()
asyncio.run(check())
PY
fi
chown -R root:pricebot "$install_dir/.venv"
chmod -R g+rX,o-rwx "$install_dir/.venv"

# Validar configuracao e pasta gravavel sem imprimir valores sensiveis e sem conectar ao bot.
cd -- "$install_dir"
runuser -u pricebot -- "$install_dir/.venv/bin/python" - <<'PY'
from pathlib import Path
from monitor.config import Config
from monitor.version import VERSION
import os
try:
    c=Config.load()
    path=Path(c.db).resolve()
    if not path.is_relative_to(Path('data').resolve()):
        raise ValueError()
    if not c.token.strip() or not os.access('data',os.W_OK):
        raise ValueError()
except Exception:
    raise SystemExit('Configuracao invalida: confira token, IDs e DATABASE_PATH dentro de data no arquivo /opt/price-monitor/.env.') from None
print('Configuracao local validada; autenticacao Telegram sera feita ao iniciar o servico.')
print('Versao instalada: '+VERSION)
PY
install -m 0644 "$install_dir/deploy/price-monitor.service" /etc/systemd/system/price-monitor.service
systemctl daemon-reload
systemctl enable --now price-monitor
sleep 2
if ! systemctl is-active --quiet price-monitor; then
    fail 'O servico nao ficou ativo. Consulte sudo journalctl -u price-monitor -n 50 --no-pager'
fi
printf '\nServico ativo no systemd. Confirme no Telegram com /ajuda.\n'
printf 'Pode desconectar do SSH. Ele inicia novamente apos reiniciar o servidor.\n'
printf 'Status: sudo systemctl status price-monitor\n'
printf 'Logs: sudo journalctl -u price-monitor -f\n'
printf 'Editar configuracao: sudo nano /opt/price-monitor/.env\n'
printf 'Reiniciar: sudo systemctl restart price-monitor\n'
printf 'Nao execute o mesmo bot no Windows e no servidor simultaneamente.\n'
