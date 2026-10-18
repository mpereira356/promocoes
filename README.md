**Versão atual: `2026.10.18-confirm-choice.1`.** Envie **/start** ou **/menu** para usar a central de botões: buscas, promoções, monitoramentos e dinheiro emprestado. Veja [MENU-TELEGRAM.md](MENU-TELEGRAM.md).

**Fila de pedidos:** o bot executa uma tarefa por vez. Se uma pesquisa ou
verificação estiver em andamento, novos comandos, mensagens e botões autorizados
recebem **⏳ Seu pedido entrou na fila** e aguardam na ordem de chegada. O trabalho
e os resultados iniciados por um comando terminam antes do próximo pedido.
Os comandos continuam sendo recebidos enquanto o bot consulta as lojas.
Verificações automáticas e envio de lembretes também usam a fila, evitando
misturar resultados. Um lembrete pode chegar após o horário se houver uma
tarefa em andamento. Menus, pausa e cancelamento também aguardam sua vez;
`/cancelar` não interrompe uma consulta em andamento.

A fila é mantida em memória: reiniciar o serviço descarta pedidos ainda não
executados. Produtos, empréstimos, histórico e agendamentos continuam persistidos
no SQLite. Uma falha de um pedido permite continuar com o próximo.

**Verificar agora em outras lojas:** monitoramentos com abrangência `all`
descobrem novas ofertas e releem todos os links vinculados. Agora também
recuperam anúncios compatíveis do SQLite (até 300 anúncios recentes examinados,
até seis links recuperados por loja), inclusive quando o índice externo está
limitado. Cada preço e estoque é consultado novamente na página; valores salvos
não são apresentados como atuais se essa consulta falhar. O resumo informa
leituras, preços obtidos, falhas e consultas adiadas por loja. Confirmações de
modelos ambíguos continuam necessárias; abrangência `site` continua restrita à
oferta escolhida. Adaptadores de cadeiras não consomem buscas externas para
consultas claramente de hardware, como B550, SSD ou teclado.

**Respostas simultâneas:** avisos e resumo de `/buscar` identificam o texto
pesquisado; resultados de verificação identificam o número do monitoramento e
o produto. Isso permite distinguir uma busca manual de uma consulta já em
andamento. Monitoramentos Sensetup A08/A161 usam marca e modelo na descoberta,
preservando o título cadastrado e a confirmação de ofertas ambíguas.

**Falhas de acesso:** timeout, conexão, erro de servidor e limite HTTP 429 agora
têm motivos separados. Os diagnósticos `scripts.diagnose_offers` e
`scripts.diagnose_stores` mostram o status HTTP de cada tentativa e apenas o
tipo da exceção, sem mensagens brutas ou credenciais. Após 429 persistente,
o bot pausa novas consultas à mesma loja; respeita `Retry-After` e continua
com as outras lojas. Sem prazo explícito, a pausa após três respostas 429 é
de pelo menos 60 segundos. A pausa vale durante o processo atual.

**Sugestões de novas ofertas:** os cartões identificam o monitoramento e o
produto acompanhado, explicam que a verificação encontrou uma oferta para
conferência e distinguem esse pedido de um alerta de mudança de preço.
O botão **Confirmar e acompanhar** inclui a oferta no monitoramento existente;
você pode ignorar a sugestão. `/opcoes ID` informa que as pendências foram
solicitadas manualmente. Open Box é destacado quando consta no título, sem
inferir uma condição diferente. Textos longos usam mensagem sem foto para
respeitar o limite de legenda do Telegram.

**Lojas de cadeiras:** buscas por nome e links agora incluem **Sensetup**,
**Elements** e **Flexform**. Exemplos: `/buscar Cadeira A08 Premium`,
`/buscar Cadeira Elements Galatea`, `/buscar Cadeira Uni All Grey`.
Sensetup e Elements usam sitemaps publicados para descobrir produtos, e dados
Shopify presentes no HTML para ler preços; Flexform usa o formulário GET da loja
e Schema.org Product. Não exigem navegador nem nova chave de busca nesses fluxos.

