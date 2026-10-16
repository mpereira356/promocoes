# Echo Dot - 2026.10.16-echo-search.1

Falha de descoberta Amazon reproduzida para "Echo Dot 5a geracao" (com ordinal e acentos no comando original). A consulta externa com inurl:dp devolveu produtos sem relacao; sem o operador retornou links Echo. Agora existe uma unica alternativa sem o operador quando a primeira consulta nao encontra candidatos relevantes. Ambas usam cache e nao ha alternativa apos erro de quota/bloqueio. Categorias continuam descartadas e precos do indice externo continuam ignorados.

O titulo real Amazon diz "geracao mais recente" e omite o numero. Para descoberta provisoria, o slug de um Echo Dot pode fornecer geracao; isso nao basta para aceitar a leitura. A ficha tecnica observada em #tech declara Echo Dot 5a geracao (2022), vinculada ao ASIN B09B8VGCR8. Essa evidencia e registrada separadamente e usada na verificacao da consulta e exibida no cartao. Echo Show, Dot Max, outra geracao e suportes sao rejeitados nos testes. URLs de outro modelo nao substituem a ficha tecnica; sem evidencia a correspondencia continua recusada.

Consultas reais locais em 16/10/2026: descoberta do Echo Dot preto e uma leitura com R$ 584,11, Amazon.com.br, disponivel. Em repeticoes posteriores, a mesma pagina ocultou o preco e pediu carrinho, sem valor individual verificavel. O fluxo completo de descoberta/leitura/SQLite/formatacao foi executado com HTTP real e entrega Telegram simulada: um candidato foi entregue, sem falha de descoberta, mas sem preco na resposta oculta. Portanto nao se afirma leitura de preco permanente. Nenhuma compra/carrinho foi acionado, nenhum bloqueio foi contornado e nao houve acesso a VPS. Pichau, Terabyte e Mercado Livre nao foram revalidados nesta revisao.

346 testes passaram, com tres avisos PTB preexistentes. Dez novos testes cobrem alternativa limitada/cache/quota, geracao da ficha tecnica, versoes/acessorios e alternancia real de resposta visivel/oculta. Os dois recortes reais foram reduzidos para excluir scripts, formularios e dados de sessao.

# Entrega de resultados - 2026.10.16-search-delivery.1

Corrigido o alcance da falha: antes, uma excecao ao salvar ou enviar um unico cartao abortava todos os demais resultados. Agora cada anuncio tem isolamento de persistencia e entrega, com contadores separados e continuidade do processamento. Falhas ao enviar avisos nao impedem tentar enviar o resumo. Nao se reenvia automaticamente o cartao inteiro apos timeout ambiguo, para evitar duplicacao; o resumo informa entrega incompleta ou nao confirmada. Se o Telegram estiver indisponivel para o resumo, a falha e registrada, sem prometer entrega.

336 testes passaram, com tres avisos PTB preexistentes. Nove novos testes simulam falha no quarto de cinco resultados: TimedOut, BadRequest e erro interno, tanto ao salvar quanto ao enviar; verificam entrega do quinto resultado e ausencia de reenvio dos anteriores. Um deles usa SQLite real e o formatador de cartoes, com transporte Telegram simulado. Tambem foram simuladas falhas em avisos e resumo. Logs registram somente etapa, classe de excecao e arquivo/linha/funcao; mensagens de excecao, argumentos e variaveis nao sao expostos.

A excecao especifica ocorrida na VPS apos a oferta MONOZEL nao foi identificada pela mensagem generica enviada pelo usuario. Esta revisao corrige a interrupcao em cascata e torna o erro diagnosticavel. Nao houve acesso SSH nem envio real ao Telegram; leitura de precos e bloqueios das lojas nao foram revalidados nesta revisao.

# Amazon - 2026.10.16-amazon-starting.1

Leitura real local em 16/10/2026 dos tres links informados: B0GQ5145QV esta indisponivel, sem preco; B004PS7O9I (Karcher) e B0BT23S5MF (WAP) ocultam o preco principal com mensagem de carrinho. O widget publico de outras ofertas declara valores a partir de R$ 234,06 e R$ 145,90, respectivamente. O leitor agora coleta essa referencia vinculada ao mesmo ASIN e mostra separadamente, com link para as outras ofertas. Nao atribui o valor ao vendedor principal, nao confirma estoque/pagamento e nao usa esse minimo em ranking, series de precos validos ou alertas. O campo price continua nulo quando a oferta individual nao foi confirmada.

