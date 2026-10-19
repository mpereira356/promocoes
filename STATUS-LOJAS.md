# Brastemp oficial - 2026.10.19-brastemp.1

Loja oficial integrada com validacao real local. BVR28PB 110V/220V: HTTP 200,
364900 centavos, disponivel; bandeira explicitamente identificada para o total
a vista no cartao, sem inferir Pix. EANs e voltagens diferentes preservados.
BVR28NB: 595900 centavos, indisponivel; BVR28NK: 480900 centavos, indisponivel.
Busca real por sitemap encontrou dois links; categoria vertical tambem consultada.
Preco generico de item indisponivel nao significa oferta compravel nem gera alerta.
Valores pontuais; nao houve execucao na VPS. Ver LOJAS-FREEZERS.md.

# Freezers - 2026.10.19-freezers.1

Frigelar: descoberta real de seis links pelo sitemap, quatro produtos lidos em
HTTP 200. EOS kit8956: 248900 centavos, disponivel; Consul kit1199: 179308,
indisponivel; Metalfrio kit9338: 769900, indisponivel; Brastemp kit9543: 440900,
indisponivel. Valores pontuais, genericos; vendedor e pagamento ausentes.
Shopee: HTTP 200 sem oferta estruturada, inclusive com Chromium. Nenhum preco
real validado. Magalu: HTTP 403 na busca e no produto. Ver LOJAS-FREEZERS.md.
Nenhum contorno de bloqueio ou envio ao Telegram; validacao local, nao na VPS.

# Rechecagem B550 AX V2 - 2026.10.18-monitor-all-stores.1

KaBuM 473028: HTTP 200, R$ 1.439,00 no Pix, vendedor GIGANTEC, estoque
disponivel. Amazon B08KGVH7YC: HTTP 503 em tres tentativas. Pichau: HTTP 403.
Nao se afirma que todas as lojas retornam precos. Monitoramentos all recuperam
links compativeis de anuncios conhecidos para releitura independente da
descoberta externa, e exibem resumo por loja; isso nao contorna bloqueios.
Teste real local, sem execucao na VPS nem envio ao Telegram.

# Sensetup OpenBox - 2026.10.18-network-diagnostics.1

Rechecagem local real: 13 leituras HTTP de sete produtos nas tres lojas de
cadeiras tiveram preco. A08 Premium OpenBox respondeu cinco vezes com
R$ 1.590,00 e estoque indisponivel. Os valores sao capturas pontuais.
A falha de rede/limite observada na VPS nao foi reproduzida aqui.
Foram corrigidas a falta de pausa por loja apos 429 persistente e a perda
dos detalhes das tentativas ao esgotar as retentativas. Causa original na
VPS permanece nao identificada; nao se afirma disponibilidade garantida.
452 testes passaram; erros de transporte e entrega Telegram foram simulados.

# Lojas de cadeiras - 2026.10.18-chair-stores.1

Validacao HTTP real local em 18/10/2026, usando Fetcher/DirectSearch/Monitor,
sem cookies de conta, sem navegador e respeitando robots e intervalos:

| Loja | Produto testado | Preco capturado | Descoberta | Categoria consultada |
| --- | --- | --- | --- | --- |
| Sensetup | A08 Premium | R$ 2.100,00 | Sitemap publicado | 1 pagina, 13 links de produtos |
| Elements | Galatea | R$ 2.887,78 | Sitemap publicado | 1 pagina, 18 links; proxima pagina detectada |
| Flexform | Uni All Grey | R$ 1.030,50 | Formulario GET term | 1 pagina, 16 links de produtos |

Esses valores sao capturas pontuais, nao garantias de preco atual. As buscas
foram limitadas ao sitemap configurado (ate 4 documentos) ou a uma pagina de
busca; nao se afirma cobertura de todo o catalogo. Na Sensetup tambem foi
descoberto o link OpenBox, sem classificar automaticamente sua condicao.