Os testes reais locais confirmaram descoberta e preço de um produto por loja,
além de uma página de categoria por loja. Isso não garante cobertura de todo o
catálogo. Variantes com preços diferentes aparecem apenas como referência
"a partir de" até informar um link com `?variant=ID`; não se misturam cores ou
estoques diferentes. Campos não declarados, como condição, vendedor e pagamento,
permanecem desconhecidos e podem impedir alertas de comparação.

Na VPS, `bash deploy/update.sh` amplia automaticamente a lista padrão antiga de
domínios. Se você personalizou `ALLOWED_DOMAINS`, mantenha sua seleção e acrescente
`sensetup.com.br,loja.elements.com.br,flexform.com.br`, depois reinicie o serviço.
As novas lojas também aparecem na seleção de promoções; há uma categoria inicial
**Cadeiras > Ergonômicas**, com limites de páginas e produtos como nas demais lojas.

**💸 Dinheiro emprestado:** no menu principal, toque nesse botão ou envie
`/emprestimos`. Use **➕ Emprestar** e informe o nome, o valor (ex.: `150`
ou `1.250,50`) e a data (ex.: `25/12/2026`). A lista mostra pendências,
atrasos, total e histórico dos pagos. Abra um registro para confirmar pagamento,
manter **Falta pagar** ou **Prorrogar** com outra data. Não há pagamentos parciais
nesta versão; marcar pago representa quitação integral.

Os dois lembretes são enviados ao chat configurado às **09h e 18h, no fuso
America/Sao_Paulo**, para cada data combinada. O bot não envia mensagens para
a pessoa cadastrada. Pagamento encerra os lembretes; prorrogação substitui a
data e permite dois novos avisos. Manter pendente não reinicia avisos já enviados.
Não há repetição diária automática após o segundo aviso; o registro continua
marcado como pendente/atrasado até pagar ou prorrogar.

Cadastros e envios ficam no mesmo SQLite dos produtos; não é preciso editar o
`.env` nem instalar dependências novas. Reinícios preservam os dados e os avisos
registrados. Se o bot estiver desligado no horário, recupera avisos pendentes
quando voltar, com intervalo mínimo de uma hora entre os dois. Nesse caso,
não é possível garantir dois avisos no dia original. Uma falha de envio será
tentada novamente; uma interrupção entre a entrega ao Telegram e a gravação
no SQLite pode ocasionar repetição. Cadastros guiados ainda não concluídos
expiram em 15 minutos ou ao reiniciar.

**Títulos e exemplos:** os títulos aparecem em negrito no Telegram, com HTML escapado, inclusive nas legendas de fotos. A ajuda explica os argumentos de `/configurar`, mostra quando os filtros disparam ou impedem um alerta, como remover o alvo e como alternar os modos. A seleção de promoções também traz exemplos de `>30` e `>=30`.

**Mensagens revisadas:** os textos enviados pelo usuário foram aplicados com acentuação, blocos curtos, botões e emojis consistentes. As regras de busca, comparação e monitoramento são preservadas. Os templates de referência estão em [TEMPLATES-REVISADOS.md](TEMPLATES-REVISADOS.md).

**Categorias ampliadas:** `/promocoes` agora navega por **201 categorias/subcategorias em 33 grupos** de links observados nas lojas, com paginação. Use `/categoria monitores`, `/categoria pets` ou qualquer outro tema; também aceita link HTTPS da categoria. `/categorias atualizar` relê os menus públicos. Sem página mapeada, usa busca por termo e informa essa limitação. Nenhuma dessas consultas cria monitoramento. Preço/estoque e acesso continuam sujeitos à validação da página. Veja [PROMOCOES.md](PROMOCOES.md).

**Precos Amazon:** o robo le primeiro a pagina e, quando necessario, consulta o painel publico usado pelo frontend da loja com parametros do mesmo ASIN. Essa leitura HTTP foi validada localmente para B08KGVH7YC, sem ChromeDriver, com preco, vendedor e condicao. Selenium/Playwright permanecem para formatos sem painel reconhecido; recusas e limites nao sao contornados. Estoque e pagamento ausentes continuam desconhecidos. Consulte [STATUS-LOJAS.md](STATUS-LOJAS.md) para os testes reais e as limitacoes; a Pichau continua retornando 403 no ambiente testado.

