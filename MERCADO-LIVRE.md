# Mercado Livre: situacao real e configuracao

**A busca real ainda nao foi validada.** Em 15/10/2026, HTTP e Chromium receberam 403, inclusive ao consultar robots.txt. A API oficial sem autenticacao tambem respondeu 403. Trocar para Selenium nao garante acesso. Nao foi validado nenhum anuncio real do Mercado Livre.

Existem dois caminhos implementados:

1. Sem token: o bot tenta descobrir o formulario GET publico e extrair links individuais. Se robots.txt, bloqueio ou CAPTCHA impedir o acesso, informa a falha.
2. Com `MERCADOLIVRE_ACCESS_TOKEN`: usa `GET https://api.mercadolibre.com/sites/MLB/search` com autorizacao Bearer somente para descobrir titulo e link. Preco e estoque da API sao ignorados; a oferta continua exigindo leitura permitida da pagina.

O segundo caminho exige um aplicativo cadastrado e autorizado no [Mercado Livre Developers](https://developers.mercadolivre.com.br/), seguindo a documentacao de [autenticacao](https://developers.mercadolivre.com.br/autenticacao-e-autorizacao) e [busca de itens](https://developers.mercadolivre.com.br/pt_br/itens-e-buscas). Cadastro, permissoes e autorizacao da conta dependem do usuario e do Mercado Livre. Um token pode nao ter permissao de busca; 403 com token nao e tratado como sucesso.

Quando tiver um token valido, adicione em `/opt/price-monitor/.env`:

```dotenv
MERCADOLIVRE_ACCESS_TOKEN=
```

Preencha o valor apenas no servidor, sem enviar pelo chat ou GitHub. Mantenha `mercadolivre.com.br` em `ALLOWED_DOMAINS` e `PLAYWRIGHT_ENABLED=true`. Reinicie:

```bash
sudo systemctl restart price-monitor
```

O token expira conforme a autorizacao do aplicativo. Esta implementacao nao inclui fluxo OAuth ou renovacao automatica; o token precisa ser atualizado quando expirar. Alertas Mercado Livre nao foram validados de ponta a ponta.

Para diagnosticar no Kali sem enviar Telegram nem alterar o banco:

```bash
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_stores --browser --store mercadolivre.com.br --query "Gigabyte B550 Aorus Elite V2"
```

O comando usa o `.env` local e imprime somente o resultado do diagnostico, sem credenciais. Compartilhe a saida se quiser investigar a disponibilidade na VPS. `discovered_urls: []` e aviso de acesso suspenso significam falha de descoberta, nao ausencia de produtos.

136 testes locais passaram: o conector da API foi testado exclusivamente com respostas simuladas (links individuais, exclusao de catalogos/dominios externos, precos ignorados, erros 401/403 sem repeticao ou exposicao de detalhes). Isso nao comprova permissoes da API nem acesso a paginas reais.
