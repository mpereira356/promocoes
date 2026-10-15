# Levar o robô para Kali Linux por SSH

Este pacote não exige interface gráfica. Instala o projeto em `/opt/price-monitor`, usa ambiente virtual Python e um usuário de serviço sem login (`pricebot`). O systemd mantém o processo após desconectar do SSH e o inicia após reiniciar o servidor.

O pacote **não contém seu `.env`, token, chave de busca ou banco pessoal**. O instalador pede os dados no terminal e oculta a digitação do token. Não precisa de chave Brave: usa busca direta. As restrições das lojas continuam iguais às documentadas no README; mudar para Kali não garante desbloqueio.

## 1. Transferir pelo Windows

No PowerShell, dentro da pasta do projeto:

```powershell
scp .\monitor-precos-kali.tar.gz usuario@IP_DO_SERVIDOR:~/
ssh usuario@IP_DO_SERVIDOR
```

Substitua usuário e IP pelos seus dados. Para porta SSH diferente, use `scp -P PORTA` e `ssh -p PORTA`. Será solicitado acesso ao seu servidor; não há chave SSH incluída.

**Pare o bot no Windows com Ctrl+C antes de iniciar no servidor.** Não rode o mesmo token nos dois lugares: eles disputariam as atualizações do Telegram. O lock de instância protege somente processos que usam o mesmo banco na mesma máquina.

## 2. Instalar no Kali

No terminal conectado por SSH:

```bash
tar -xzf monitor-precos-kali.tar.gz
cd monitor-precos-kali
sudo bash deploy/install-kali.sh
```

Se estiver conectado como root e `sudo` não existir, use `bash deploy/install-kali.sh`.

O instalador requer Kali/Debian com **systemd ativo**, Python 3.11+ e acesso de saída a repositórios APT/PyPI, Telegram e lojas. Ele instala dependências do sistema, cria `.venv`, pede token, ID do grupo e seu ID pessoal, valida a configuração local e ativa o serviço. O ID do grupo e seu ID pessoal sao obrigatorios.

Cole somente o token quando solicitado; a digitação ficará oculta. A autenticação real acontece ao iniciar o bot, não durante a validação local. Serviço ativo no systemd não prova que o token, o grupo ou as lojas estejam acessíveis: confirme com `/ajuda` no Telegram. Não precisa abrir porta de entrada para o bot; ele usa polling de saída.