Para publicar no GitHub e atualizar o servidor com Git, veja [GITHUB.md](GITHUB.md).

**Leia [STATUS-LOJAS.md](STATUS-LOJAS.md) para o estado real de cada integracao.** Amazon Brasil foi adicionada a descoberta e ao leitor de paginas; precos ocultos ou dados ausentes permanecem desconhecidos. Pichau/Terabyte usam descoberta externa quando o sitemap limitado nao encontra candidatos. Nem todas as lojas possuem todos os campos validados; nao ha promessa de cobertura universal.

**Mercado Livre: descoberta de links pelo indice externo Tavily sem chave.** Use `/buscarml nome` para pesquisar somente no Mercado Livre, ou `/buscar nome` com `SEARCH_PROVIDER=direct` para incluir a loja nas pesquisas gerais. Nao exige aplicativo Mercado Livre, dominio, redirect ou token. O modo publico e limitado e pode ficar temporariamente indisponivel. Veja [MERCADO-LIVRE.md](MERCADO-LIVRE.md).

A descoberta foi testada com resultados reais para Gigabyte B550 Aorus Elite V2 em 15/10/2026. Links de catalogo sao exibidos para conferencia, sem preco, ID de anuncio monitoravel, medalhas ou alertas. O titulo vem do indice e pode estar desatualizado. A leitura de paginas Mercado Livre continua bloqueada com 403 no ambiente testado; monitoramento de precos dessa loja ainda nao foi validado. Nenhum preco do indice e usado como preco de oferta.

Ao executar `bash deploy/update.sh`, o instalador acrescenta `mercadolivre.com.br` se o `.env` ainda contiver exatamente a lista padrao das tres lojas. Listas personalizadas devem receber esse dominio manualmente em `/opt/price-monitor/.env`; depois reinicie o servico. A descoberta externa nao precisa de Chromium. A leitura de ofertas ainda depende do acesso permitido a loja.

# Monitor de preços pelo Telegram

Python 3.11+, SQLite e comandos assíncronos. Busca direta nas lojas, sem API paga por padrão. Verifica a cada **5 horas**, avisa aumentos e quedas e continua até você pausar ou remover. Não existe prazo de encerramento após o primeiro alerta.

## Configuração

Copie `.env.example` para `.env` apenas na primeira instalação. Em atualizações, preserve seu `.env` e o diretório `data`. Nunca publique o token ou a chave. O token compartilhado no chat deve ser revogado no BotFather e substituído no `.env`.

- `TELEGRAM_BOT_TOKEN`: token do seu bot.
- `TELEGRAM_CHAT_ID`: grupo de destino. Preencha com o ID do seu grupo.
- `TELEGRAM_USER_ID`: seu ID pessoal positivo. Somente essa pessoa, nesse grupo, pode executar comandos ou clicar nos botões. O ID do grupo não serve nesse campo.
- `SEARCH_PROVIDER=direct`: pesquisa nas lojas, sem chave externa.
- `SEARCH_API_KEY`: pode ficar vazio em `direct`. A alternativa `brave` exige chave própria; `disabled` permite somente links.
- `ALLOWED_DOMAINS`: domínios autorizados, separados por vírgulas; `www.` é normalizado. Adicionar um domínio não implementa sua pesquisa.
- `DATABASE_PATH=data/monitor.sqlite3`: banco, agenda e fila de alertas persistentes.
- `INTERVAL_HOURS=5`, `REQUEST_DELAY=3`: intervalo entre ciclos e espera mínima por domínio.
- `PLAYWRIGHT_ENABLED=false`: navegador opcional, desligado por padrão.
- `MIN_DROP_BRL`, `MIN_DROP_PERCENT`, `TARGET_PRICE`: filtros para o modo opcional de somente quedas. Use ponto decimal, sem separador de milhar.

