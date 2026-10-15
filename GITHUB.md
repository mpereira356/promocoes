# Publicar e atualizar pelo GitHub

O `.env`, banco de dados, caches e pacotes gerados sao privados e ignorados pelo Git. Nunca use `git add -f` nesses arquivos. A verificacao automatica de credenciais e limitada; revise os arquivos antes de publicar.

## Publicar a partir do Windows

Crie no GitHub um repositorio vazio, sem README ou gitignore, de preferencia privado. No PowerShell desta pasta:

```powershell
git add .
python scripts/check_repository.py
git diff --cached --stat
git commit -m "Projeto de monitoramento de precos"
git remote add origin https://github.com/mpereira356/promocoes.git
git push -u origin main
```

Se o Git solicitar identidade, configure `git config user.name "Seu nome"` e `git config user.email "Seu email"` e repita o commit. Autentique pelo mecanismo do GitHub; nao coloque tokens no codigo ou na URL do repositorio.

## Primeira instalacao no Kali/Debian

Clone em uma pasta separada da instalacao em `/opt/price-monitor`:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/mpereira356/promocoes.git ~/monitor-precos-src
cd ~/monitor-precos-src
sudo bash deploy/install-kali.sh --with-browser
```

Em repositorio privado, autentique com sua conta ou chave SSH autorizada no GitHub. O instalador pede as credenciais somente se `/opt/price-monitor/.env` ainda nao existir. Se o servico ja foi instalado pelo pacote, reutiliza o `.env` e os dados existentes nesse diretorio.

## Atualizar

No Windows, depois de alterar e testar:

```powershell
git add .
python scripts/check_repository.py
git commit -m "Descreva a atualizacao"
git push
```

No servidor, como o usuario dono do clone:

```bash
cd ~/monitor-precos-src
bash deploy/update.sh
```

Esse comando executa `git pull --ff-only`, reinstala as dependencias necessarias e reinicia o servico. Preserva `/opt/price-monitor/.env` e `/opt/price-monitor/data`. Recusa atualizacao se houver alteracoes locais rastreadas. Um `git pull` sozinho atualiza o clone, mas o servico usa a copia instalada em `/opt/price-monitor`.

Se ja executou o pull manualmente:

```bash
git pull --ff-only
bash deploy/update.sh --no-pull
```

Antes de atualizacoes importantes, faca um backup do banco com `scripts/export_database.py` (consulte `LEIA-ME-KALI.md`) e guarde uma copia privada do `.env`.

```bash
sudo systemctl status price-monitor --no-pager
sudo journalctl -u price-monitor -n 50 --no-pager
```

Confira `/status` e `/ajuda` no Telegram. Os testes do GitHub usam dados simulados e snapshots; nao comprovam que as lojas estao acessiveis no servidor. A instalacao systemd deve ser validada no Kali; consulte `VALIDACAO.md` para os limites dos testes reais.