O instalador não usa `pip` no Python do sistema nem `--break-system-packages`: as dependências ficam no ambiente virtual. Isso acompanha a orientação do [Kali sobre ambientes Python isolados](https://www.kali.org/docs/general-use/python3-external-packages/). `requirements-server.txt` instala apenas dependências de execução HTTP; não instala pytest, Playwright ou navegador. O modo padrão não precisa deles.

## 3. Usar e administrar

No Telegram:

```text
/ajuda
/buscar b550
/monitorar ID_DO_ANUNCIO
/lista
```

No SSH:

```bash
sudo systemctl status price-monitor --no-pager
sudo journalctl -u price-monitor -n 50 --no-pager
sudo journalctl -u price-monitor -f
sudo systemctl restart price-monitor
sudo systemctl stop price-monitor
sudo systemctl start price-monitor
```

Ctrl+C ao acompanhar os logs apenas sai do visualizador; o serviço continua ativo. Depois de confirmar que o bot respondeu, pode sair do SSH com `exit`. O serviço está habilitado para subir no próximo boot.

Para configurar novamente:

```bash
sudo nano /opt/price-monitor/.env
sudo systemctl restart price-monitor
```

Os dados ficam em `/opt/price-monitor/data/monitor.sqlite3`. O serviço só tem permissão de escrita em `data`; mantenha `DATABASE_PATH=data/monitor.sqlite3`. O usuário `pricebot` não executa como root. `.env` tem permissão 640 e fica fora do pacote.

## 4. Preservar o histórico e os IDs do Windows (opcional)

Sem esta etapa, o servidor começa com banco vazio. O código é o mesmo, mas os anúncios e acompanhamentos locais não são transferidos automaticamente.

Ainda no Windows, exporte um snapshot consistente do SQLite. O script considera o WAL e recusa substituir arquivos existentes:

```powershell
.\.venv\Scripts\python.exe -m scripts.export_database monitor-backup.sqlite3
scp .\monitor-backup.sqlite3 usuario@IP_DO_SERVIDOR:~/
```

Depois pare o bot do Windows e faça a primeira instalação no Kali com:

```bash
tar -xzf monitor-precos-kali.tar.gz
cd monitor-precos-kali
sudo bash deploy/install-kali.sh --restore "$HOME/monitor-backup.sqlite3"
```

A opção `--restore` é somente para instalação nova, antes de existir banco no destino. Confere integridade e tabelas do projeto, instala o snapshot com permissões apropriadas e deixa o programa executar as migrações. Preserva IDs, histórico, agenda e pausas existentes no momento da exportação. Tokens não estão nesse backup. Proteja o arquivo, pois contém seu histórico de produtos.

Se o servidor já possui banco, o instalador recusa sobrescrevê-lo. Não copie um banco por cima de uma instalação ativa: faça um backup do servidor e planeje a migração antes de substituir dados.

## 5. Atualizar

Transfira um novo pacote e extraia em uma pasta de origem, como na primeira instalação. Execute novamente `sudo bash deploy/install-kali.sh`. Ele preserva `.env`, `data` e `.venv`, para o serviço antes de copiar código, atualiza dependências e reinicia. Faça um backup do banco antes de atualizar:

```bash
sudo systemctl stop price-monitor
cd /opt/price-monitor
sudo .venv/bin/python -m scripts.export_database /tmp/monitor-antes-atualizacao.sqlite3
```

Guarde o backup em local protegido. Se a atualização falhar, o instalador avisa; o serviço pode permanecer parado. Consulte status/logs, corrija a falha e execute o instalador novamente. Não se promete rollback automático do código.

## 6. Ambiente sem systemd

Contêineres, alguns ambientes chroot e certas configurações de WSL podem não ter systemd. O instalador recusa esse caso antes de instalar. É possível executar manualmente, mas esse caminho não gerencia início após boot:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ca-certificates tzdata nano tmux
cd ~/monitor-precos-kali
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-server.txt
cp .env.example .env
chmod 600 .env
nano .env
tmux new -s precos
.venv/bin/python -m monitor
```

Para desconectar da sessão tmux sem encerrar o processo: Ctrl+B, solte, depois D. Para voltar: `tmux attach -t precos`. Uma sessão tmux não inicia novamente sozinha após reboot. Em um servidor Kali com systemd, prefira o instalador.

## Validação deste pacote

O projeto foi desenvolvido em Windows. Foram verificadas sintaxe Bash, estrutura/permissões do arquivo tar, ausência de `.env`/dados pessoais no pacote e exportação SQLite com dados simulados. **A instalação APT/systemd e a operação real no seu Kali não foram executadas aqui.** Chromium/Playwright no servidor não faz parte deste instalador e não foi validado. Veja `VALIDACAO.md` para as verificações anteriores do robô e as limitações reais das lojas.

## Atualização de acesso por Chromium: versão 2026.10.15-browser.1

Para corrigir o acesso Pichau/Terabyte, transfira o **novo** arquivo `monitor-precos-kali-browser.tar.gz`, extraia e execute:

```bash
tar -xzf monitor-precos-kali-browser.tar.gz
cd monitor-precos-kali
sudo bash deploy/install-kali.sh --with-browser
```

A opção instala Chromium e bibliotecas nativas via APT, instala Playwright no ambiente virtual e baixa a versão de navegador compatível com o Playwright. O teste de inicialização do navegador é executado como `pricebot` antes de iniciar o serviço. Não abre janela nem exige desktop. A instalação pode baixar centenas de MB.

O instalador preserva token, IDs e banco, mas ativa `PLAYWRIGHT_ENABLED=true` e configura `PLAYWRIGHT_BROWSERS_PATH`, `XDG_CACHE_HOME` e `XDG_CONFIG_HOME` dentro de `/opt/price-monitor/data`, onde o serviço pode escrever. A KaBuM continua usando HTTP; Pichau e Terabyte usam Chromium comum, com o mesmo User-Agent identificável PriceMonitor, sem proxies, stealth ou solução de CAPTCHA. O transporte inicial não executa JavaScript: as ofertas testadas já entregaram dados no HTML. Renderização só é usada se necessária em página permitida.

Após atualizar, envie `/status` no Telegram. Deve informar **2026.10.15-browser.1**, Chromium **ativado** e descoberta por sitemaps. Isso confirma que o processo foi atualizado; uma resposta antiga indica que outra cópia ainda está executando.

Diagnóstico direto no servidor, sem Telegram e sem imprimir credenciais:

```bash
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_stores --browser --query "Gigabyte B550 Aorus Elite V2"
```

A saída mostra a versão, links descobertos, dados identificados e códigos de erro. Não cria monitoramentos nem dispara alertas. O programa respeita robots.txt para cada página e interrompe barreiras reais de CAPTCHA. Um widget opcional no formulário de avaliações não impede ler dados públicos já presentes na página, nem é resolvido/interagido pelo robô.

**Validação real local:** o transporte de produção leu a Elite V2 da Pichau, identificando Pix, vendedor Pichau, condição nova e estoque disponível. Na Terabyte, leu o mesmo modelo e identificou estoque indisponível e vendedor TerabyteShop; o preço visual zero dessa página não virou um preço válido. As pesquisas das duas lojas retornaram links sem os antigos avisos. Isso foi executado no Windows com Chromium; a instalação APT/systemd no seu Kali continua dependendo da execução do instalador no servidor.