O caminho completo Monitor -> adaptador -> mensagem foi conferido com HTTP real local para Karcher e WAP, com navegador habilitado na configuracao, sem adicionar itens ao carrinho. Links publicos de outras ofertas tambem foram consultados por HTTP: retornaram pagina do mesmo ASIN sem linhas individuais AOD. Portanto, a coleta completa de vendedor e preco individual continua sem validacao nesses dois anuncios; nao se afirma que essa limitacao foi resolvida. Falhas de rede da VPS nao foram reproduzidas nem eliminadas. Nao houve envio real ao Telegram ou acesso SSH.

327 testes passaram (tres avisos PTB de depreciacao). Simulacoes e recortes reais reduzidos verificam ASIN/origem/escopo, moeda, valores zero e ambiguos, ausencia de ranking, entrega da referencia na mensagem, ausencia de alerta e preservacao do ultimo preco valido. Os valores acima sao capturas pontuais, nao garantias de precos atuais.

# Amazon - 2026.10.16-amazon-query.1

Falha reproduzida ao vivo localmente em 16/10/2026: a consulta "Aspirador de Po Portatil" com acentos retornou somente paginas de busca, mesmo com inurl:dp. A mesma consulta sem diacriticos retornou produtos individuais. A descoberta Amazon agora remove apenas diacriticos, preservando codigos, pontuacao e as regras de conferencia do produto. A chave de cache usa a mesma grafia normalizada, sem consultas duplicadas. Nao houve contorno de bloqueios ou limites.

Depois da alteracao, a consulta original encontrou candidatos sem o aviso de ausencia. Uma leitura real separada confirmou MONOZEL B0F53JGRLS por R$ 242,96, em estoque, vendedor Amazon Global. Outros candidatos estavam indisponiveis e sem preco. Pecas de reposicao foram excluidas dos resultados de aspiradores completos. Sao capturas locais pontuais; a VPS e o envio real no Telegram nao foram validados. Nao se garante descoberta de qualquer produto ou disponibilidade permanente do indice externo.

317 testes passaram, incluindo simulacoes de normalizacao, cache, preservacao de codigo de modelo e exclusao de motor sobressalente. Tres avisos de depreciacao PTB continuam nos testes de RetryAfter, sem falhas.

# Amazon — 2026.10.16-amazon-main.1

Consulta real local: descoberta e leitura de páginas individuais de aspiradores passaram a obter preços no bloco principal. MONOZEL B0F53JGRLS: R$ 242,96, Amazon Global, disponível. WAP B0BT23S5MF: R$ 149,00, disponível. Esses valores são capturas pontuais, sem validação pelo IP da VPS. Condição/pagamento ausentes continuam impedindo alertas comparáveis. Preço oculto com exigência de carrinho continua sem confirmação. Não se garante leitura de todo anúncio Amazon.

315 testes passaram; detalhes e limitações em VALIDACAO.md. Os registros anteriores abaixo permanecem como histórico.

# Estado observado — 2026.10.16-review.1

As observações abaixo são consultas locais limitadas, sem envio real ao Telegram ou acesso à VPS. Os registros antigos permanecem após esta tabela como histórico.

| Loja | Validação nesta revisão | Limitação restante |
| --- | --- | --- |
| KaBuM | G PRO 920-009388: R$ 699,99 Pix, disponível | Condição ausente; comparação e alertas dessa leitura continuam suspensos |
| Pichau | G PRO 920-009388: R$ 639,99 Pix, novo, disponível | O bloqueio relatado na VPS não foi reproduzido localmente |
| Terabyte | Corsair K65 Pro Mini: R$ 649,99 Pix/Boleto, novo, disponível; bloco de/por validado | Descoberta limitada não encontrou Logitech G PRO; outros layouts podem exigir adaptação |
| Mercado Livre | Links externos foram encontrados | Robots indisponível; sem preço validado nesta revisão |
| Amazon Brasil | Links externos foram encontrados | Preço oculto com exigência de carrinho; sem preço validado nesta revisão |

Consulte VALIDACAO.md para separar testes simulados, capturas e consultas reais. Nenhuma afirmação de cobertura integral ou disponibilidade futura é feita.

# Precos Amazon ? registro 2026.10.15-amazon-offers.1

