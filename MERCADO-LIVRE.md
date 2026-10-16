# Pesquisa de produtos Mercado Livre

## Descoberta externa sem chave

Use no Telegram:

```text
/buscarml Gigabyte B550 Aorus Elite V2
```

O comando consulta o indice externo Tavily Search no [modo oficial sem chave](https://docs.tavily.com/documentation/keyless). Nao precisa criar aplicativo Mercado Livre, fornecer token, configurar dominio ou redirect. Somente o texto do produto e o filtro de dominio sao enviados a Tavily; nao envia Telegram ID, token Telegram ou banco de dados. Nao usa chave Tavily nem fallback automatico para plano pago.

`/buscar nome`, com `SEARCH_PROVIDER=direct`, tambem inclui essa descoberta junto das outras lojas. `mercadolivre.com.br` precisa estar em `ALLOWED_DOMAINS`. O instalador acrescenta esse dominio a lista padrao antiga, preservando listas personalizadas.

O bot aceita apenas links HTTPS em hosts Mercado Livre autorizados e paginas de anuncio/produto. Descarta categorias, dominios externos, arquivos/manual/BIOS nao solicitados e conflitos entre consulta e modelo no slug. Titulo e endereco compativeis nao comprovam modelo exato: o indice pode estar desatualizado.

## Resultados nao verificados

A descoberta de links e a leitura de precos sao etapas distintas. Links nao conferidos aparecem com titulo, fonte, link e aviso de que preco, estoque, vendedor, condicao e pagamento nao foram verificados. Nao recebem medalha ou ID de anuncio monitoravel e nao ativam alertas. Catalogos podem alternar vendedores, portanto nao representam uma oferta individual. Se um anuncio individual puder ser lido pela pagina, segue o fluxo normal de ofertas.

HTTP e Chromium receberam 403 ao obter robots.txt do Mercado Livre nos ambientes testados. A descoberta externa nao remove esse bloqueio. Precos, estoque e alertas reais dessa loja continuam sem validacao e nunca sao importados de snippets ou precos da API.

## Limites e configuracao

O modo sem chave tem limites publicos e disponibilidade variavel. O bot guarda ate 32 consultas em memoria por cinco horas, serializa chamadas e aguarda apos limites de requisicao, sem trocar IP/conta. O cache se perde ao reiniciar, sem afetar produtos e historico SQLite. Falhas sao informadas; ausencia de resultados nao comprova ausencia do produto.

`MERCADOLIVRE_DISCOVERY=external` e o padrao. `site` tenta o formulario GET publico, sujeito a robots.txt e bloqueios. Se `MERCADOLIVRE_ACCESS_TOKEN` estiver preenchido, pesquisas gerais usam a API oficial, que pode exigir permissoes adicionais e renovacao manual. `/buscarml` usa sempre o indice externo sem chave. OAuth e renovacao automatica nao estao implementados.

## Validacao

Em 15/10/2026, a chamada real a `https://api.tavily.com/search` em modo keyless respondeu 200 e retornou paginas Mercado Livre para B550 Aorus Elite V2, inclusive `https://www.mercadolivre.com.br/placa-mae-gigabyte-b550-aorus-elite-v2-12-ddr4-am4-atx/p/MLB22450130`. O fluxo real de descoberta e geracao de mensagens foi executado com SQLite em memoria: nenhum monitoramento ou oferta valida foi criado a partir dos links nao conferidos. Nao foram enviados Telegram reais nem confirmados precos atuais.

Os testes simulados cobrem dominio permitido, cache, limites, conflito titulo/endereco, exclusao de categorias/arquivos, ausencia de preco do indice e entrega de links sem criar ofertas. A disponibilidade na VPS deve ser conferida apos atualizar.

Diagnostico opcional, sem Telegram:

```bash
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_stores --browser --store mercadolivre.com.br --query "Gigabyte B550 Aorus Elite V2"
```

`discovered_urls` mostra os links do indice. Falha ao ler a pagina pode continuar aparecendo separadamente.