O padrão de alertas é **qualquer alteração observada**, sem aplicar filtros de queda ou alvo. `/configurar` ativa o modo somente quedas; nesse modo todos os limites configurados devem ser satisfeitos. `/alertas ID todas` volta a avisar aumentos e quedas. As variáveis de filtros são copiadas para novos acompanhamentos; não atualizam retroativamente os existentes.

## Executar no Windows

Primeira instalação no PowerShell:

```powershell
cd C:\Users\viny_\Desktop\projetos\promocoes
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m monitor
```

Se já está instalado e configurado, basta iniciar:

```powershell
.\.venv\Scripts\python.exe -m monitor
```

Mantenha o terminal aberto. Ctrl+C encerra. Depois de atualizar o código, pare o processo e execute novamente. Não copie `.env.example` sobre suas configurações durante uma atualização. `requirements.lock.txt` contém as versões instaladas na validação; pode ser usado para reproduzi-las. Somente uma instância pode usar o mesmo banco; um lock do sistema operacional bloqueia uma segunda inicialização.

O token não é utilizado nos testes. Não existe envio real de teste automático ao Telegram.

## Encontrar e selecionar um anúncio

1. Envie `/buscar Placa Mãe Asus ROG STRIX B550-F GAMING WIFI II` ou um nome mais curto, como `/buscar b550`.
2. Cada resultado começa com **Anúncio ID**, seguido de foto quando disponível, medalha, preço, pagamento, vendedor, condição, estoque e link.
3. Envie `/monitorar 3`, usando o ID do anúncio desejado, ou clique em **Monitorar anúncio 3**.
4. O robô pergunta: **Só esta oferta neste site** ou **Outras lojas também**.
5. Após escolher, recebe um **Monitoramento ID** para os comandos de controle.

O ID do anúncio é persistente, não é a posição no ranking e continua válido após outras buscas ou reinícios. A mesma URL/modelo conserva o ID; alterações de identidade do produto geram outro ID. Diferentes modalidades da mesma página podem compartilhar um ID de anúncio.

`/buscar` registra os resultados no catálogo SQLite, mas **não ativa acompanhamento**. `/monitorar nome` ou `/monitorar https://link` também apresentam anúncios para selecionar pelo ID; não ativam um monitoramento silenciosamente. Somente a escolha da abrangência cria o acompanhamento. Cliques repetidos não duplicam a mesma assinatura. Se já estiver pausada, use `/retomar ID` para reativar.

- **Só esta oferta:** consulta exclusivamente a URL escolhida. Não pesquisa outras lojas nem substitui o produto por similares.
- **Outras lojas:** mantém a oferta original e redescobre o mesmo modelo nas lojas autorizadas e suportadas em cada ciclo. Cada oferta mantém sua própria série de preços.

O reconhecimento entre lojas aceita GTIN válido igual, MPN e marca iguais, ou título completo normalizado idêntico contendo número de modelo. Identificadores conflitantes são recusados. Sem evidência suficiente, a oferta aguarda confirmação explícita por `/confirmar OFERTA_ID` ou `/opcoes MONITORAMENTO_ID`. SKU interno da loja não é usado como identificador universal. Variantes WIFI, sem Wi-Fi e WIFI II não são automaticamente equivalentes.

A foto vem de `Product.image` da própria página (URL, lista ou ImageObject). A URL HTTPS é entregue ao Telegram para carregar; nenhum desenho ou foto é inventado. Se a foto falhar, o resultado continua por texto. Imagens ilustrativas não comprovam modelo, condição ou estoque. Candidatos ambíguos em outros acompanhamentos continuam usando cartões de confirmação próprios.

## Comandos

```text
/buscar nome ou https://link
/monitorar ID_DO_ANUNCIO
/monitorar nome ou https://link
/lista
/opcoes MONITORAMENTO_ID
/confirmar OFERTA_ID
/historico MONITORAMENTO_ID
/verificar MONITORAMENTO_ID
/pausar MONITORAMENTO_ID
/retomar MONITORAMENTO_ID
/remover MONITORAMENTO_ID
/alertas MONITORAMENTO_ID todas
/alertas MONITORAMENTO_ID quedas
/configurar MONITORAMENTO_ID reais porcentagem alvo
/ajuda
```

