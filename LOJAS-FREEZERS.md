# Shopee e freezers verticais

## Loja oficial Brastemp (19/10/2026)

`brastemp.com.br` integrado à busca, cadastro por link e menu de promoções.
A descoberta usa os dois sitemaps de produtos publicados pela loja, com índice
externo como alternativa quando não há candidato compatível. A cobertura é limitada.

```text
/buscar freezer vertical Brastemp
/buscar Brastemp BVR28PB
```

O adaptador confere SKU, EAN, título e voltagem selecionados usando Schema.org e
os dados Next.js do próprio produto. Preços conflitantes entre essas fontes são
recusados. O preço de cartão vem do total explícito de uma parcela sem juros,
identificando a bandeira; nunca do valor de uma parcela de um plano parcelado.
Pix só é informado quando associado explicitamente à oferta, sem aplicar
novamente descontos. Vendedor sem nome pode aparecer pelo identificador publicado.

Teste real local: BVR28PB 110V e 220V tiveram preço e estoque explícitos, com
EANs diferentes. BVR28NK e BVR28NB foram identificados como indisponíveis.
Categoria de freezers verticais e descoberta por sitemap também foram consultadas.
Essas leituras não garantem os mesmos valores ou disponibilidade na VPS.
O preço de referência (`listPrice`) só é usado para a mesma oferta/SKU validada;
não comprova queda histórica. Frete não incluído.

O instalador inclui Brastemp nas listas padrão anteriores. Em lista personalizada,
acrescente `brastemp.com.br` ao `ALLOWED_DOMAINS` e reinicie o serviço.

Use os comandos e botões existentes:

```text
/buscar freezer vertical
/buscar freezer vertical EOS EFV300 110V
/buscar freezer vertical Consul 220V
```

A busca consulta as lojas autorizadas. Para cadastrar acompanhamento, use o ID
da oferta ou seu link em `/monitorar`. A busca sozinha não cria monitoramento.
Voltagem e capacidade diferentes não são tratadas como o mesmo freezer. Peças,
gavetas e termostatos são descartados quando você procura o equipamento completo.

| Loja | Integração e validação em 19/10/2026 |
| --- | --- |
| Frigelar | Descoberta por dois sitemaps públicos anunciados pela loja, com índice externo como alternativa. Consulta real encontrou seis candidatos; quatro páginas de produtos foram lidas com preço e estoque explícitos. |
| Shopee | Adaptador de links individuais e ofertas Schema.org, com descoberta pelo índice externo existente. A busca real não retornou candidatos nesta amostra. Um link de produto respondeu HTTP 200, mas permaneceu sem oferta estruturada, inclusive com Chromium. **Coleta de preços reais ainda não validada.** |
| Magalu | Descoberta pelo índice externo e leitura conservadora de ofertas Schema.org. Busca e produto testados responderam HTTP 403. **Coleta real bloqueada neste ambiente.** |

Os testes de Shopee/Magalu com ofertas estruturadas são **simulados**. Não se
afirma que essas lojas passaram a devolver preços reais. O resultado depende da
página e do ambiente; não há contorno de bloqueios, CAPTCHA ou autenticação.
Links encontrados sem leitura continuam identificados como não verificados.

Frigelar publicou preço genérico, sem associar vendedor ou forma de pagamento.
O bot mostra o valor, mas mantém os alertas suspensos enquanto esses campos
não estiverem explícitos. Não presume Pix, cupom ou condição de membro.
O preço anterior não é inventado para qualificar uma promoção percentual.
O frete não está incluído. As consultas são limitadas, não representam o catálogo inteiro.

As integrações anteriores, como Amazon, KaBuM e Mercado Livre, permanecem nas
buscas conforme a configuração e suas limitações de acesso.

## Atualizar no servidor

```bash
cd ~/monitor-precos-src
bash deploy/update.sh
```

O instalador acrescenta Shopee, Magalu e Frigelar às listas padrão antigas,
preservando credenciais e banco. Listas personalizadas são preservadas; nesse
caso acrescente `shopee.com.br,magazineluiza.com.br,frigelar.com.br` ao valor de
`ALLOWED_DOMAINS` em `/opt/price-monitor/.env` e reinicie o serviço.

Diagnóstico por link na VPS, sem enviar mensagens ao Telegram:

```bash
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_offers --no-browser --url 'https://www.frigelar.com.br/freezer-vertical-eos-242-litros-ecogelo-efv300-110v/p/kit8956'
```

O teste real foi executado no ambiente local de desenvolvimento, não na VPS.
Fixtures Frigelar guardam somente o JSON-LD público reduzido e não indicam preços atuais.