Sensetup/Elements publicam variants com cores e estoques diferentes: preco
unico somente quando todas as variantes selecionadas tem o mesmo preco.
Parametro variant seleciona apenas o ID existente no proprio produto. Sem
selecao, estoques divergentes sao desconhecidos; precos divergentes ficam
como referencia a partir de e nao como preco individual confirmado.

Pagamento, condicao e vendedor nao foram declarados suficientemente nas
capturas Shopify e permanecem desconhecidos. Na Flexform, estoque e condicao
vieram do Product, mas pagamento/vendedor nao. Isso limita alertas comparaveis.
Frete nao cotado. Promocoes usam compare_at_price apenas das mesmas variantes;
referencia ausente, divergente ou inferior ao preco atual nao inventa desconto.

Foi corrigido o falso CAPTCHA causado por nomes de bibliotecas de protecao
de formularios Shopify em paginas publicas completas. Desafios reais,
recusas HTTP, robots e widgets ativos continuam recusados.

440 testes passaram (3 avisos PTB preexistentes), incluindo 21 novos casos.
Entrega Telegram/SQLite de anuncios foi simulada; sem envio real ao chat
nem execucao na VPS. Flexform esta limitada a URLs /cadeiras/tipo/produto;
outros departamentos ainda nao tem parser de descoberta validado.

# Painel publico Amazon - 2026.10.18-amazon-public-panel.1

Correcao funcional validada com resposta real em 18/10/2026: o JavaScript AOD usado pela propria Amazon declarou a rota GET /gp/product/ajax/aodAjaxMain e os parametros do dataset #all-offers-display-params, mais pc=dp. O script foi localizado pelo carregador aodIngressClick na pagina, sem inventar endpoint ou credenciais. O bot agora usa essa consulta antes de Selenium/Playwright e funciona tambem com navegador desativado. ASIN deve corresponder tanto ao URL quanto aos parametros da pagina; titulo do cabecalho do painel deve corresponder ao titulo original, e precos continuam limitados a cada linha de oferta/vendedor/condicao. Fragmentos sem ofertas nao viram preco zero.

A consulta usa conexao HTTP isolada, mantendo identificacao PriceMonitor, verificacao DNS/publicidade de enderecos, robots, HTTPS, dominio autorizado, retentativas e limites do Fetcher. Em diagnostico, conexao reutilizada apos abrir a pagina retornou 503, enquanto consulta isolada retornou 200; nao foi atribuida uma causa definitiva a cookies ou ao servidor. Recusas 403/CAPTCHA/robots e limites nao disparam uma tentativa de contorno com navegador.

Validacao real local: B08KGVH7YC retornou R$ 1.753,22, Amazon Global (ID A2EB9PYM83FCP9), NewCondition. Nao houve declaracao suficiente de pagamento ou estoque no painel; esses campos continuam desconhecidos e nao geram alerta comparavel. O fluxo completo HTTP real -> Monitor -> SQLite em memoria -> formatador foi exercitado para o link informado com ?th=1: um cartao com preco, zero falhas de leitura, pesquisa concluida. O transporte Telegram foi simulado; nao houve envio ao chat nem acesso SSH/VPS. Os valores sao capturas pontuais, nao garantias de preco atual. O AK820 B0CYGT9CWW apresentou falhas transitorias/503 ou divergencia de titulo; nao se afirma validacao desse anuncio ou de toda a Amazon.

Foi corrigido tambem o tratamento do MPN generico "b550", observado na ficha tecnica Amazon. Um chipset isolado nao deve confirmar qualquer placa com o mesmo chipset nem descartar automaticamente um modelo apenas porque outra loja declara codigo mais completo. Correspondencia sem identificadores fortes permanece pendente de confirmacao; conflitos de chipset, GTIN, versao ou codigos especificos continuam recusados.

397 testes passaram, com tres avisos PTB preexistentes. Quatorze novos casos cobrem parametros de mesmo ASIN, recortes reais de resposta, leitura sem navegador, recusa de titulo incorreto, preservacao de bloqueios/quotas, transporte isolado e MPN generico. Fixtures sao recortes reduzidos, sem formularios, scripts ou tokens. Testes nao consultam lojas.