Exemplo de filtro: `/configurar 1 50 5 1500`. Significa somente quedas de pelo menos R$ 50 e 5%, com preço atual até R$ 1.500. Use `-` no alvo para removê-lo. O comando ativa somente quedas. Para receber qualquer alteração novamente, use `/alertas 1 todas`.

São três identificadores distintos: **Anúncio ID** para `/monitorar`, **Monitoramento ID** para controle e histórico, **Oferta ID** para confirmar páginas pendentes dentro de um acompanhamento. Cada mensagem identifica qual usar. Um ID desconhecido de anúncio não é interpretado como ID de monitoramento.

`/verificar` consulta imediatamente, inclusive quando pausado, mas os alertas de um monitoramento pausado ficam pendentes até retomar. `/pausar` suspende agenda e entrega; uma consulta já iniciada pode terminar. `/remover` exclui o monitoramento, suas ofertas, séries, leituras e alertas por cascata. Os anúncios do catálogo permanecem com seus IDs, permitindo uma nova assinatura. `/historico` exibe as últimas 30 leituras e mínimos das modalidades; o banco preserva o histórico completo.

## Alertas e duração

A primeira leitura comparável após ativar registra a base, sem fabricar preço anterior nem usar o resultado antigo da busca como leitura nova. Cada série é separada por URL, título, vendedor, condição, pagamento e moeda. Pix não é comparado com cartão; usado não é comparado com novo. Novas modalidades são identificadas como novas, sem queda fictícia.

No modo padrão, cada mudança válida observada gera um aviso destacado com **🚨**, indicando aumento **📈** ou queda **📉**, preços anterior e atual, variação em reais e percentual, loja, vendedor, condição, pagamento, menor histórico daquela série, horário de São Paulo, link e frete não incluído. O robô não calcula frete, cashback ou cupons pessoais. Os avisos continuam após qualquer alteração; manter o mesmo preço não gera repetição. Uma subida seguida de queda são dois episódios, ambos avisados no modo todas.

Dados insuficientes de preço, moeda BRL, vendedor, condição ou pagamento suspendem a comparação. Alertas também exigem evidência de estoque disponível na página. A ausência de evidência não vira estoque confirmado. Falha de rede, CAPTCHA, preço inválido ou página removida não vira preço zero, não apaga o último preço válido e não encerra o monitoramento.

As consultas ocorrem a cada cinco horas após terminar o ciclo. Uma alteração temporária entre duas consultas pode não ser observada. A agenda, status, escolhas de abrangência, catálogo, histórico e fila sobrevivem ao reinício. Consultas vencidas executam uma vez após reiniciar; não há tempestade para recuperar todos os intervalos perdidos. Computador suspenso não verifica.

Alertas são enfileirados na mesma transação da mudança de preço. Falhas de envio deixam a mensagem pendente. Existe uma janela entre o Telegram aceitar a mensagem e o banco confirmar: um crash nessa janela pode repetir a mensagem, pois `sendMessage` não tem chave de idempotência. Não se promete entrega exatamente uma vez. O destaque visual não muda o volume ou as configurações de notificação do seu aparelho.

## Medalhas

A busca reúne as leituras e ordena por preço em cada grupo de pagamento, condição e moeda: **🥇**, **🥈**, **🥉** para os três menores valores distintos. Empatados recebem a mesma medalha; o próximo valor recebe a seguinte. Sem preço positivo em BRL, pagamento identificado ou estoque confirmado, não há medalha.

Condição ausente fica em grupo separado, marcado **ranking provisório**. Isso compara apenas valores exibidos, sem afirmar equivalência de condição e sem habilitar alertas históricos. Modelos diferentes de uma busca ampla podem participar, com aviso explícito. O ranking considera somente os anúncios lidos nessa consulta, sem frete; não representa toda a internet nem o mínimo histórico.

## Busca direta e limites reais

A busca direta usa o mesmo controle de acesso e limites das ofertas. Consulta somente a primeira página de cada loja, com até seis links por loja e quinze no total. Filtra os tokens numéricos do modelo e ordena pela correspondência dos títulos. Não substitui B550 por B650/X870. Nenhum preço do catálogo ou de snippet de busca gera comparação: preço e estoque são conferidos na página da oferta.

