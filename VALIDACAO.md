# Atualização 2026.10.15-menu.1

246 testes locais passaram. O menu, atalhos, entradas de busca, listas paginadas, seleção do ID correto, filtros guiados com vírgula decimal, cancelamento, confirmação de remoção, bloqueio de callbacks repetidos e invalidação de cartões após remoção/reutilização do ID foram exercitados com objetos Telegram simulados. Entradas monetárias ambíguas como 1.500 são recusadas, sem virar R$ 1,50. O fluxo de promoções também testa retorno à seleção de lojas após informar CEP e permanência na entrada após percentual inválido. O modo de grupo verifica ForceReply seletivo ligado à mensagem do usuário autorizado e ausência de resposta automática para mensagens comuns sem entrada pendente.

Os testes não enviaram mensagens reais nem registraram comandos na API do Telegram. O registro do menu nativo é uma tentativa na inicialização; falha nesse registro mantém os botões inline disponíveis. Busca/preços/estoque das lojas não foram novamente validados nesta revisão. Os comandos existentes e as regras de comparação/agendamento são reutilizados; os estados temporários do menu ficam em memória.

# Atualização 2026.10.15-categorias.1

236 testes locais passaram, incluindo as verificações de seleção livre e navegação paginada.

O limite fixo Hardware/Placas-mãe foi removido da interface e da execução. O catálogo distribuído contém 215 links observados, agrupados em 201 categorias/subcategorias e 33 departamentos. Menus reais de KaBuM, Pichau e Terabyte foram consultados pelo Fetcher; a leitura de links não comprova extração de preços em todas essas categorias. As rotas anteriores de placas-mãe Amazon/Mercado Livre foram preservadas, com suas limitações.

Novos testes locais simulam paginação de botões, rejeição de botões antigos, seleção de Pets chegando à execução, categorias livres fora do catálogo, recusa de URLs não autorizadas, atualização/cache dos menus e preservação em caso de bloqueio. Duas fixtures adicionais são recortes reduzidos de navegação real; testes que as leem não fazem consultas de rede. O pacote Kali inclui category_seed.json.

Validação ao vivo separada, sem SQLite ou Telegram, em 15/10/2026:

- Pichau/Monitores: 1 página, 36 links descobertos, 2 produtos lidos com preço Pix, disponibilidade e referência anterior. Os valores observados foram 408999/588234 e 139999/235293 centavos (atual/anterior); o filtro >=30% foi aplicado sobre esses valores. Não são preços atuais garantidos.
- Pichau/Pets: 1 página, 36 links, 2 produtos com preços atuais de 7486 e 11174 centavos e disponibilidade declarada; sem referência anterior legível. Foram excluídos do filtro percentual, sem inventar desconto.
- Terabyte/Monitores: 1 página, 152 links reconhecidos pelo adaptador existente, leitura limitada a 1 produto. Preço atual 148999 centavos e disponibilidade declarada, mas sem referência anterior validada; não qualificou como promoção percentual. A contagem é de links reconhecidos, não de todo o estoque da loja.

A atualização automática dos menus foi validada com simulação e os mesmos marcadores HTML observados nas páginas reais; não houve envio real de botões ao Telegram nesta revisão. Pesquisa por termo é identificada como parcial e não se apresenta como varredura integral de categoria. As limitações de acesso e de referência anterior de cada loja continuam válidas.

# Atualização 2026.10.15-titulos.1

Títulos enviados em HTML com conteúdo dinâmico escapado. A divisão de mensagens ocorre antes da criação das tags e respeita unidades UTF-16, preservando emojis. A suíte inclui verificações de escape de nomes com `<`, `>` e `&`, divisão de textos longos e preservação do teclado/parse_mode. Exemplos de filtros explicam a combinação obrigatória de valor, percentual e alvo e não alteram os cálculos existentes. Os testes usam Telegram simulado; nenhum envio real ou nova consulta de loja foi realizado nesta atualização.

# Atualização 2026.10.15-editorial.1

Revisão de apresentação baseada no arquivo de templates enviado pelo usuário: ajuda, lista, histórico, cartões, botões, estados de leitura, alertas, erros e promoções. Os testes existentes foram ajustados às novas mensagens, preservando as verificações de preços, limites, autorização, duplicidade e persistência. As mensagens comuns continuam como texto simples, sem asteriscos de formatação; os resultados de promoções mantêm o título em HTML escapado. O envio alternativo para legendas longas foi preservado. Esta revisão não valida novamente o acesso às lojas nem envia mensagens reais no Telegram.

# Atualização 2026.10.15-promocoes.1

224 testes locais passaram. Os testes novos simulam filtros estritos/inclusivos, centavos, referências ausentes/zero/inválidas, parcelas, cupons sem reaplicação, ranking e deduplicação, comparação por identificadores e variantes, condições diferentes, falhas parciais, bloqueio de consultas duplicadas, autorização e callbacks antigos. O serviço manual é exercitado sem banco, agendador ou envio Telegram. Há teste de compartilhamento de uma leitura com o Monitor existente e de empacotamento do módulo/documentação para Kali.

As fixtures `kabum_category_real.html` e `pichau_category_real.html` são recortes de HTML real capturado nesta sessão, com apenas três links e a paginação; os testes que as leem são locais, não consultas de rede. O suporte genérico a StrikethroughPrice é simulado e não foi observado como fonte funcional de desconto nas demais lojas.

Validação ao vivo separada em 15/10/2026, por `scripts.diagnose_deals`, sem banco nem Telegram:

- Uma página de categoria KaBuM retornou 60 links; a Pichau retornou 36. O parâmetro `page_number=2&page_size=60` na categoria KaBuM foi conferido com paginação.current=2. A paginação Pichau veio de link real `?page=2`; não foi varrida toda a categoria.
- Primeira amostra: duas ofertas lidas por loja, nenhuma apta ao filtro >=30%. O resultado ficou vazio, sem completar com produtos fora do filtro.
- Segunda amostra: seis ofertas da KaBuM e seis da Pichau; foram lidos preços atuais Pix, disponibilidade e referências de/por, com uma referência ausente na KaBuM. Houve uma leitura complementar nova na KaBuM. A saída apresentou três ofertas ordenadas por desconto anunciado e marcou comparação não confirmada quando faltavam dados de identidade/condição. Exemplos observados nessa leitura: KaBuM TUF Gaming B550M-Plus de 116800 por 78999 centavos; Pichau MSI B550 Gaming WiFi6E de 164705 por 105699 centavos. Estes valores são evidência datada de leitura, não preços garantidos atuais.
- A Pichau exibiu referência de 1117646 centavos para uma placa com preço Pix de 81999 centavos. O desconto calculado superior a 90% recebeu o aviso de referência suspeita. Não foi apresentado como queda histórica comprovada.
- Terabyte falhou ao carregar a categoria com `browser_resource_refused`; Amazon falhou com `network_or_rate_limit`; Mercado Livre recusou robots.txt com HTTP 403 e gerou `robots_unavailable`. Nenhuma dessas falhas virou preço zero, desconto inventado ou alegação de consulta completa. O resumo informa as limitações específicas.

A interface Telegram nova foi testada com objetos simulados, sem envio de mensagens reais. Frete por CEP não está implementado, e a categoria inicial é somente Hardware > Placas-mãe. Extração completa de cupons/assinaturas e referências HTML não está validada em todas as lojas. Veja [PROMOCOES.md](PROMOCOES.md).

# Atualizacao 2026.10.15-amazon-offers.1

170 testes locais passaram. Validacao real separada do fluxo completo Monitor.read no ASIN Amazon B08KGVH7YC obteve preco 172711 centavos, vendedor Amazon Global com identificador explicito e condicao Novo no painel publico AOD. Frete separado nao foi usado como preco. Pagamento e estoque nao foram confirmados; a leitura nao e comparavel para alertas. Selenium normal carregou o painel com JavaScript, sem login, CAPTCHA, compras ou modificacao da automacao. A validacao ocorreu no Windows; o novo caminho Selenium Amazon ainda depende de verificacao na VPS.

A fixture amazon_aod_real.html e um recorte do DOM real, diferenciado dos testes simulados. Inclui somente titulo, condicao, bloco de preco e vendedor; forms, cookies e tokens nao sao incluidos. Os testes de integracao usam navegador simulado; nao enviaram Telegram.

# Atualizacao 2026.10.15-stores.1

157 testes locais passaram. Novos testes simulados cobrem fallback de sitemap incompleto, separacao de Aorus Elite/Elite AX/Gaming X, titulo real divergente da pesquisa, ordinais/capacidades e bloqueios Amazon. Duas fixtures reduzidas foram obtidas de paginas Amazon reais, sem dados de sessao: B550 indisponivel e Echo Dot com preco oculto.

Validacao ao vivo separada: Pichau leu o link fornecido pelo usuario com titulo, vendedor Pichau, NewCondition, Pix, preco e disponibilidade. KaBuM leu preco/Pix/vendedor/estoque mas nao condicao. Terabyte leu a oferta regular B550 como indisponivel, sem pagamento confirmado. Mercado Livre encontrou links, mas continua bloqueando a pagina. Amazon encontrou e leu paginas reais, mas o preco nao foi fornecido; B550 indisponivel e Echo com vendedor Amazon.com.br/estoque nao confirmado. Nao houve envio Telegram ou alteracao do banco do usuario.

Nao foi atingida a coleta completa de todos os campos em todas as lojas. Consulte STATUS-LOJAS.md para resultados e limites. Os registros abaixo descrevem versoes anteriores.

# Atualizacao 2026.10.15-ml-search.1

143 testes locais passaram. Os testes novos usam respostas simuladas da busca externa, verificando cache, limites, dominios permitidos, descarte de categorias/arquivos e de titulos incompatveis com o endereco, e entrega de links nao verificados sem criar ofertas ou monitoramentos.

Validacao real em 15/10/2026: a busca publica Tavily em modo oficial sem chave retornou HTTP 200 e cinco links Mercado Livre compativeis com Gigabyte B550 Aorus Elite V2 (incluindo variantes AX identificadas nos titulos). O fluxo real de geracao de mensagens tambem foi exercitado com SQLite em memoria, sem envio Telegram. Nao foram conferidos precos, vendedores ou estoque das paginas; o bloqueio 403 da loja continua. Esses links sao candidatos de indice externo, nao ofertas verificadas. Ver MERCADO-LIVRE.md.

Os registros abaixo descrevem etapas anteriores e suas respectivas validacoes.

# Validação executada em 15/10/2026

## Testes simulados