Pichau: produto e pagina inicial continuaram retornando HTTP 403 no teste local. Nenhum acesso funcional foi obtido e esta revisao nao resolve o bloqueio da loja. Foi verificado o atendimento oficial em https://www.pichau.com.br/atendimento para solicitar acesso permitido/liberacao do IP; nao foi enviada mensagem em nome do usuario e nao existe API/credencial Pichau configurada ou validada neste projeto.

# Acesso das lojas - 2026.10.18-store-access.1

Pichau: o link informado da B550 Aorus Elite AX V2 retornou HTTP 403 tambem no teste local em 18/10/2026. Nao ha acesso funcional validado para esse link/IP nesta revisao. Nao foi implementado bypass de bloqueio/CAPTCHA, mudanca de identidade ou proxy. A coleta depende de acesso permitido pela loja; a alteracao abaixo nao libera o acesso nem recupera preco atual da Pichau.

Amazon: no HTML real recebido para B08KGVH7YC?th=1, havia aviso de carrinho mas nenhum link de opcoes de compra. O bot agora tambem tenta o painel publico do mesmo ASIN nesse caso, usando a rota AOD ja observada e usada pelo projeto, antes de encerrar a leitura. Nao adiciona itens ao carrinho. O teste real do painel publico B08KGVH7YC terminou em amazon_offers_panel_timeout; portanto a obtencao de preco individual continua nao validada para essa consulta. A captura reduzida nova documenta a variacao sem botao. O teste de preco 172711 usa uma fixture historica, sem representar preco atual.

Monitoramento: uma falha de acesso/robots/CAPTCHA suspende apenas os demais links daquela loja durante a verificacao atual. Gera um unico aviso por loja, conta as ofertas afetadas, registra consultas adiadas e preserva os precos validos; as outras lojas seguem. No ciclo seguinte volta a tentar, respeitando o intervalo de acesso do Fetcher. Nao ha suspensao definitiva do produto ou do agendamento.

383 testes passaram, com tres avisos PTB de depreciacao preexistentes. Os testes simulam abertura do painel mesmo com preco oculto/sem botao e dois ciclos com falhas de acesso, robots e CAPTCHA, mantendo consulta das outras lojas e ultimos precos. Nao houve acesso SSH, envio real Telegram ou validacao pela VPS. Nao se afirma que Pichau ou todos os precos Amazon estejam funcionando.

# HyperX Mars - 2026.10.18-model-monitoring.2

O anexo mostrou que a consulta manual "hyperx mars" encontrava outras lojas, mas o monitoramento podia reutilizar o titulo comercial ou MPN longo. A versao anterior ainda nao reconhecia essa familia. O extrator agora usa "hyperx mars" para a descoberta dos monitoramentos desse modelo, mantendo titulo e identificadores originais para verificar a oferta e suas variantes. Monitoramentos existentes passam a usar os novos termos sem recadastro.

30 testes focados passaram, incluindo tres novos casos com os titulos do anexo e monitoramento existente consultando a oferta original e outra loja por "hyperx mars". Nao se liberam alertas quando a condicao continua ausente. Consulta real local ao anuncio KaBuM 219729 confirmou marca estruturada "hyperx" e termo resultante "hyperx mars". Nao houve verificacao real das demais lojas ou da VPS nesta revisao. Links Amazon duplicados, preco oculto e restricoes Mercado Livre vistos no anexo sao problemas separados e nao se afirmam resolvidos aqui.

# Busca por modelo no monitoramento - 2026.10.18-model-monitoring.1

Auditoria do modo "Outras lojas tambem": a cada verificacao ele ja executava a descoberta nas lojas autorizadas e relia todos os candidatos persistidos, inclusive os de outras lojas. O titulo integral e guardado para exibicao/referencia; antes, quando nao havia identificador util, ele tambem podia virar a consulta inteira. MPN comercial numerico podia produzir descoberta excessivamente restrita.