- **KaBuM:** descoberta pelo `__NEXT_DATA__` observado na página `/busca/termos` e links de produto. A busca real por `b550` descobriu seis URLs. O nome completo da B550-F GAMING WIFI II não retornou candidato compatível na consulta validada.
- **Pichau:** descoberta por sitemap publico e leitura por Chromium comum, quando ativado. A Gigabyte B550 Aorus Elite V2 foi lida pelo coletor de producao, com Pix, vendedor, condicao nova e estoque. HTTP simples ainda pode falhar; use o pacote com --with-browser no Kali.
- **Terabyte:** descoberta pelos sitemaps publicados, sem consultar /busca. Chromium leu robots.txt, sitemaps e a Elite V2; essa oferta estava indisponivel. CAPTCHA de avaliacao nao e tratado como barreira quando os dados publicos do produto ja foram entregues. Desafios reais e robots continuam respeitados.
- **Amazon:** sem adaptador de busca direta implementado. Autorizar o domínio não cria essa integração.

Zero candidatos no HTML consultado não prova inexistência do produto: busca pode omitir indisponíveis, exigir JavaScript ou não estar compatível. Bloqueios de uma loja não descartam resultados das demais. Avisos aparecem juntos em um resumo.

Os adaptadores de preço ficam separados em `monitor/adapters/`. O parser comum prefere um único `Product` Schema.org inequívoco, rejeita `AggregateOffer.lowPrice` e recomendações como oferta, e exige modalidade explicitamente identificada para comparar. Preços JSON-LD usam ponto decimal.

Na KaBuM, o adaptador complementa vendedor com `pageProps.product.sellerName` somente quando ID da URL e título correspondem. Validado no HTML real de uma oferta própria (KaBuM!) e de marketplace (GIGANTEC). Pix exige correspondência entre preço JSON-LD, `prices.priceWithDiscount` e um único valor no mesmo parágrafo do rótulo visível “à vista no PIX”. Palavra Pix no rodapé não basta. Vendedor conflitante interrompe a leitura.

**A condição não foi declarada nas duas ofertas KaBuM validadas.** `isOpenbox=false` não comprova produto novo. O campo permanece ausente e os alertas ficam suspensos, mesmo com vendedor/Pix identificados. Não há validação completa de alertas reais nas lojas. Escolher abrangência não elimina essa limitação.

Adicionar outra loja requer autorizar o domínio e implementar/registrar seu adaptador de descoberta. Links diretos podem usar o parser genérico, sem garantia de compatibilidade. Novos seletores devem ser baseados em HTML real e acompanhados de fixtures com procedência, sem inferir condições de preço.

## Acesso e navegador opcional

HTTP com timeout de 30 segundos, até três tentativas para rede/429/5xx, espera progressiva, `Retry-After` e intervalo mínimo por domínio. Esperas longas ficam para outro ciclo. Robots.txt usa curingas, âncora final e prioridade da regra mais específica. Se o arquivo estiver indisponível, a leitura é recusada; 404/410 significa ausência de regras. CAPTCHA e 401/403 não são contornados.

Playwright só é tentado quando o HTML permitido não fornece o produto/candidatos, nunca como contorno de bloqueio. Para instalar no Windows:

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

Depois configure `PLAYWRIGHT_ENABLED=true`. Recursos ficam restritos aos domínios autorizados; lojas dependentes de APIs/CDNs externos podem continuar incompatíveis. O navegador não foi validado em lojas reais nem no serviço Debian fornecido.

URLs e redirecionamentos passam pela lista exata de domínios; endereços não públicos são recusados. Não autorize domínios não confiáveis. A checagem DNS adicional não promete isolamento contra DNS rebinding; ambientes hostis precisam de filtro de saída. Tokens não são colocados em logs HTTP ou mensagens de erro. Locks impedem consultas duplicadas do mesmo monitoramento; URLs em andamento são compartilhadas. Comandos continuam sendo recebidos durante a rede.

## VPS Debian 12/13 e systemd