O leitor agora tenta o painel publico de opcoes de compra quando a pagina Amazon nao fornece preco e nao declara indisponibilidade. Usa o link publicado pela loja ou o painel AOD observado no redirecionamento real, sempre para o mesmo ASIN e com robots.txt conferido antes. Selenium normal, sem stealth, login ou interacao com CAPTCHA; nenhum botao de carrinho/compra e acionado. O navegador roda em uma thread com fila, sem bloquear comandos Telegram, e e encerrado ao final de cada leitura.

Validacao real local em 15/10/2026: o fluxo Monitor.read completo no anuncio https://www.amazon.com.br/Gigabyte-B550-AORUS-ELITE-AX/dp/B08KGVH7YC retornou 172711 centavos (R$ 1.727,11), vendedor Amazon Global (ID A2EB9PYM83FCP9), condicao Novo. O painel apresentava frete separado; esse valor nao foi somado ao preco. Sao dados observados no teste, nao precos fixos no codigo. O painel nao declarou modalidade nem estoque de forma explicita; esses campos continuam desconhecidos, impedindo comparacoes e medalhas dessa leitura. Nao houve envio Telegram real nem alteracao do banco do usuario.

170 testes locais passaram. A fixture amazon_aod_real.html e um recorte de DOM real, sem forms, cookies ou tokens. Testes simulados extras cobrem conflitos de preco, frete/cupom, troca de produto/ASIN, bloqueio por robots e acionamento do navegador so quando falta preco.

O instalador com --with-browser (usado por deploy/update.sh) instala chromium-driver e Selenium. A execucao desse novo fluxo ainda nao foi validada na VPS Kali; nao e necessario executar o diagnostico Selenium manual anterior para ativar a coleta Amazon.

# Estado real das lojas em 15/10/2026

Teste adicional Selenium 4.51.0 + Chrome padrao headless em 15/10/2026: robots.txt Mercado Livre respondeu 403 (text/html). Nenhuma pagina de produto ou preco foi consultada apos essa recusa. Teste local Windows; nao foi testado Selenium com janela visivel nem na VPS. O transporte geral permanece Playwright; o painel de ofertas Amazon agora usa Selenium normal quando o preco nao esta no HTML inicial.

Diagnostico Selenium opcional no Kali, apos atualizar o projeto:

```bash
sudo apt-get install -y chromium chromium-driver
sudo /opt/price-monitor/.venv/bin/python -m pip install -r /opt/price-monitor/requirements-selenium.txt
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_selenium --binary /usr/bin/chromium --driver /usr/bin/chromedriver
```

Esse teste nao acessa Telegram ou SQLite. `--headed` exige ambiente grafico e pode ser usado em computador com desktop; nao funciona em SSH puro. Usa perfil novo, nao importa cookies do navegador pessoal e nao interage com desafios. A instalacao do driver no Kali ainda depende de validacao no servidor.

Versao atual: `2026.10.15-amazon-offers.1`. Os testes anteriores abaixo permanecem como registro historico.

| Loja | Descoberta real | Leitura real validada nesta etapa | Limite atual |
| --- | --- | --- | --- |
| Pichau | B550 Aorus Elite V2 encontrada; sitemap limitado com alternativa em indice externo | Link fornecido pelo usuario: titulo, vendedor Pichau, condicao nova, Pix, preco e disponibilidade da pagina | Validacao de uma oferta nao garante cobertura de todo o catalogo |
| KaBuM | B550 Aorus Elite V2 encontrada | Titulo, preco, Pix, vendedor GIGANTEC e disponibilidade | Condicao ausente na pagina analisada; alertas dessa oferta permanecem suspensos |
| Terabyte | B550 Aorus Elite V2 e Open Box encontradas | Oferta regular: titulo, preco, vendedor, condicao e indisponibilidade declarada | Modalidade de pagamento nao confirmada para a oferta indisponivel; nao anunciar como disponivel |
| Mercado Livre | Links encontrados no indice externo | Paginas continuam bloqueando a leitura com 403 | Links nao verificados nao recebem preco, medalha ou monitoramento |
| Amazon Brasil | Links reais encontrados | Anuncio B08KGVH7YC: preco do painel AOD, vendedor Amazon Global e condicao Novo, com Selenium normal | Modalidade de pagamento e estoque nao explicitados no painel; alertas dessa leitura continuam suspensos. Alguns outros produtos seguem com preco oculto ou indisponivel |

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