Agora a consulta do monitoramento separa modelo e titulo: extrai modelos completos de familias reconhecidas (Gigabyte Aorus, Asus ROG Strix, AJAZZ e EPOMAKER), preservando AX, versao, Wi-Fi/II quando parte do modelo reconhecido e revisao explicita. Tambem aproveita o campo model declarado no Product estruturado, com marca. Caso nao haja evidencia suficiente para encurtar, preserva a busca conservadora anterior por MPN/marca ou titulo. Nao existe promessa de reconhecer automaticamente qualquer produto. Nao altera titulo salvo, assinatura, ID, banco ou proximo agendamento. Monitoramentos existentes passam a calcular os novos termos a cada ciclo, sem recadastro.

Exemplo informado: "Placa-Mae Gigabyte B550 Aorus Elite Ax V2, Chipset B550, AMD Am4, Atx, DDR4, 9mb55aew2-00-10" vira "gigabyte b550 aorus elite ax v2" para descoberta. Isso nao confirma ofertas: a comparacao continua priorizando codigos verificados e recusando conflitos; correspondencia ambigua depende de confirmacao. Precos continuam separados por oferta/vendedor/condicao/pagamento.

376 testes passaram nesta revisao (375 na suite completa antes do ultimo caso e 14 testes focados depois da extensao de marca estruturada). A suite emite tres avisos PTB de depreciacao preexistentes. Quatorze novos casos simulam extracao de modelos, versoes, revisao, marca/modelo estruturado e dois ciclos com cinco lojas, incluindo uma bloqueada. Confirmam nova consulta em cada ciclo, releitura de todas as ofertas, preservacao do titulo salvo e ausencia de aprovacao automatica apenas pelo termo curto. Nenhum acesso real a lojas, Telegram ou VPS foi feito nesta revisao. Bloqueios e precos ocultos do relato permanecem limitacoes independentes da identidade/busca.

# Opcoes de compra Amazon - 2026.10.17-amazon-options.1

O link publico declarado em "Ver todas as opcoes de compra" agora tem prioridade sobre a mensagem de preco oculto/carrinho. Falhas tecnicas de inicializacao, ausencia de Selenium ou encerramento do Chrome permitem uma tentativa com o Chromium Playwright ja instalado pelo deploy. Bloqueio, CAPTCHA, HTTP recusado e timeout de leitura nao disparam troca de navegador. Falhas de acesso sao respeitadas. O navegador aguarda scripts/painel e aciona somente o link publico do mesmo ASIN e origem; nenhum botao de compra e utilizado. Precos do painel so sao aceitos se o titulo corresponder ao da pagina principal, preservando identificadores do produto.

O modo de painel admite apenas scripts estaticos dos CDNs Amazon observados, com DNS publico, robots.txt proprio, cache de regras e limite de recursos. Outros dominios, metodos que alteram estado e rotas de carrinho/checkout continuam recusados. Se o painel falhar tecnicamente mas existir minimo publico, o bot preserva apenas a referencia "a partir de", sem trata-la como preco individual ou gerar alertas.

Validacao real local em 17/10/2026: B0CYGT9CWW possui o botao e o link informado, e publicou outras ofertas a partir de R$ 369,00. Tentativas de carregar o painel com Playwright terminaram em timeout, sem linhas de ofertas individuais. Portanto NAO foi validada a coleta de preco por vendedor desse AK820. A VPS, instalacao de ChromeDriver como pricebot e envio real Telegram nao foram acessados. Nao se afirma que todos os problemas Amazon foram resolvidos.

362 testes passaram, com tres avisos PTB preexistentes. Dezesseis novos casos simulam precedencia do botao sobre o aviso de carrinho, alternativa tecnica de navegador, recusa de troca apos bloqueio/CAPTCHA/timeout, politica/cache do CDN, acionamento restrito ao ASIN correto e preservacao da referencia publica. O preco 172711 centavos usado no teste de painel vem de uma fixture historica de placa-mae; nao e o preco do AK820. A fixture nova AK820 e recorte real reduzido do botao e do minimo publico, sem scripts, formularios ou tokens.

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