Transfira o projeto sem `.env`, `.venv` ou dados locais para `/opt/price-monitor`, depois configure:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ca-certificates tzdata
sudo useradd --system --home /opt/price-monitor --shell /usr/sbin/nologin pricebot
sudo mkdir -p /opt/price-monitor/data
# Copie os arquivos para /opt/price-monitor antes dos próximos comandos.
sudo python3 -m venv /opt/price-monitor/.venv
sudo /opt/price-monitor/.venv/bin/python -m pip install -r /opt/price-monitor/requirements.txt
sudo cp /opt/price-monitor/.env.example /opt/price-monitor/.env
sudo nano /opt/price-monitor/.env
sudo chown -R root:pricebot /opt/price-monitor
sudo chmod 640 /opt/price-monitor/.env
sudo chown -R pricebot:pricebot /opt/price-monitor/data
sudo chmod 750 /opt/price-monitor/data
sudo cp /opt/price-monitor/deploy/price-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now price-monitor
sudo systemctl status price-monitor
sudo journalctl -u price-monitor -f
```

Use `DATABASE_PATH=data/monitor.sqlite3`. Para atualizar, pare o serviço, faça backup do diretório `data`, copie código, atualize dependências e inicie novamente. Preserve as permissões. As migrações aditivas atuais são automáticas e preservam agenda, pausa e histórico. A atualização ativa alertas de todas as alterações nos acompanhamentos anteriores; `/alertas ID quedas` restaura o modo filtrado.

O serviço permite escrita somente em `data`. A operação HTTP não precisa de navegador. Playwright no Debian exige instalar bibliotecas/Chromium e definir uma pasta de browsers legível pelo usuário do serviço; esse cenário não foi validado sob o confinamento systemd fornecido.

## Validação

Veja `VALIDACAO.md`. A suíte atual tem **92 testes aprovados**, cobrindo comparação, falhas, fila, IDs, abrangência, persistência, autorização, identidade de modelo e medalhas. Três testes usam snapshots reduzidos reais de metadados KaBuM; os demais usam dados simulados. Preços e envios Telegram dos testes são simulados. Não se executou um ciclo real de cinco horas nem o serviço Debian. Nenhuma mensagem real foi enviada durante o desenvolvimento.

Sondagem de busca sem credenciais: `python -m scripts.probe_search b550`. Sondagem de ofertas: `python -m scripts.probe_stores`. Relatórios ficam em `data` e não são incluídos no pacote. Não confundem compatibilidade parcial com integração de alertas completa.

Referências: [python-telegram-bot](https://docs.python-telegram-bot.org/en/stable/telegram.ext.applicationbuilder.html), [Schema.org Offer](https://schema.org/Offer), [Brave opcional](https://api-dashboard.search.brave.com/app/documentation/web-search/get-started).

## Pacote para Kali por SSH

Use `monitor-precos-kali.tar.gz` e siga [LEIA-ME-KALI.md](LEIA-ME-KALI.md). O instalador `sudo bash deploy/install-kali.sh` cria o ambiente virtual, pede as credenciais no terminal e configura o systemd. Não inclui dados pessoais no pacote. O guia também explica como exportar/migrar o banco e preservar os IDs. A suíte ampliada de empacotamento tem **95 testes aprovados**; a instalação real no seu Kali não foi executada neste ambiente Windows.


## Atualizacao de sitemaps para Pichau e Terabyte

A descoberta nessas duas lojas usa sitemaps publicados como alternativa a busca interna. A leitura de preco e estoque continua obrigatoriamente na pagina da oferta. XML invalido, DTD/entidades, URLs externas e caminhos de produto inadequados sao recusados. Cada indice e limitado a quatro documentos e cinquenta mil URLs, com cache de cinco horas para reduzir acesso; nao ha varredura ilimitada. O filtro de relevancia e a confirmacao do modelo continuam valendo. O slug e usado apenas para selecionar links candidatos, nunca para afirmar preco, estoque ou identidade exata do produto.

Nenhum bloqueio foi contornado e Selenium nao foi acrescentado: o recurso de navegador ja existente e opcional para paginas permitidas que precisem de JavaScript. Nao e acionado para ignorar robots.txt, 401/403 ou CAPTCHA. No Kali o modo HTTP nao requer instalar navegador nem alterar dependencias. Atualize com o novo `monitor-precos-kali.tar.gz` e execute novamente `sudo bash deploy/install-kali.sh`; o instalador preserva `.env`, dados e IDs. O sucesso na descoberta nao elimina bloqueios na leitura das ofertas.

## Correção atual de Pichau/Terabyte — 2026.10.15-browser.1

A investigação desta versão conseguiu ler as páginas reais com Chromium comum. Para ativar no Kali, use o novo pacote **monitor-precos-kali-browser.tar.gz** e execute `sudo bash deploy/install-kali.sh --with-browser`. Isso instala navegador e bibliotecas, ativa o transporte dessas duas lojas e preserva credenciais, dados e IDs. Consulte o final de LEIA-ME-KALI.md para os comandos completos. `/status` mostra versão e se Chromium está ativado.

Dois problemas foram corrigidos: cabeçalhos de compressão do texto já decodificado não são aplicados outra vez; e um campo de reCAPTCHA do formulário de avaliações não é confundido com uma barreira de acesso ao conteúdo público do produto. Nenhum CAPTCHA é resolvido nem interagido. O transporte mantém o User-Agent PriceMonitor, domínios, DNS público, robots.txt, limites e tempos de espera. A consulta inicial por Chromium não executa JavaScript, pois os dados testados já estão no HTML; não há stealth, proxy ou mudança de identidade para agentes privilegiados.

Pichau agora tem extração de Pix pelo bloco de preço à vista associado ao produto e ao rótulo explícito, mantendo vendedor/condição/estoque do JSON-LD. Terabyte lê o vendedor explícito e não converte preço visual zero em oferta. Na sondagem real da Elite V2, a Pichau estava disponível e comparável; a Terabyte estava indisponível, sem modalidade atual segura para comparação. As regras de não misturar modalidades e não inventar estoque/preço continuam valendo.

A validação real foi executada no Windows com Chromium, sem Telegram, usando o mesmo Fetcher e adaptadores de produção. A instalação APT/systemd no seu Kali ainda precisa ser executada; o instalador verifica a inicialização do navegador como usuário do serviço. Outros produtos e futuras mudanças do site podem exigir novas adaptações. As limitações de transporte HTTP das versões anteriores ficam substituídas por este caminho testado quando o modo navegador estiver ativado.

## Diagnosticar um anúncio que falhou na VPS

Após atualizar o projeto, consulte o mesmo link como usuário do serviço:

```bash
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_offers --browser \
  --url 'https://www.pichau.com.br/teclado-mecanico-ajazz-ak820-rgb-switch-vermelho-preto-ak820-bk'
