# Estado real das lojas em 15/10/2026

Teste adicional Selenium 4.51.0 + Chrome padrao headless em 15/10/2026: robots.txt Mercado Livre respondeu 403 (text/html). Nenhuma pagina de produto ou preco foi consultada apos essa recusa. Teste local Windows; nao foi testado Selenium com janela visivel nem na VPS. O motor de producao permanece Playwright.

Diagnostico Selenium opcional no Kali, apos atualizar o projeto:

```bash
sudo apt-get install -y chromium chromium-driver
sudo /opt/price-monitor/.venv/bin/python -m pip install -r /opt/price-monitor/requirements-selenium.txt
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_selenium --binary /usr/bin/chromium --driver /usr/bin/chromedriver
```

Esse teste nao acessa Telegram ou SQLite. `--headed` exige ambiente grafico e pode ser usado em computador com desktop; nao funciona em SSH puro. Usa perfil novo, nao importa cookies do navegador pessoal e nao interage com desafios. A instalacao do driver no Kali ainda depende de validacao no servidor.

Versao: `2026.10.15-stores.1`.

| Loja | Descoberta real | Leitura real validada nesta etapa | Limite atual |
| --- | --- | --- | --- |
| Pichau | B550 Aorus Elite V2 encontrada; sitemap limitado com alternativa em indice externo | Link fornecido pelo usuario: titulo, vendedor Pichau, condicao nova, Pix, preco e disponibilidade da pagina | Validacao de uma oferta nao garante cobertura de todo o catalogo |
| KaBuM | B550 Aorus Elite V2 encontrada | Titulo, preco, Pix, vendedor GIGANTEC e disponibilidade | Condicao ausente na pagina analisada; alertas dessa oferta permanecem suspensos |
| Terabyte | B550 Aorus Elite V2 e Open Box encontradas | Oferta regular: titulo, preco, vendedor, condicao e indisponibilidade declarada | Modalidade de pagamento nao confirmada para a oferta indisponivel; nao anunciar como disponivel |
| Mercado Livre | Links encontrados no indice externo | Paginas continuam bloqueando a leitura com 403 | Links nao verificados nao recebem preco, medalha ou monitoramento |
| Amazon Brasil | Links reais da B550 e de Echo Dot encontrados | B550: titulo e indisponibilidade explicita. Echo Dot: titulo e vendedor Amazon.com.br | Amazon omitiu preco na resposta e pediu adicionar ao carrinho; nao foi feito login, compra ou interacao com carrinho. Condicao e estoque Echo nao confirmados |

**Nao ha validacao completa de todos os campos em todas as lojas.** Nenhum adaptador pode prometer encontrar qualquer produto, interpretar qualquer frase ou manter acesso a paginas que mudam/restringem acesso. Os campos ausentes sao declarados ausentes, sem inferir produto novo, Pix ou estoque.

## Correcoes

- Pichau/Terabyte: se o sitemap limitado nao trouxer candidatos compativeis, consultar o indice externo Tavily sem chave. Falhas de bloqueio/robots no acesso a loja continuam respeitadas. Descoberta de links nao autoriza leitura proibida.
- Separar Aorus Elite V2 de Elite AX V2 e Gaming X V2; nao tratar esses modelos como ofertas equivalentes. Recusar um titulo real divergente mesmo quando o indice apresentou um titulo compativel.
- Tratar acentos, hifens, Wi-Fi, ordinais como 5a geracao e espaco em capacidades como 500 GB. Isso nao constitui um interpretador universal de linguagem natural.
- Amazon tem adaptador separado, aceita somente paginas de produto DP/ASIN ou gp/product e nao usa precos de recomendacoes, cupons ou snippets. Na ausencia de Schema.org, apenas campos observados nas duas paginas reais analisadas sao usados.
- Remover parametros conhecidos de publicidade dos links, preservando parametros de variacao de produto.

O aviso antigo do Mercado Livre sobre falta de aplicativo nao pertence a esta versao. Confirme a versao com `/status` apos atualizar.

## Reproduzir no servidor

```bash
cd ~/monitor-precos-src
bash deploy/update.sh
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_stores --browser --store kabum.com.br,pichau.com.br,terabyteshop.com.br,mercadolivre.com.br,amazon.com.br --query "Gigabyte B550 Aorus Elite V2"
```

O diagnostico consulta fontes reais sem enviar Telegram ou alterar SQLite. Mostra os links, origem da descoberta, campos lidos, preco em centavos e se a leitura pode ser comparada. So consulta a primeira pagina encontrada de cada loja. A disponibilidade na VPS pode diferir deste ambiente Windows.

O instalador atualiza as listas padrao anteriores de tres ou quatro lojas, incluindo Amazon. Se voce usa lista personalizada, acrescente `amazon.com.br` manualmente em `ALLOWED_DOMAINS` e reinicie o servico.

## Testes

Os testes locais incluem simulacoes de sitemap incompleto, conflito de modelos, dados ausentes e desafios antirobo. As fixtures Amazon sao recortes reduzidos de HTML real, explicitamente identificados: uma oferta indisponivel e outra com preco oculto. Nao sao testes de acesso ao vivo. As verificacoes reais descritas na tabela foram executadas separadamente e nao enviaram alertas Telegram.