Executados no Windows, Python 3.11.9, ambiente virtual do projeto:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=data/pytest-final
```

Resultado final registrado após a execução da suíte. Todos os HTMLs e preços de `tests/` são **sintéticos**; não são fixtures extraídas das lojas e não representam ofertas reais.

Cobertura: preço inicial sem alerta, queda, repetição do preço, novo episódio, vendedor/condição/pagamento diferentes, preço inválido, falha sem apagar preço válido, estoque desconhecido/indisponível, mudança de modelo, confirmação pendente, filtros de reais/porcentagem/alvo, dados estruturados incompletos, JSON corrompido, AggregateOffer, reinício SQLite, remoção em cascata, entrega concorrente e falha de envio. Testes adicionais cobrem concorrência de consulta, agendamento persistido e bloqueio de instância.

A importação de `monitor.__main__` com python-telegram-bot instalado também foi executada, sem inicializar polling e sem usar token.

## Sondagem real pelo código

Comando: `python -m scripts.probe_stores`. Uma página do modelo foi consultada por loja, incluindo robots.txt, sem browser, sem credenciais e sem contornar bloqueios. O JSON resumido fica em `data/probe-results.json` e pode ser regenerado. Nenhum preço coletado foi usado como exemplo ou teste de comparação.

| Loja | Resultado observado | Limitação |
| --- | --- | --- |
| KaBuM | Parser encontrou um Product/Offer e preço; disponibilidade estruturada indicou indisponível. | JSON-LD não forneceu vendedor, condição ou pagamento ao extrator. Comparação desabilitada. |
| Pichau | `blocked_no_bypass` | Acesso HTTP bloqueado; nenhum seletor específico validado. |
| Terabyte | `robots_unavailable` | Não foi possível obter regras de acesso; consulta recusada. |

URLs sondadas estão declaradas em `scripts/probe_stores.py`. Uma sondagem não valida estabilidade da loja, todas as variantes de oferta nem vendedor marketplace. O fato de a página aparecer em uma ferramenta de navegação externa não demonstra que o extrator HTTP consegue acessá-la.

**Nenhuma loja foi validada de ponta a ponta para alertas reais.** Os adaptadores específicos herdam um parser genérico de Schema.org. Será necessária adaptação por loja com evidência de vendedor, condição, pagamento e disponibilidade quando esses dados não existirem no JSON-LD. Não há seletores inventados nem promessa de alertas para páginas incompletas.

## Não executado

- Polling/entrega real do Telegram: token fornecido não foi usado; falta configurar ID pessoal do usuário e novo token.
- Brave Search autenticado: falta chave da API. Implementação segue a documentação pública, sem teste real autenticado.
- Playwright/Chromium em lojas: navegador opcional não instalado nem validado.
- Deploy em Debian/systemd: arquivos e instruções fornecidos; serviço não foi iniciado nesta máquina Windows.

## Referências consultadas

- [KaBuM: página sondada](https://www.kabum.com.br/produto/398852/placa-mae-asus-rog-strix-b550-f-gaming-wifi-ii-amd-m-2-ddr4-90mb19v0-mvaay0)
- [Pichau: página do modelo](https://www.pichau.com.br/placa-mae-asus-rog-strix-b550-f-gaming-wi-fi-ii-ddr4-socket-am4-atx-chipset-amd-b550-rog-strix-b550-f-gaming-wifi-ii)
- [Terabyte: página do modelo](https://www.terabyteshop.com.br/produto/20306/placa-mae-asus-rog-strix-b550-f-gaming-wi-fi-ii-chipset-b550-amd-am4-atx-ddr4-90mb19v0-m0eay0)
- [python-telegram-bot ApplicationBuilder](https://docs.python-telegram-bot.org/en/stable/telegram.ext.applicationbuilder.html)
- [Brave Web Search API](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started)
- [Schema.org Offer](https://schema.org/Offer)


## Atualizacao: selecao com foto

Suite ampliada: **47 testes simulados passaram** em 2,43 segundos (`--basetemp=data/pytest-selection-final`). Inclui extracao de imagem do Product, rejeicao de URLs inadequadas, envio de foto via bot simulado, fallback textual, botao vinculado ao titulo/URL, autorizacao de usuario e grupo, confirmacao somente da oferta clicada, repeticao sem nova consulta, botao obsoleto/removido, migracao aditiva de banco anterior e reenvio dos candidatos pendentes. Os 32 testes anteriores continuam passando.

Nenhuma imagem foi enviada ao Telegram real nem houve nova validacao de lojas nesta atualizacao. A foto real depende dos metadados fornecidos pela pagina e de o Telegram conseguir carregar a URL. `/buscar` continua textual; cartoes de escolha com foto sao usados em `/monitorar` e `/opcoes`.

Referencias da interface: [CallbackQueryHandler](https://docs.python-telegram-bot.org/en/stable/telegram.ext.callbackqueryhandler.html) e [Bot.send_photo](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html#telegram.Bot.send_photo).


## Diagnostico de busca sem chave

Confirmado localmente que SEARCH_API_KEY estava vazio, sem exibir credenciais. A busca por nome agora valida configuracao antes de criar outro produto, explica a variavel ausente e diferencia chave recusada, provedor desativado e indisponibilidade. Cadastros existentes continuam preservados. Suite: **53 testes simulados passaram** em 2,50 segundos; nenhuma consulta autenticada Brave ou envio real Telegram foi realizado.


## Busca direta nas lojas (atualiza??o sem API externa)

`SEARCH_PROVIDER=direct` implementado e ativado no `.env` e em `.env.example`. Nenhuma chave externa ? exigida nesse modo; Brave permanece opcional. A busca direta respeita o mesmo Fetcher, robots.txt, limite de acesso e pol?tica contra bloqueios. Nenhuma chamada ao Telegram real foi efetuada.

**Execu??o real:** `python -m scripts.probe_search b550` descobriu seis URLs de produto KaBuM. N?o foram usados pre?os do cat?logo como pre?os de oferta. `python -m scripts.probe_search Placa Mae Asus ROG STRIX B550-F GAMING WIFI II` n?o retornou candidato compat?vel. O HTML da consulta mais espec?fica continha modelos de outros chipsets, rejeitados pelo filtro. Isso n?o prova que o modelo deixou de existir; a busca pode omitir indispon?veis ou exigir outra consulta. N?o h? pagina??o nem varredura ilimitada.

Nas duas sondagens, **Pichau foi bloqueada** (`blocked_no_bypass`), e **Terabyte n?o permitiu obter robots.txt** (`robots_unavailable`). N?o se tentou contornar essas condi??es. A rota p?blica da Terabyte foi observada em p?ginas indexadas, mas o extrator de links dessa loja s? teve valida??o simulada. Para Pichau n?o se inventou uma rota: o c?digo tenta descobrir um formul?rio GET real e, se n?o conseguir, informa a limita??o.

Relat?rios locais: `data/direct-search-b550.json` e `data/direct-search-probe.json`. O script pode regenerar o ?ltimo relat?rio sem credenciais. Snapshot reduzido de tr?s itens de cat?logo KaBuM, obtido em 15/10/2026, inclu?do em `tests/fixtures/kabum_catalog_real.html`, com proced?ncia no README da pasta. Esse teste usa nomes e URLs reais; os pre?os e demais dados foram removidos.

Suite executada: **64 testes passaram** em 3,36 segundos. S?o 63 testes com dados simulados e um teste de extra??o do snapshot reduzido real. Novas verifica??es incluem aus?ncia de chamadas ? API externa no modo direto, deduplica??o, rejei??o de outro chipset, formul?rio GET observado, cat?logo corrompido, bloqueio de uma loja preservando resultados de outra e falta de suporte a nova loja. Nenhum desses testes valida alertas reais nem estabilidade futura das p?ginas.

A leitura de vendedor, condi??o e pagamento nas ofertas continua limitada como documentado; a descoberta direta n?o resolveu essas limita??es. Reinicie o processo para carregar o novo provedor.


## Correcao dos campos KaBuM e apresentacao

Em 15/10/2026 foram consultadas, pelo Fetcher e sem Telegram, as paginas KaBuM dos produtos 692460 (loja propria) e 683504 (marketplace). O HTML real revelou `pageProps.product.sellerName` respectivamente como KaBuM! e GIGANTEC, identidade do produto e paragrafo com preco e rotulo Pix. O parser corrigido foi executado sobre esses HTMLs reais e identificou o vendedor e Pix em ambos. A condicao permaneceu ausente em ambos e `comparable=False`, comportamento intencional. Nao houve emissao de alerta real nem validacao de comparacao real completa.

Foram incluidos dois snapshots reais reduzidos em `tests/fixtures/kabum_offer_*_metadata.json`, somente com ID, titulo, vendedor e flags; sem precos, descricao ou outros dados. As quantias nos testes unitarios de Pix sao sinteticas. A validacao com HTML real completo ficou local em `data/` e nao integra o pacote.

Suite: **78 testes passaram** em 3,19 segundos. Tres testes usam metadados de snapshots reais (um de catalogo e dois de vendedores); os demais usam dados simulados, inclusive quantias, envio de fotos, falhas e robots.txt. Novos testes verificam identidade de produto antes de enriquecer, preco visivel divergente, Pix no rodape, condicao ausente mesmo com isOpenbox=false, modalidade com condicao explicita, normalizacao de www, envio/fallback de foto e regras robots com curingas/ancoras/prioridades. Nenhuma mensagem foi enviada ao Telegram real nesta validacao.

O `/buscar` agora tem fotos quando disponiveis (substitui a limitacao textual descrita em atualizacoes anteriores), rotulos de estoque em portugues, motivos de suspensao da comparacao e resumo unico dos avisos de lojas. Amazon continua sem adaptador de busca direta. Os bloqueios HTTP da Pichau e do robots.txt local da Terabyte continuam sem solucao automatica. A ferramenta web conseguiu consultar [robots.txt da Terabyte](https://www.terabyteshop.com.br/robots.txt), que proibe `/busca` para User-agent generico, e [robots.txt da Pichau](https://www.pichau.com.br/robots.txt), que inclui restricao a URLs com query. Essas consultas externas nao foram utilizadas para ignorar a politica de acesso do Fetcher local.


## Medalhas dos menores valores na busca

Suite: **82 testes passaram** em 3,15 segundos. Quatro testes adicionais, inteiramente simulados, verificam ordenacao e medalhas das tres primeiras faixas de preco, ausencia de medalha no quarto valor, empates, separacao de Pix/cartao/condicao, exclusao de preco invalido e estoque nao confirmado, ranking provisorio para condicao ausente e deduplicacao por URL/modalidade. Nenhuma mensagem real foi enviada. A busca passou a reunir leituras antes de enviar para calcular as posicoes; os alertas historicos nao foram alterados.

## IDs de anúncios, abrangência e qualquer alteração

Suíte final: **92 testes passaram** em 3,38 segundos. Esta atualização usa dados simulados: IDs persistentes e estáveis após busca/reinício; ausência de acompanhamento antes da escolha; dois botões de abrangência; rejeição de usuário não autorizado; primeiro clique prevalecendo; ausência de duplicação na mesma abrangência; exclusão preservando catálogo; botão antigo; identidade alterada criando novo ID; consulta exclusiva da URL no modo site; busca multiloja mantendo origem; identificadores conflitantes recusados; variantes ambíguas aguardando confirmação; GTIN com checksum e MPN/marca; migração preservando agenda/pausa; aumento/queda/repetição/falhas e modo quedas opcional.

Nenhum envio real Telegram ou ciclo de cinco horas foi executado nesta atualização. A identificação entre lojas foi validada somente com dados sintéticos. Os bloqueios e limitações reais registrados anteriormente permanecem; condição ausente continua suspendendo alertas, inclusive no modo todas. O catálogo de anúncios é persistido, mas somente a escolha da abrangência ativa um acompanhamento. IDs antigos de produtos não são reinterpretados como anúncios: use o Anúncio ID exibido por uma nova busca ou oferta atualizada. Os acompanhamentos não expiram nem terminam após alertar.

## Pacote Kali Linux por SSH

Arquivo `monitor-precos-kali.tar.gz`, gerado por `scripts/build_kali_package.py`. Inclui instalador Bash, dependências de execução sem navegador/test runner, serviço systemd, documentação de terminal e exportador SQLite. Não inclui `.env`, tokens, banco do usuário, ambiente virtual Windows ou caches. O tar normaliza arquivos para UTF-8/LF e marca o instalador como executável. A soma SHA-256 acompanha o pacote.

**95 testes passaram** em 3,65 segundos. Três testes adicionais verificam exportação de snapshot com origem em WAL sem sobrescrever arquivos, origem inexistente sem criar banco vazio e estrutura segura do tar com exclusão de dados/credenciais, caminhos relativos e permissões Unix. Sintaxe do instalador verificada com `bash -n` no Git Bash do Windows. O teste de pacote foi executado com a fonte local; não é teste de instalação Linux.

**Não executado em Kali real:** APT, criação de usuário Linux, instalação de dependências nesse sistema, serviço systemd, autenticação do bot ou execução contínua no servidor. O instalador usa venv, conforme documentação oficial do Kali sobre Python externally-managed, e valida configuração local sem exibir credenciais. A confirmação funcional exige resposta ao `/ajuda` no servidor. A migração do banco é opcional e deve ser feita antes de o servidor possuir um banco próprio. O bot do Windows deve estar parado antes de usar o mesmo token no servidor.

## Descoberta por sitemap: Pichau e Terabyte

Atualização sem Selenium e sem novas dependências: a descoberta da Pichau usa `/media/sitemap.xml`; a Terabyte usa `/sitemap-manus.xml` e `/sitemap.xml`, sem consultar `/busca`. A mesma política de robots.txt, intervalo, domínio, rede e CAPTCHA continua obrigatória. O navegador não é usado como fallback para restrições.

**Sondagem real em 15/10/2026:** o Fetcher leu o sitemap público da Pichau com 18.692 URLs e localizou dois links do modelo B550-F GAMING WIFI II. A consulta pelo novo fluxo produziu cinco candidatos, dois correspondendo ao nome completo e três variantes que continuam exigindo conferência. A página do primeiro modelo exato ainda retornou `blocked_no_bypass`. Assim, a descoberta da Pichau foi validada, mas a leitura de oferta dessa loja continua bloqueada no ambiente local. Na Terabyte, o Fetcher continuou retornando `robots_unavailable`; o novo caminho de sitemap dessa loja só foi validado com simulação.

Snapshot reduzido de duas URLs reais da Pichau em `tests/fixtures/pichau_sitemap_real.xml`; não inclui preço, estoque ou imagem. O parser usa somente elementos loc diretos, descarta imagens e XML inválido/DTD/entidades. Índices têm limite de quatro documentos e 50 mil URLs, cache de cinco horas e checagem do domínio de cada endereço. Isso não garante cobertura de todo o catálogo. Links encontrados continuam sendo lidos nas páginas antes de gerar preço, histórico ou alerta.

Os novos testes verificam XML, cache, filtros, índices limitados, rejeição de domínios externos, nenhuma chamada à rota proibida, e nenhuma tentativa de browser ao encontrar robots/403/CAPTCHA. Há também um teste com o snapshot real reduzido. A versão gerada para Kali inclui o novo módulo e as fixtures XML; nenhuma instalação no servidor ou mensagem real do Telegram foi executada nesta atualização.

Resultado final desta atualização: **104 testes passaram** em 4,87 segundos. Quatro testes da suíte usam snapshots reais reduzidos (catálogo KaBuM, dois vendedores KaBuM e sitemap Pichau); preços, alertas e envios continuam simulados. A coleta completa de ofertas Pichau/Terabyte não foi validada como funcional.

## Correção de transporte Chromium e CAPTCHA de avaliações

Versão **2026.10.15-browser.1**. Os avisos genéricos relatados pelo usuário motivaram uma sondagem com Chromium real. O acesso com Chromium comum, sem stealth, proxy, credenciais ou resolução de CAPTCHA, retornou HTTP 200 no robots.txt, sitemap e página da Pichau e no robots.txt/sitemaps da Terabyte. O transporte de produção foi adaptado para usar esse acesso nessas duas lojas quando `PLAYWRIGHT_ENABLED=true`; a KaBuM continua em HTTP. Cabeçalhos de compressão e tamanho são removidos ao converter o texto já descomprimido pelo navegador, corrigindo um `DecodingError` real da integração inicial.

Na Terabyte, a página pública continha um input `g-recaptcha-response` do formulário de avaliações. Não era uma barreira de acesso ao produto. O detector anterior tratava qualquer ocorrência como bloqueio; agora distingue uma página com dados Product/Offer já disponíveis de uma página de desafio. O robô não resolve nem interage com o widget. Títulos/páginas de desafio continuam recusados, e recursos de desafio não são executados. Robots.txt, domínios, endereços públicos, limites e tempos de espera continuam sendo conferidos. Nenhum disfarce de User-Agent foi usado: o navegador se identifica como PriceMonitor.

**Sondagem final real, usando o código de produção**, em `data/browser-exact-product-validation.json`:

- Pichau: URL da Gigabyte B550 Aorus Elite V2 terminada em `b550-aorus-elite-v2`; preço da modalidade Pix lido, vendedor Pichau, condição NewCondition, InStock e leitura comparável. O JSON-LD continha outro valor, sem modalidade; o adaptador passou a usar o bloco de preço à vista associado explicitamente ao rótulo Pix, sem atribuir Pix ao valor genérico.
- Terabyte: `/produto/16143/placa-mae-gigabyte-b550-aorus-elite-v2-chipset-b550-amd-am4-atx-ddr4`; página lida, vendedor TerabyteShop, NewCondition e OutOfStock. O campo visual zero não virou preço válido. Sem modalidade atual suficiente, a leitura não gera alerta.
- A descoberta por sitemaps das duas lojas retornou URLs sem avisos de bloqueio nessa execução. Outros resultados podem incluir variantes; seleção e identidade continuam necessárias. Não se garante acesso futuro nem cobertura de todos os produtos.

Dois snapshots HTML reais reduzidos foram adicionados em `tests/fixtures/pichau_product_browser_real.html` e `terabyte_product_browser_real.html`, preservando apenas JSON-LD relevante e os blocos usados na extração. Eles contêm quantias capturadas na sondagem datada, sem representar ofertas atuais. O restante da página, avaliações e descrições foi removido. Os demais testes novos simulam o navegador e respostas comprimidas, sem rede.

O instalador Kali aceita `--with-browser`, preserva credenciais/dados, configura pastas graváveis e verifica se o navegador inicia como usuário do serviço. Foi verificada a sintaxe Bash, mas não foram executados APT, systemd ou Chromium no Kali real. O `/status` informa versão e configuração; `scripts.diagnose_stores` permite verificar acesso a partir do próprio servidor sem expor tokens e sem enviar Telegram. Não houve alerta real enviado durante a validação.

Suíte final da versão 2026.10.15-browser.1: **117 testes passaram** em 5,29 segundos. Inclui testes com os dois novos recortes reais de produto e testes simulados de compressão, CAPTCHA bloqueante versus widget opcional, separadores monetários, roteamento Chromium por loja, fechamento do contexto e recusa por robots. A sintaxe Bash do instalador com `--with-browser` passou em `bash -n`. A sondagem final foi novamente executada contra as URLs exatas de Elite V2 da Pichau/Terabyte com o transporte de produção, sem erros de acesso e sem avisos da descoberta por sitemap; estoque indisponível na Terabyte foi preservado. Nenhum alerta Telegram foi enviado; nenhuma instalação Kali remota foi executada.
# Mercado Livre — 2026.10.15-marketplace.1

HTTPX e Chromium comum retornaram 403 para robots.txt nos hosts www, lista e produto a partir deste ambiente. Nenhuma oferta real ou formulario real do Mercado Livre foi validado; a descoberta usa apenas formularios e links efetivamente presentes na resposta permitida. O adaptador e experimental e pode exigir adaptacoes quando houver acesso real. Os testes novos usam exclusivamente HTML/Schema.org inventados para simulacao, explicitamente identificados no arquivo de teste. Verificam separacao de vendedores/condicoes/pagamentos, recusa de catalogos, dados ausentes, hosts autorizados e distribuicao do limite entre quatro lojas.

# Atualizacao 2026.10.15-browser.2

126 testes locais passaram. Os novos testes simulam timeout e interrupcao de conexao do Chromium, verificam retentativas e garantem que CAPTCHA/bloqueio nao sejam repetidos como erro temporario. Tambem verificam o resumo final de pesquisas com sucesso, erro de leitura ou falha de descoberta.

Em 15/10/2026, os tres links Pichau relatados (B550 Aorus Elite AX V2, Aorus Elite V2 e Gaming X V2) foram lidos pelo Fetcher real com Chromium no Windows. Foram extraidos titulo, modalidade Pix e disponibilidade declarada. A Aorus Elite V2 redirecionou para seu endereco atual. Nao houve envio real ao Telegram nesse teste.

Nao foi reproduzido o acesso pela VPS Kali do usuario: disponibilidade local nao comprova acesso a partir do IP da VPS. As mensagens agora exibem motivos conhecidos sem detalhes internos ou credenciais; timeouts e conexoes interrompidas recebem ate tres tentativas. Bloqueios e CAPTCHA continuam interrompendo a leitura. Sem o motivo produzido na VPS nao e possivel afirmar a causa original.

# Correções do relatório de promoções — 15/10/2026

Resumo de cobertura separado dos avisos por loja, sem duplicação de ícones ou do rótulo de comparação. Links de catálogo do Mercado Livre são descartados antes de consultar uma oferta individual. Referências com desconto anunciado de 70% ou mais continuam sinalizadas como suspeitas; não representam queda histórica comprovada.

Novos testes simulam o relatório com avisos repetidos e a descoberta de links de catálogo junto de anúncios individuais. Não houve validação adicional em lojas reais nem envio ao Telegram nesta alteração. Bloqueios e restrições das lojas permanecem limitações explícitas.

# Atualização 2026.10.16-ddr4.1

Corrigida a conversão de cabeçalhos do Chromium para HTTPX: valores com acentos causavam UnicodeEncodeError na Terabyte. Falhas em recursos opcionais não escondem o motivo de uma falha na navegação principal. Restrições de acesso continuam preservadas.

DDR4 usa o contexto de memória RAM nas buscas por termo e a categoria geral de RAM já observada na KaBuM, com filtro explícito de geração no título. DDR5, títulos sem geração declarada e acessórios identificados não qualificam. Não foram inventadas rotas de categoria para outras lojas.

O envio ao Telegram respeita RetryAfter, repetindo apenas o trecho recusado. Falhas de entrega são diferenciadas de falhas da consulta. Erros de DNS/conexão de uma loja são tratados sem interromper as demais. Os avisos de leitura mostram motivos conhecidos, sem incluir mensagens brutas de exceções.

Validação real local em 16/10/2026: consulta limitada a uma página e um produto por loja. KaBuM descobriu 60 links e leu uma memória XPG DDR4, R$ 568,99, referência R$ 682,34, disponível. Pichau leu uma Corsair DDR4, R$ 339,69, indisponível, sem referência anterior válida. Após corrigir os cabeçalhos, Terabyte descobriu 63 links e leu uma Spectrum Blitz DDR4, R$ 399,99, disponível, sem preço anterior válido. Valores são capturas pontuais e podem mudar. O filtro >99 usado nesses diagnósticos evitou qualificar ofertas ou iniciar comparações complementares; não houve envio ao Telegram.

Amazon falhou no painel de opções de compra. Mercado Livre retornou catálogos nos links examinados; não houve validação de preço de anúncio individual. Essas duas integrações permanecem parciais. Não foi testado o acesso pelo IP da VPS Kali. Testes automatizados adicionais simulam limitação de mensagens, falha de entrega, DNS, recursos opcionais e cabeçalhos com acentos.

# Atualização 2026.10.16-offers.1 — links AJAZZ informados pelo usuário

266 testes automatizados passaram, incluindo capturas reduzidas e simulações. Os testes de envio ao Telegram usam substitutos locais, sem envio real.

Os cinco links exatos foram consultados localmente, com o mesmo Monitor/Fetcher usado pelo bot, sem Telegram e sem banco. Os dois anúncios da Pichau foram lidos: AK820 preto, R$ 219,99 Pix, e AK820 Pro branco/azul, R$ 419,99 Pix; ambos indisponíveis. O primeiro redirecionou para o endereço atual da loja. A Terabyte retornou AK820 Pro branco/roxo, R$ 569,90, indisponível, sem modalidade explícita. Foram incluídos recortes dessas capturas como testes de regressão. Esses preços são registros pontuais de 16/10/2026 e podem mudar.

O bloqueio Pichau e as falhas internas da VPS não foram reproduzidos localmente. Não há acesso SSH ao servidor nesta sessão, portanto não foi corrigido nem validado o acesso pelo IP da VPS. A resolução DNS agora recebe três tentativas com espera progressiva e falha com motivo específico, sem remover a verificação de endereços públicos.

Nos links Amazon não houve validação de preço. O navegador Selenium local apresentou encerramento de aba (`tab crashed`), agora classificado separadamente de falhas de instalação, conexão e timeout do painel. A execução Linux recebe a opção padrão disable-dev-shm-usage para ambientes com memória compartilhada pequena; isso não foi validado na VPS e não resolve todo tipo de encerramento do Chrome. Uma captura HTTP do AK820 e a consulta final do AK820 Pro mostraram que a loja exige adicionar ao carrinho para revelar detalhes/preço. O leitor reconhece o aviso dentro do bloco principal observado e não inicia ação de compra. Uma consulta final do primeiro link retornou apenas título e campos parciais, sem preço: não equivale a uma oferta com preço validado.

O resumo de buscas diferencia conclusão com limitações e informa quantas ofertas enviadas tiveram preço lido. Exceções internas registram apenas o tipo no log. O novo `scripts.diagnose_offers` consulta links exatos e informa motivos e posições do código sem enviar mensagens nem alterar dados. Os testes adicionais de classificação de erro, DNS e credenciais rejeitadas são simulações; os testes dos recortes reais não executam rede.

# Atualização 2026.10.16-access.1 — Logitech e bloqueios por loja

Consulta real local dos dois links informados em 16/10/2026, com o transporte Chromium de produção: Logitech G213 Prodigy, R$ 419,99 Pix, indisponível; Logitech G PRO GX Blue, R$ 639,99 Pix, disponível segundo a página. O bloqueio relatado na VPS não foi reproduzido neste ambiente; essas leituras não validam acesso pelo IP da VPS nem garantem consultas futuras.

Após 401/403 ou CAPTCHA, o Fetcher suspende novas consultas àquela loja por 15 minutos. A pausa fica em memória e expira automaticamente; não afeta outras lojas e não tenta contornar a recusa. A primeira recusa continua sendo informada. O diagnóstico de links exatos agora inclui status HTTP das páginas e transporte usado para distinguir HTTP de Chromium.

Catálogos e links externos sem preço ficam agrupados por loja depois dos anúncios efetivamente lidos. Não são salvos como ofertas ou usados em alertas. Resumos com esses links ou avisos passam a indicar conclusão com limitações. Não houve validação de preços do Mercado Livre nesta alteração; agrupar links não implementa uma nova integração de preços.

268 testes automatizados passaram. Novos testes simulam bloqueio 403, ausência de repetição durante a pausa, continuidade em outra loja, expiração e agrupamento de seis catálogos sem consulta nem gravação de oferta. Nenhuma mensagem real ao Telegram foi enviada.

# Atualização 2026.10.16-mpn.1 — descoberta pelo código do fabricante

273 testes automatizados passaram; envio Telegram foi simulado.

O acompanhamento em outras lojas passa a pesquisar marca e MPN declarados quando disponíveis. Como auxílio de descoberta, títulos Logitech com o padrão 920-NNNNNN geram uma consulta curta pelo código, preservando o título e os identificadores originais. A seleção de candidatos reconhece o mesmo código explícito apesar de descrições comerciais diferentes e rejeita códigos diferentes e acessórios. Um código extraído apenas do título não é inserido como MPN verificado nem confirma automaticamente anúncios entre lojas.

Validação real local em 16/10/2026: o título longo da KaBuM fornecido pelo usuário encontrou via busca direta de produção o link exato da Pichau 920-011902; a página foi lida, R$ 1.129,99 Pix, novo, disponível, vendido pela Pichau. O anúncio KaBuM 585201 foi lido a R$ 999,99 Pix, disponível, com marca Logitech G; essa leitura não declarou MPN/condição suficientes para uma comparação automática. Não houve envio Telegram nem acesso SSH à VPS. O bloqueio relatado da VPS continua dependente de validação naquele IP, e a alteração não elimina recusas HTTP da loja.

O acompanhamento agora traduz motivos de falha, inclui loja e link, apresenta estoque em português e formata reais com vírgula. Leituras incompletas identificam os campos ausentes. Códigos técnicos continuam gravados no SQLite para diagnóstico, sem substituir o último preço válido.

Os testes simulam consulta por MPN, títulos diferentes com o mesmo código, código divergente, acessórios, ausência de confirmação automática, preservação de preço após bloqueio e indicação dos dados faltantes. As consultas reais acima são separadas desses testes sem rede.

# Atualização 2026.10.16-amazon-variant.1

O link Amazon B0BRSQCZLS enviado pelo usuário abriu localmente a variante branca Logitech G PRO X 60, com número da peça 920-011921, diferente do produto preto 920-011902 acompanhado anteriormente. A tabela principal declarou marca Logitech G, ASIN B0BRSQCZLS e código 920-011921 em Número do modelo/Número da peça. O preço não foi disponibilizado na resposta pública; o bloco principal pediu adicionar o produto ao carrinho. Não foi feita ação de compra. A busca real pelo código 920-011902 no índice consultado não encontrou candidato Amazon compatível nesta execução; isso não prova inexistência.

O adaptador lê marca e MPN da tabela de detalhes observada somente quando o ASIN da tabela corresponde ao URL. Não usa tabelas de recomendações, não transforma o número do modelo em MPN e recusa conflitos com identificadores estruturados. Nenhum preço foi inventado. 275 testes passaram, incluindo recorte dessa captura real e testes simulados de rejeição de ASIN incorreto, tabela fora do bloco principal, MPN divergente e conflito com dados estruturados. Não houve envio real ao Telegram nem teste pela VPS.

# Revisão 2026.10.16-review.1 — relatório Logitech G PRO

291 testes passaram. `pip check` não encontrou dependências incompatíveis; `compileall` de monitor/scripts passou. Foram incluídos testes de importação em processos Python novos: uma dependência circular Mercado Livre/discovery estava escondida pela ordem de importação da suíte e foi removida. Testes também cobrem rejeição de marcas e famílias incompatíveis, descarte sem gravação/alerta, modalidade à vista vinculada a produto e preservação das regras de preços.

Defeito reproduzido: palavras genéricas permitiam Corsair/SuperFrame e outros Logitech na consulta G PRO. Agora a marca solicitada é obrigatória para as marcas reconhecidas; G PRO precisa aparecer como família e G PRO X é tratado separadamente. Leituras de páginas redirecionadas também são filtradas no acompanhamento. Incompatibilidades são contadas como descartes, sem virar erros de leitura nem anúncios salvos. Isso não equivale a um classificador universal de marcas e modelos.

Terabyte: HTML real do Corsair K65 Pro Mini apresentou título SEO diferente do h1, modalidade dois níveis acima do valor e um segundo id valVista com preço zero dentro de modal de compartilhamento. O leitor vincula os títulos pelo MPN/marca e URL da oferta; considera o bloco principal e ignora o modal observado. Consulta real final leu R$ 649,99, novo, disponível, nas modalidades Pix e Boleto. O preço anterior R$ 965,90 foi validado no bloco de/por dessa mesma captura; testes impedem usar preços riscados de recomendações e valores ambíguos. A porcentagem é calculada e não depende do selo arredondado da loja. Outros layouts continuam limitados.

Busca real local com as cinco lojas e a consulta exata do relatório: KaBuM descobriu um candidato G PRO e leu R$ 699,99 Pix, disponível, condição não declarada. Pichau descobriu seis candidatos da família e leu o primeiro, G PRO 920-009388, R$ 639,99 Pix, novo, disponível. Terabyte não descobriu candidato compatível na fonte limitada; não se afirma ausência do produto. Mercado Livre retornou seis links e a tentativa de ler o primeiro foi interrompida por robots indisponível. Amazon retornou dois links e o primeiro exigiu carrinho para revelar preço. Não houve preço validado nessas duas últimas lojas. São capturas locais de 16/10/2026, não preços garantidos nem validação da VPS.

Também foi executado o fluxo real deliver_search com descoberta/leitura nas cinco lojas, banco SQLite exclusivo em data e Telegram substituído por coletores locais: nenhum produto monitorado ou alerta foi criado. Esse ensaio revelou a necessidade adicional de excluir G515/G915, depois corrigida e conferida nos testes e na descoberta real final. O banco do usuário não foi aberto nem alterado. Não houve envio real ao Telegram nem implantação SSH. Bloqueios por IP, preço oculto e condição ausente permanecem limites explícitos: não foi validado funcionamento completo de todas as lojas.