```

Repita `--url 'LINK'` para testar outros anúncios. O diagnóstico não grava banco nem envia Telegram. Mostra preço quando lido, disponibilidade, motivo de falha e posições do código. Não imprime mensagens brutas de exceções ou credenciais. `price_verified: true` significa que o preço foi lido, inclusive em um produto indisponível; não confirma possibilidade de compra. No Windows, use `.\.venv\Scripts\python.exe` no lugar de `sudo -u pricebot .venv/bin/python`.

Bloqueios por IP, CAPTCHA e exigência de carrinho podem impedir obter preços. Sucesso no Windows não confirma acesso pela VPS. A validação dos links AJAZZ e as limitações restantes estão em [VALIDACAO.md](VALIDACAO.md).

**Monitoramento em outras lojas:** o titulo completo permanece salvo para exibicao, mas a descoberta usa marca/modelo reconhecido ou identificadores declarados. Exemplo: `Gigabyte B550 Aorus Elite AX V2`, sem exigir a mesma descricao comercial em cada loja. Familias ainda nao reconhecidas usam a busca conservadora anterior. A descoberta e repetida em cada ciclo e os links conhecidos sao relidos; falhas de acesso nao significam ausencia do produto. Ofertas ambiguas precisam de confirmacao e bloqueios continuam sendo respeitados.
