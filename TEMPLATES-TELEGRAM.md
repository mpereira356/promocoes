# Templates e respostas atuais do bot Telegram

Documento para revisao editorial por outra IA. Extraido do codigo instalado no projeto; nao altera o funcionamento do bot.

## Pedido para a outra IA

Reorganize e padronize os textos e fluxos de mensagens deste bot em portugues brasileiro. Melhore clareza, hierarquia visual, pontuacao, acentuacao e uso moderado de emojis. Proponha os templates completos e uma tabela com texto atual, texto sugerido e arquivo/funcao de origem.

Preserve todos os comandos, seus argumentos, IDs e placeholders. Nao altere regras de preco, calculos, autorizacao, callbacks ou monitoramento. Diferencie anuncio, oferta e monitoramento. A busca /promocoes e pontual e nunca cadastra alertas futuros. Nao invente preco, estoque, vendedor, pagamento, comparacao confirmada, queda historica ou integracoes funcionando. Preserve avisos de dados ausentes, referencia suspeita, limites, frete nao incluido e falhas de lojas. Na busca de promocoes use o mesmo emoji de trofeu em cada resultado; na busca comum ha medalhas por preco.

Nao foram incluidos .env, banco de dados, tokens, credenciais ou IDs pessoais. Os valores entre chaves sao variaveis de template, nao valores reais. Alguns textos atuais nao possuem acentos; isso faz parte do material para revisao.

## Como ler

O catalogo abaixo contem os textos literais e f-strings de apresentacao encontrados nos modulos indicados, com suas linhas e funcoes. Expressoes condicionais podem representar variantes de uma mesma resposta. Fragmentos sao montados em sequencia no codigo. Campos entre chaves indicam os dados dinamicos originais. Campos numericos podem conter especificadores de formato, como :.2f.

Ao final ha uma referencia exata dos modulos que montam as mensagens, incluindo a funcao de alerta e os mapas de erros. Ela permite conferir a ordem dos fragmentos, condicoes de exibicao, botoes e respostas sem precisar acessar o repositorio.

## Comandos que devem ser preservados

/start, /ajuda, /status, /buscar nome, /buscarml nome, /monitorar ID_DO_ANUNCIO ou nome/link, /lista, /opcoes PRODUTO_ID, /confirmar OFERTA_ID, /historico ID, /pausar ID, /retomar ID, /remover ID, /verificar ID, /configurar ID reais porcentagem alvo, /alertas ID todas|quedas, /promocoes, /descontopromo >=30, /ceppromo 01001000.

## Mapa de fluxos

1. Ajuda, status, validacao de argumentos e controle de monitoramentos.
2. Pesquisa por nome/link, resultados com ou sem foto, medalhas, precos desconhecidos e resumo de conclusao.
3. Links de indice externo ainda nao verificados, especialmente catalogos Mercado Livre.
4. Escolha de oferta e confirmacao de modelo exato.
5. Escolha de abrangencia: uma oferta ou outras lojas; ativacao e acompanhamento.
6. Leitura inicial, dados insuficientes, mudanca de titulo e falhas com preservacao do ultimo preco.
7. Alertas de aumento/queda com preco anterior, atual, economia/aumento e menor historico.
8. Promocoes por categoria: categoria, subcategoria, filtro, lojas, CEP, execucao e resultados com trofeu.
9. Resumo de cobertura parcial e limitacoes das lojas.

# Catalogo de textos atuais

## monitor/__main__.py

### modulo - linha 22

```text
/buscar nome - encontrar anuncios com ID, fotos e medalhas (sem ativar acompanhamento)
/promocoes - busca pontual por categoria, desconto e lojas; sem acompanhamento
/descontopromo >=30 - percentual personalizado na etapa de desconto
/ceppromo 01001000 - informar CEP da consulta (frete ainda nao cotado)
/buscarml nome - descobrir links Mercado Livre; dados nao verificados sao identificados
/monitorar ID_DO_ANUNCIO - escolher so esta oferta ou outras lojas
/monitorar nome ou https://link - procurar anuncios para escolher
/lista - produtos, status e ofertas pendentes
/opcoes PRODUTO_ID - reenviar candidatos com foto e botao de escolha
/confirmar OFERTA_ID - aprovar exatamente o titulo e link exibidos
/historico PRODUTO_ID - ultimas 30 leituras e menores precos por modalidade
/pausar ID - interromper acompanhamento
/retomar ID - reativar e agendar consulta imediata
/remover ID - excluir produto, historico e alertas
/verificar ID - consultar agora, mesmo pausado
/configurar ID reais porcentagem alvo - filtros por produto; use - para remover alvo
/alertas ID todas|quedas - avisar qualquer alteracao ou somente quedas filtradas
Ex.: /configurar 1 50 5 1500 (reais E percentual E alvo)
/ajuda - comandos
/status - versao instalada e modo de acesso das lojas
Busca padrao: diretamente nas lojas, sem chave de API.
Todos os horarios usam America/Sao_Paulo. Frete nao incluido.
Monitoramentos nao expiram. Avisos padrao para aumentos e quedas, com dados comparaveis.
IDs de anuncio, oferta e monitoramento sao diferentes; cada mensagem indica qual usar.
Confirme ofertas somente apos conferir modelo, variante e link.
```

### check_send - linha 129

```text
Falha na verificacao. Dados validos anteriores preservados.
```

### command - linha 141

```text
/ajuda
```

### command - linha 141

```text
/start
```

### command - linha 144

```text
Versao: {VERSION}

```

### command - linha 148

```text
/status
```

### command - linha 150

```text
Versao: {VERSION}
Busca: {config.provider}
Chromium: {'ativado' if config.browser else 'desativado'}
Pichau/Terabyte: descoberta por sitemaps.
Preco e estoque conferidos na oferta; CAPTCHA e robots.txt continuam respeitados.
```

### command - linha 152

```text
/lista
```

### command - linha 157

```text
Monitoramento {p['id']} | Anuncio {p['seed_ad'] or 'legado'}: {p['query']} | {'ativo' if p['active'] else 'pausado'} | abrangencia: {p['scope']} | alertas: {p['alert_mode']} | sem vencimento | proxima: {datetime.fromtimestamp(p['next_due'], ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}
```

### command - linha 167

```text
  Anuncio {c['ad_id'] or 'pendente'} | Oferta {c['id']}: {'confirmada' if c['confirmed'] else 'aguarda confirmacao'} | {c['title']} | ultima leitura: {last[0]['status'] if last else 'pendente'}
{c['url']}
```

### command - linha 169

```text
Nenhum produto.
```

### command - linha 170

```text
/monitorar
```

### command - linha 170

```text
/buscar
```

### command - linha 170

```text
/buscarml
```

### command - linha 173

```text
Informe um nome ou link (ate 600 caracteres).
```

### command - linha 174

```text
/monitorar
```

### command - linha 179

```text
/buscarml
```

### command - linha 183

```text

Nenhum novo cadastro foi criado.
```

### search_send - linha 189

```text
/buscarml
```

### command - linha 192

```text
/buscarml
```

### command - linha 192

```text
🔎 Pesquisando links do Mercado Livre...
```

### command - linha 192

```text
Consultando paginas das ofertas...
```

### command - linha 196

```text
Informe um ID. Veja /ajuda.
```

### command - linha 198

```text
/confirmar
```

### command - linha 202

```text
Oferta inexistente ou sem titulo lido. Execute /verificar PRODUTO_ID.
```

### command - linha 205

```text
Modelo confirmado: 
```

### command - linha 207

```text

A proxima leitura valida registra a base inicial.
```

### command - linha 213

```text
Produto nao encontrado.
```

### command - linha 214

```text
/opcoes
```

### command - linha 217

```text
Nenhuma oferta pendente de escolha. Use /verificar ID para buscar novamente.
```

### command - linha 219

```text
/verificar
```

### command - linha 220

```text
Verificacao solicitada.
```

### command - linha 222

```text
/pausar
```

### command - linha 225

```text
Pausado. Uma leitura ja iniciada pode terminar; alertas ficam suspensos.
```

### command - linha 227

```text
/retomar
```

### command - linha 229

```text
Retomado; consulta agendada.
```

### command - linha 230

```text
/remover
```

### command - linha 232

```text
Produto e dados associados removidos.
```

### command - linha 233

```text
/alertas
```

### command - linha 234

```text
todas
```

### command - linha 234

```text
quedas
```

### command - linha 235

```text
Use /alertas ID todas ou /alertas ID quedas.
```

### command - linha 236

```text
todas
```

### command - linha 239

```text
Avisos de aumentos e quedas ativados.
```

### command - linha 241

```text
Avisos somente de quedas, respeitando os filtros.
```

### command - linha 243

```text
/configurar
```

### command - linha 248

```text
Use /configurar ID reais porcentagem alvo (ou -).
```

### command - linha 265

```text
Filtros atualizados; modo somente quedas ativado. Use /alertas ID todas para voltar a qualquer alteracao.
```

### command - linha 267

```text
/historico
```

### command - linha 282

```text
{when} | oferta {r['cid']} | {r['status']} | {detail}
```

### command - linha 289

```text
Oferta {s['candidate']} | {s['seller']} | {s['condition']} | {s['payment']} | ultimo R$ {s['last'] / 100:.2f}; menor R$ {s['lowest'] / 100:.2f}
```

### command - linha 291

```text
Sem historico.
```

### command - linha 294

```text
Comando ou configuracao invalida. Consulte /ajuda; nenhum erro de leitura representa preco zero.
```

## monitor/presentation.py

### modulo - linha 1

```text
Mensagens de oferta com foto e rotulos claros, sem inferir dados ausentes.
```

### rank_offers - linha 10

```text
Ranking visual da busca, sem alterar series ou regras de alerta.
```

### offer_text - linha 52

```text
{reading.price // 100:,}
```

### offer_text - linha 52

```text
,{reading.price % 100:02d}
```

### offer_text - linha 53

```text
nao lido
```

### offer_text - linha 56

```text
✅ Disponivel segundo a pagina
```

### offer_text - linha 57

```text
❌ INDISPONIVEL
```

### offer_text - linha 58

```text
❓ Nao confirmado pela pagina
```

### offer_text - linha 59

```text
❓ Nao confirmado pela pagina
```

### offer_text - linha 61

```text
🆕 Novo
```

### offer_text - linha 62

```text
⚠️ USADO
```

### offer_text - linha 63

```text
⚠️ RECONDICIONADO
```

### offer_text - linha 64

```text
⚠️ DANIFICADO
```

### offer_text - linha 65

```text
❓ Nao declarada pela pagina
```

### offer_text - linha 70

```text
{MEDALS[rank]} {rank}º menor valor desta busca — {reading.payment[:100]}
```

### offer_text - linha 75

```text
⚠️ Ranking provisorio: condicao nao declarada.
```

### offer_text - linha 77

```text
Ranking entre ofertas da mesma condicao e pagamento.
```

### offer_text - linha 81

```text
🔎 Os modelos desta busca podem ser diferentes; confira o produto.
```

### offer_text - linha 84

```text
🏪 Loja: 
```

### offer_text - linha 86

```text
💰 Preco: {price}
```

### offer_text - linha 87

```text
💳 Pagamento: {reading.payment[:100] or '❓ Nao declarado para este preco'}
```

### offer_text - linha 88

```text
👤 Vendedor: {reading.seller[:100] or '❓ Nao declarado pela pagina'}
```

### offer_text - linha 89

```text
Condicao: {condition}
```

### offer_text - linha 90

```text
Estoque: {stock}
```

### offer_text - linha 91

```text
🚚 Frete nao incluido.
```

### offer_text - linha 105

```text
moeda BRL
```

### offer_text - linha 107

```text
⏸️ Alertas de preco suspensos: falta confirmar 
```

### offer_text - linha 109

```text
🔎 Confira o modelo exato antes de monitorar.
```

### offer_text - linha 111

```text
🆔 Anuncio ID: {ad_id}

```

### offer_text - linha 112

```text

🔔 Monitorar: /monitorar {ad_id}
```

### send_offer - linha 120

```text
🔗 Abrir oferta
```

### send_offer - linha 126

```text
🔔 Monitorar anuncio {ad_id}
```

### send_offer - linha 129

```text
🔗 Abrir oferta
```

### send_offer - linha 137

```text

📋 Detalhes na proxima mensagem.
```

## monitor/search_results.py

### modulo - linha 1

```text
Entrega de buscas com resumo final, sem transformar erros em ofertas.
```

### deliver_search - linha 20

```text
Nenhuma oferta descoberta.
```

### deliver_search - linha 24

```text
Tavily Search
```

### deliver_search - linha 41

```text
falha de leitura nao identificada
```

### deliver_search - linha 41

```text
falha interna de leitura
```

### deliver_search - linha 43

```text

Leitura da pagina: 
```

### deliver_search - linha 46

```text
Nao foi possivel ler esta oferta: 
```

### deliver_search - linha 52

```text
Avisos da pesquisa:

```

### deliver_search - linha 58

```text
Busca interrompida por uma falha. Tente novamente mais tarde.
```

### deliver_search - linha 60

```text
Pesquisa encerrada com falha
```

### deliver_search - linha 60

```text
Pesquisa concluida
```

### deliver_search - linha 61

```text
{status}. Ofertas enviadas: {sent}. Links com falha de leitura: {failed}. Avisos das lojas: {len(notices)}. Links para conferencia: {unverified}.
```

### discovered_text - linha 69

```text
 — link encontrado


```

### discovered_text - linha 71

```text
📌 Fonte: indice externo Tavily Search; titulo ainda nao conferido na pagina.

```

### discovered_text - linha 72

```text
❓ Preco, estoque, vendedor, condicao e pagamento nao verificados.

```

### discovered_text - linha 73

```text
⚠️ Confira o modelo, a oferta e o vendedor ao abrir. Catalogos podem alternar vendedores.

```

### discovered_text - linha 74

```text
⏸️ Este resultado nao ativa monitoramento nem alertas.


```

## monitor/selection.py

### modulo - linha 1

```text
Cartoes e confirmacao de ofertas no Telegram, testaveis sem rede.
```

### identity - linha 8

```text
{candidate['product']}
{candidate['url']}
{candidate['title']}
```

### send_card - linha 26

```text
Monitorar esta oferta
```

### send_card - linha 30

```text
Abrir na loja
```

### send_card - linha 34

```text
Anuncio ID: {candidate['ad_id'] if 'ad_id' in candidate.keys() and candidate['ad_id'] else 'nao atribuido'}
Qual destas ofertas corresponde ao produto que voce quer?
Produto {candidate['product']} | Oferta {candidate['id']}
{candidate['title'][:500]}
Loja: {candidate['store'][:100]}
Confira modelo, Wi-Fi e versao antes de escolher.
A foto e ilustrativa da pagina; nao comprova o modelo ou estoque.
Voce pode escolher mais de uma oferta.
Alternativa: /confirmar {candidate['id']}
```

### send_card - linha 52

```text

Foto indisponivel.
```

### handle_choice - linha 61

```text
Somente o usuario autorizado pode escolher.
```

### handle_choice - linha 66

```text
Escolha invalida.
```

### handle_choice - linha 71

```text
Oferta removida ou alterada. Use /opcoes PRODUTO_ID.
```

### handle_choice - linha 75

```text
Esta oferta ja foi selecionada.
```

### handle_choice - linha 77

```text
Oferta selecionada!
```

### handle_choice - linha 83

```text
Oferta {candidate['id']} selecionada: {candidate['title']}
Produto {candidate['product']}. Somente ofertas confirmadas geram comparacoes.
Consultando para registrar o preco inicial, se os dados forem suficientes.
```

## monitor/subscriptions.py

### modulo - linha 1

```text
Escolha de abrangencia persistente para anuncios encontrados.
```

### ad_fingerprint - linha 10

```text
{ad['id']}
{ad['url']}
{ad['title']}
{ad['title_key']}
```

### ask_scope - linha 19

```text
Anuncio nao encontrado. Execute /buscar nome e use o ID exibido no resultado.
```

### ask_scope - linha 27

```text
So esta oferta neste site
```

### ask_scope - linha 32

```text
Outras lojas tambem
```

### ask_scope - linha 39

```text
Anuncio ID: {ad_id}
{ad['title'][:500]}
{ad['url']}
Onde deseja acompanhar este produto?
Avisarei aumentos e quedas, a cada 5 horas, sem prazo para encerrar.
Outras lojas: somente o mesmo modelo; resultados ambiguos exigem confirmacao.
Bloqueios das lojas e dados insuficientes podem impedir comparacoes.
```

### handle_subscription - linha 54

```text
Somente o usuario autorizado pode escolher.
```

### handle_subscription - linha 63

```text
Escolha invalida.
```

### handle_subscription - linha 68

```text
Escolha antiga ou monitoramento removido. Use /monitorar ID_DO_ANUNCIO.
```

### handle_subscription - linha 74

```text
Monitoramento ativado!
```

### handle_subscription - linha 74

```text
Este monitoramento ja existe.
```

### handle_subscription - linha 82

```text
Monitoramento {pid} ja cadastrado. Use /lista para consultar o status ou /retomar {pid} se estiver pausado.
```

### handle_subscription - linha 86

```text
somente esta oferta
```

### handle_subscription - linha 88

```text
mesmo modelo nas lojas autorizadas que permitirem acesso
```

### handle_subscription - linha 91

```text
✅ Monitoramento {pid} ativado: {scope}.
🚨 Alertas de aumentos e quedas; verificacao a cada 5 horas, sem data de encerramento.
Controle com /pausar {pid}, /retomar {pid} e /historico {pid}.
Registrando o preco inicial. Dados insuficientes suspendem os alertas, sem inventar valores.
```

## monitor/service.py

### options - linha 33

```text
 ORDER BY c.id
```

### options - linha 41

```text
Oferta {candidate['id']}: {candidate['title']}
{candidate['url']}
Escolha com /confirmar {candidate['id']}.
```

### read_snapshot - linha 63

```text
Leituras e HTML da mesma consulta, sem gravar anuncios ou historico.
```

### check - linha 109

```text
Verificacao ja em andamento.
```

### check - linha 113

```text
Produto nao encontrado.
```

### check - linha 140

```text
Nenhuma oferta descoberta nesta consulta. Tente um nome mais curto ou cadastre um link.
```

### check - linha 182

```text
R$ {reading.price / 100:.2f}
```

### check - linha 184

```text
preco nao lido
```

### check - linha 187

```text
Anuncio ID: {ad['id']} | Oferta {candidate['id']}: {reading.title}
{price}; estoque: {reading.stock}; pagamento: {reading.payment or 'nao identificado'}
{info}
{candidate['url']}
```

### check - linha 199

```text
Oferta {candidate['id']}: {code}. Ultimo preco preservado.
```

## monitor/db.py

### __init__ - linha 61

```text
TEXT NOT NULL DEFAULT 'legacy'
```

### __init__ - linha 63

```text
TEXT NOT NULL DEFAULT 'all'
```

### record - linha 236

```text
Pendente: confirme o modelo com /confirmar %s
```

### record - linha 243

```text
Titulo alterado: nova confirmacao necessaria /confirmar %s
```

### record - linha 247

```text
Leitura registrada; faltam dados explicitos para comparar.
```

### record - linha 266

```text
Nova oferta/condicao: preco inicial registrado; sem preco anterior.
```

### record - linha 294

```text
📉 Queda de preco
```

### record - linha 294

```text
📈 Aumento de preco
```

### record - linha 296

```text
Economia
```

### record - linha 296

```text
Aumento
```

### record - linha 298

```text
🚨🚨 ALERTA DE PRECO 🚨🚨
{direction}: {reading.title}
Monitoramento {candidate['product']} | Oferta {candidate['id']}
Loja: {candidate['store']}
Vendedor: {reading.seller}
Condicao: {reading.condition}
Anterior: R$ {row['last'] / 100:.2f}
Atual: R$ {reading.price / 100:.2f}
{variation}: R$ {abs(delta) / 100:.2f} ({abs(delta) / row['last'] * 100:.2f}%)
Menor historico: R$ {min(row['lowest'], reading.price) / 100:.2f}
Pagamento: {reading.payment}
Estoque: disponivel segundo a pagina
Frete nao incluido.
{datetime.fromtimestamp(now, ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}
{candidate['url']}
```

### record - linha 309

```text
Atual: R$ {reading.price / 100:.2f}; menor: R$ {min(row['lowest'], reading.price) / 100:.2f}
```

## monitor/search.py

### modulo - linha 1

```text
Busca descobre URLs; snippets e precos da API nunca sao usados.
```

### search_error_message - linha 10

```text
Adicione mercadolivre.com.br a ALLOWED_DOMAINS no .env e reinicie o servico.
```

### search_error_message - linha 12

```text
A busca por nome nao esta configurada: falta SEARCH_API_KEY no arquivo .env.
Crie uma chave em https://api-dashboard.search.brave.com/ e preencha:
SEARCH_PROVIDER=brave
SEARCH_API_KEY=sua_chave
Depois salve e reinicie o robo. O token do Telegram nao substitui essa chave.
```

### search_error_message - linha 17

```text
A busca por nome esta desativada. Use SEARCH_PROVIDER=direct no .env para pesquisar nas lojas sem chave, ou cadastre um link.
```

### search_error_message - linha 18

```text
SEARCH_PROVIDER invalido. Use direct (sem chave), brave (opcional) ou disabled.
```

### search_error_message - linha 19

```text
A API de busca recusou a chave ou a permissao. Confira sua chave e o acesso no painel Brave Search.
```

### search_error_message - linha 20

```text
A API de busca limitou as consultas. Aguarde antes de tentar novamente.
```

### search_error_message - linha 21

```text
A API de busca nao respondeu apos as tentativas. Tente novamente mais tarde.
```

### search_error_message - linha 22

```text
A API de busca retornou um erro. Confira sua conta e tente novamente.
```

## monitor/discovery.py

### modulo - linha 1

```text
Descoberta em paginas publicas; nenhum preco do catalogo e utilizado.
```

### form_search_url - linha 84

```text
Usar apenas formulario GET realmente declarado pela loja.
```

### modulo - linha 108

```text
Selenium nao instalado; atualize com deploy/update.sh
```

### modulo - linha 109

```text
Amazon recusou ou nao entregou o painel de ofertas
```

### modulo - linha 110

```text
nao foi possivel carregar as opcoes de compra Amazon no navegador
```

### modulo - linha 111

```text
titulo real da pagina nao corresponde ao produto pesquisado
```

### modulo - linha 112

```text
limite da busca externa sem chave atingido; aguarde antes de tentar novamente
```

### modulo - linha 113

```text
indice externo indisponivel; nenhum resultado foi inventado
```

### modulo - linha 114

```text
API oficial exige MERCADOLIVRE_ACCESS_TOKEN no .env
```

### modulo - linha 115

```text
token da API invalido ou expirado; atualize MERCADOLIVRE_ACCESS_TOKEN
```

### modulo - linha 116

```text
API oficial recusou acesso (403); verifique permissoes do aplicativo, token pode nao ser suficiente
```

### modulo - linha 117

```text
API oficial indisponivel ou resposta invalida
```

### modulo - linha 118

```text
exige link de anuncio individual; catalogo pode trocar de vendedor
```

### modulo - linha 119

```text
Chromium indisponivel; execute o instalador com --with-browser
```

### modulo - linha 120

```text
tempo limite ao carregar a pagina no Chromium
```

### modulo - linha 121

```text
conexao com a loja interrompida
```

### modulo - linha 122

```text
falha de navegacao no Chromium
```

### modulo - linha 123

```text
recurso da pagina recusado por seguranca ou falha de rede
```

### modulo - linha 124

```text
pagina sem dados estruturados de um produto unico
```

### modulo - linha 125

```text
redirecionamento para outra loja recusado
```

### modulo - linha 126

```text
acesso bloqueado pela loja; sem tentativa de contorno
```

### modulo - linha 127

```text
CAPTCHA detectado; consulta interrompida
```

### modulo - linha 128

```text
nao foi possivel obter robots.txt; acesso suspenso
```

### modulo - linha 129

```text
robots.txt nao permite esta consulta
```

### modulo - linha 130

```text
formulario de busca nao suportado; exige adaptacao
```

### modulo - linha 131

```text
erro de rede ou limite de consultas
```

### modulo - linha 132

```text
limite de consultas; tentar em outro ciclo
```

### modulo - linha 133

```text
pagina de busca indisponivel
```

### links - linha 155

```text
{domain}: dominio autorizado para links, mas sem adaptador de busca direta. Adicionar o dominio nao instala uma integracao.
```

### links - linha 216

```text
{store.name}: nenhum candidato compativel na fonte consultada (HTML, sitemap limitado ou indice externo). Isso nao prova ausencia do produto.
```

### links - linha 220

```text
falha ao ler a busca
```

### links - linha 222

```text
falha ao ler a busca
```

### links - linha 224

```text
{store.name}: {reason}.
```

### links - linha 226

```text
Mercado Livre: descoberta falhou nesta consulta. Isso nao prova ausencia do produto.
```

## monitor/deals/telegram.py

### modulo - linha 1

```text
Assistente efemero de consulta; nenhum job ou registro de monitoramento.
```

### command - linha 38

```text
Já existe uma pesquisa de promoções em andamento; os demais comandos continuam disponíveis.
```

### command - linha 39

```text
/promocoes
```

### command - linha 41

```text
🏷️ Busca pontual de promoções. Escolha a categoria:
```

### command - linha 41

```text
Hardware
```

### command - linha 44

```text
Inicie com /promocoes. A seleção expira em 30 minutos.
```

### command - linha 46

```text
/descontopromo
```

### command - linha 50

```text
/ceppromo
```

### command - linha 53

```text
Use /ceppromo 01001000. Frete só será incluído se houver cotação verificável; por enquanto será informado como não consultado.
```

### command - linha 55

```text
CEP registrado apenas nesta pesquisa. Frete ainda não é cotado pelos adaptadores; preços serão apresentados sem frete.
```

### command - linha 56

```text
Escolha a etapa pelos botões. Percentual personalizado: /descontopromo >=25,5 na etapa de desconto.
```

### show_stores - linha 66

```text
Todas as lojas habilitadas
```

### show_stores - linha 66

```text
🔎 Pesquisar agora
```

### show_stores - linha 67

```text
Selecione as lojas. Toque para marcar/desmarcar e depois em Pesquisar agora. Opcional: /ceppromo 01001000. A consulta é limitada e não ativa alertas.
```

### callback - linha 77

```text
Seleção expirada ou pesquisa em andamento.
```

### callback - linha 83

```text
Hardware > escolha a subcategoria:
```

### callback - linha 83

```text
Placas-mãe
```

### callback - linha 86

```text
Escolha o desconto anunciado ou use /descontopromo >25,5. >30 exclui 30%; >=30 inclui 30%.
```

### callback - linha 86

```text
Maior que 30%
```

### callback - linha 86

```text
Maior ou igual a 30%
```

### callback - linha 92

```text
Este botão pertence a uma etapa anterior. Use a seleção mais recente.
```

### callback - linha 104

```text
Selecione pelo menos uma loja.
```

### callback - linha 108

```text
🔎 Pesquisa pontual iniciada. Até 2 páginas de categoria e 12 produtos por loja; comparações complementares limitadas. Pode levar alguns minutos. Nenhum monitoramento será criado.
```

### execute - linha 116

```text
Pesquisa de promoções encerrada com falha inesperada. Nenhum acompanhamento foi criado; tente novamente com menos lojas.
```

## monitor/deals/formatting.py

### reais - linha 7

```text
{cents / 100:,.2f}
```

### messages - linha 13

```text
Novo
```

### messages - linha 13

```text
Usado
```

### messages - linha 14

```text
Recondicionado
```

### messages - linha 14

```text
Danificado
```

### messages - linha 14

```text
não declarada
```

### messages - linha 15

```text
🏆 {r.title}
Loja: {offer.store}
De: {reais(offer.previous)}
Por: {reais(r.price)}
Desconto anunciado: {offer.percent:.2f}%
Pagamento: {r.payment or 'não declarado para este preço'}
Vendedor: {r.seller or 'não declarado'}
Condição: {condition}
Estoque: disponível segundo a página
Comparação: {result.comparison}.

```

### messages - linha 23

```text
Modelo declarado: {offer.model}

```

### messages - linha 25

```text
Identificadores: 
```

### messages - linha 25

```text
{k.upper()}: {v}
```

### messages - linha 26

```text
Referência: {offer.reference_source or 'preço anterior explícito da oferta'}.

```

### messages - linha 28

```text
Menor preço comparável: {result.lowest.store}, {reais(result.lowest.reading.price)}.

```

### messages - linha 29

```text
Preços em outras lojas: 
```

### messages - linha 31

```text
nenhuma correspondência confirmada nas mesmas condições.

```

### messages - linha 33

```text
{o.store}: {reais(o.reading.price)} ({o.reading.payment}); {o.url}
```

### messages - linha 34

```text
Cupom: 
```

### messages - linha 34

```text
nenhum requisito confirmado; não foi aplicado desconto adicional
```

### messages - linha 35

```text
Assinatura: 
```

### messages - linha 35

```text
nenhum requisito identificado; confira condições da loja
```

### messages - linha 36

```text
Frete: não incluído; 
```

### messages - linha 36

```text
não consultado para o CEP {report.cep}.
```

### messages - linha 36

```text
CEP não informado.
```

### messages - linha 38

```text
⚠️ Preço de referência suspeito: desconto de 70% ou mais; confira na loja.

```

### messages - linha 41

```text
Link: {offer.url}
```

### messages - linha 44

```text
✅ Pesquisa concluída — {title}; filtro {report.filter}. Ofertas válidas apresentadas: {len(report.results)}.

```

### messages - linha 45

```text
Desconto anunciado calculado sobre a referência da própria loja; não comprova queda histórica. Comparações usam o preço do produto, sem frete.

```

### messages - linha 46

```text
Consulta: {datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}
Cobertura parcial (não é o site inteiro):

```

### messages - linha 48

```text
• {cov.store}: {cov.category_pages} página(s) de categoria tentada(s), {cov.product_pages} oferta(s) tentada(s), {cov.comparison_pages} oferta(s) complementares; {cov.discovery_pages} documento(s) de descoberta complementar ({cov.discovery_loaded} lidos); {cov.discovered} links descobertos, {cov.excluded} produtos sem oferta apta.

```

### messages - linha 54

```text
Contagem por página lógica, sem somar robots.txt, recursos do navegador, redirecionamentos ou retentativas. Descoberta pode usar cache ou índice externo; preços são lidos na oferta. Comparação complementar limitada; não cobre todos os anúncios. Nenhum acompanhamento ou alerta futuro foi cadastrado.
```

## monitor/deals/models.py

### parse - linha 17

```text
Use >30 ou >=30, com percentual entre 0 e 100.
```

### parse - linha 20

```text
Percentual deve estar entre 0 e 100.
```

## monitor/deals/service.py

### modulo - linha 1

```text
Consulta manual limitada e sem qualquer dependencia de banco/agendador.
```

### __init__ - linha 27

```text
Limites devem estar entre 1 e 100.
```

### run - linha 33

```text
Categoria ou loja nao habilitada.
```

### run - linha 35

```text
CEP deve ter oito digitos.
```

### run - linha 37

```text
Ja existe uma consulta de promocoes em andamento.
```

### read - linha 65

```text
Falha de leitura de oferta: 
```

### _run - linha 72

```text
Categoria ainda nao mapeada nesta loja.
```

### _run - linha 89

```text
Nenhum link extraido: pagina vazia ou formato de categoria nao validado.
```

### _run - linha 100

```text
Categoria nao consultada com sucesso: 
```

### _run - linha 104

```text
Limite de {self.limits.category_pages} paginas de categoria atingido.
```

### _run - linha 107

```text
Leitura limitada aos primeiros {self.limits.products_per_store} produtos descobertos.
```

### _run - linha 135

```text
Busca complementar indisponivel; comparacao parcial.
```

### compare_offer - linha 174

```text
comparação não confirmada
```

### compare_offer - linha 176

```text
existe oferta mais barata
```

### compare_offer - linha 176

```text
menor preço encontrado
```

## monitor/deals/adapters/amazon.py

### AmazonCategories - linha 7

```text
Categoria limitada a dados estruturados; HTML de categoria e preco anterior por vendedor ainda nao validados.
```

## monitor/deals/adapters/base.py

### modulo - linha 1

```text
Contratos de categoria. Precos sempre vêm da pagina individual da oferta.
```

### offer - linha 59

```text
Somente metadados atribuidos inequivocamente ao Product principal.
```

### offer - linha 95

```text
Schema.org StrikethroughPrice da mesma oferta
```

## monitor/deals/adapters/kabum.py

### offer - linha 41

```text
/produto/(\d+)(?:/|$)
```

### offer - linha 45

```text
oldPrice do produto na KaBuM
```

### offer - linha 49

```text
KaBuM Prime (exclusividade declarada)
```

### offer - linha 52

```text
Cupom divulgado: 
```

### offer - linha 52

```text
; nao aplicado novamente ao preco.
```

## monitor/deals/adapters/mercadolivre.py

### MercadoLivreCategories - linha 7

```text
Categoria limitada a dados estruturados; acesso real pode ser bloqueado. Catalogos com varios vendedores nao qualificam como oferta individual.
```

## monitor/deals/adapters/pichau.py

### offer - linha 20

```text
Pix
```

### offer - linha 25

```text
preco de/por do bloco principal Pichau
```

## monitor/deals/adapters/terabyte.py

### TerabyteCategories - linha 9

```text
Preco anterior por HTML ainda nao validado nesta loja; somente StrikethroughPrice estruturado da oferta pode qualificar.
```

## monitor/deals/adapters/__init__.py

### modulo - linha 8

```text
Hardware
```

### modulo - linha 8

```text
Placas-mãe
```

# Referencia exata de montagem e botoes

Codigo de referencia, sem configuracao privada. As linhas do catalogo correspondem a esta versao dos arquivos.

## monitor/__main__.py

```python
import asyncio
import logging
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from .config import Config
from .db import DB
from .network import Fetcher
from .search import Search, search_error_message
from .adapters.base import ReadError
from .service import Monitor
from .instance import InstanceLock
from .selection import authorized, send_card, handle_choice
from .search_results import deliver_search
from .adapters import adapter
from .subscriptions import ask_scope, handle_subscription
from .version import VERSION
from .deals.service import Deals
from .deals.telegram import PromotionsTelegram

HELP = """/buscar nome - encontrar anuncios com ID, fotos e medalhas (sem ativar acompanhamento)
/promocoes - busca pontual por categoria, desconto e lojas; sem acompanhamento
/descontopromo >=30 - percentual personalizado na etapa de desconto
/ceppromo 01001000 - informar CEP da consulta (frete ainda nao cotado)
/buscarml nome - descobrir links Mercado Livre; dados nao verificados sao identificados
/monitorar ID_DO_ANUNCIO - escolher so esta oferta ou outras lojas
/monitorar nome ou https://link - procurar anuncios para escolher
/lista - produtos, status e ofertas pendentes
/opcoes PRODUTO_ID - reenviar candidatos com foto e botao de escolha
/confirmar OFERTA_ID - aprovar exatamente o titulo e link exibidos
/historico PRODUTO_ID - ultimas 30 leituras e menores precos por modalidade
/pausar ID - interromper acompanhamento
/retomar ID - reativar e agendar consulta imediata
/remover ID - excluir produto, historico e alertas
/verificar ID - consultar agora, mesmo pausado
/configurar ID reais porcentagem alvo - filtros por produto; use - para remover alvo
/alertas ID todas|quedas - avisar qualquer alteracao ou somente quedas filtradas
Ex.: /configurar 1 50 5 1500 (reais E percentual E alvo)
/ajuda - comandos
/status - versao instalada e modo de acesso das lojas
Busca padrao: diretamente nas lojas, sem chave de API.
Todos os horarios usam America/Sao_Paulo. Frete nao incluido.
Monitoramentos nao expiram. Avisos padrao para aumentos e quedas, com dados comparaveis.
IDs de anuncio, oferta e monitoramento sao diferentes; cada mensagem indica qual usar.
Confirme ofertas somente apos conferir modelo, variante e link."""


async def chunks(send, text):
    # Texto simples: nomes de lojas nao injetam Markdown/HTML.
    for start in range(0, len(text), 3800):
        await send(text[start : start + 3800])


def main():
    config = Config.load()
    instance = InstanceLock(config.db)
    # Bibliotecas HTTP podem registrar URL do Telegram contendo token.
    logging.basicConfig(level=logging.CRITICAL)
    db = DB(config.db)
    fetcher = Fetcher(config)
    tasks = set()

    async def send(text):
        await chunks(lambda t: app.bot.send_message(config.chat, t), text)

    async def send_candidate(candidate):
        await send_card(app.bot, config.chat, candidate)

    monitor = Monitor(
        db, config, fetcher, Search(config, fetcher), send, send_candidate
    )
    search_configuration_error = monitor.search.configuration_error()
    if search_configuration_error:
        print(search_error_message(search_configuration_error), flush=True)

    async def start(app):
        app.bot_data["scheduler"] = asyncio.create_task(monitor.scheduler())

    async def stop(app):
        running = list(tasks) + [app.bot_data["scheduler"]]
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)
        snapshots = list(monitor.snapshot_inflight.values())
        for task in snapshots:
            task.cancel()
        await asyncio.gather(*snapshots, return_exceptions=True)
        await fetcher.close()
        db.conn.close()

    app = (
        Application.builder()
        .token(config.token)
        .concurrent_updates(16)
        .post_init(start)
        .post_stop(stop)
        .build()
    )

    def background(coro):
        task = asyncio.create_task(coro)
        tasks.add(task)

        def done(completed):
            tasks.discard(completed)
            if not completed.cancelled():
                completed.exception()  # Consumir falhas sem imprimir objetos que podem conter tokens.

        task.add_done_callback(done)

    async def send_promotion(text):
        async def formatted(part):
            first, separator, rest = part.partition('\n')
            rendered = ('<b>' + escape(first) + '</b>' + separator + escape(rest)
                        if first.startswith('🏆') else escape(part))
            await app.bot.send_message(config.chat, rendered, parse_mode='HTML')
        await chunks(formatted, text)

    promotions = PromotionsTelegram(config, Deals(monitor), send_promotion, background)
    for name in ('promocoes', 'descontopromo', 'ceppromo'):
        app.add_handler(CommandHandler(name, promotions.command))
    app.add_handler(CallbackQueryHandler(promotions.callback, pattern=r'^promo:'))

    async def check_send(pid):
        try:
            await send(await monitor.check(pid))
        except Exception:
            await send("Falha na verificacao. Dados validos anteriores preservados.")

    async def command(update, context):
        if not authorized(update, config):
            return

        async def reply(text):
            await chunks(update.effective_message.reply_text, text)

        name = update.effective_message.text.split()[0].split("@")[0].lower()
        args = context.args
        try:
            if name in ("/ajuda", "/start"):
                error = monitor.search.configuration_error()
                return await reply(
                    f"Versao: {VERSION}\n"
                    + HELP
                    + ("\n\n" + search_error_message(error) if error else "")
                )
            if name == "/status":
                return await reply(
                    f'Versao: {VERSION}\nBusca: {config.provider}\nChromium: {"ativado" if config.browser else "desativado"}\nPichau/Terabyte: descoberta por sitemaps.\nPreco e estoque conferidos na oferta; CAPTCHA e robots.txt continuam respeitados.'
                )
            if name == "/lista":
                rows = db.rows("SELECT * FROM products ORDER BY id")
                lines = []
                for p in rows:
                    lines.append(
                        f"Monitoramento {p['id']} | Anuncio {p['seed_ad'] or 'legado'}: {p['query']} | {'ativo' if p['active'] else 'pausado'} | abrangencia: {p['scope']} | alertas: {p['alert_mode']} | sem vencimento | proxima: {datetime.fromtimestamp(p['next_due'],ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}"
                    )
                    for c in db.rows(
                        "SELECT * FROM candidates WHERE product=?", (p["id"],)
                    ):
                        last = db.rows(
                            "SELECT status FROM checks WHERE candidate=? ORDER BY id DESC LIMIT 1",
                            (c["id"],),
                        )
                        lines.append(
                            f"  Anuncio {c['ad_id'] or 'pendente'} | Oferta {c['id']}: {'confirmada' if c['confirmed'] else 'aguarda confirmacao'} | {c['title']} | ultima leitura: {last[0]['status'] if last else 'pendente'}\n{c['url']}"
                        )
                return await reply("\n".join(lines) or "Nenhum produto.")
            if name in ("/monitorar", "/buscar", "/buscarml"):
                query = " ".join(args).strip()
                if not query or len(query) > 600:
                    return await reply("Informe um nome ou link (ate 600 caracteres).")
                if name == "/monitorar" and query.isdigit():
                    return await ask_scope(app.bot, config.chat, db, int(query))
                if "://" in query:
                    query, _ = fetcher.canonical(query)
                else:
                    error = monitor.search.configuration_error() if name != '/buscarml' else None
                    if error:
                        return await reply(
                            search_error_message(error)
                            + "\nNenhum novo cadastro foi criado."
                        )

                async def search_send():
                    await deliver_search(
                        monitor, fetcher, db, app.bot, config.chat, query, send,
                        marketplace_only=name == '/buscarml'
                    )

                await reply("🔎 Pesquisando links do Mercado Livre..." if name == '/buscarml' else "Consultando paginas das ofertas...")
                background(search_send())
                return
            if not args:
                return await reply("Informe um ID. Veja /ajuda.")
            pid = int(args[0])
            if name == "/confirmar":
                candidate = db.confirm_candidate(pid)
                if candidate is None:
                    return await reply(
                        "Oferta inexistente ou sem titulo lido. Execute /verificar PRODUTO_ID."
                    )
                await reply(
                    "Modelo confirmado: "
                    + candidate["title"]
                    + "\nA proxima leitura valida registra a base inicial."
                )
                background(check_send(candidate["product"]))
                return
            products = db.rows("SELECT * FROM products WHERE id=?", (pid,))
            if not products:
                return await reply("Produto nao encontrado.")
            if name == "/opcoes":
                if not await monitor.options(pid):
                    await reply(
                        "Nenhuma oferta pendente de escolha. Use /verificar ID para buscar novamente."
                    )
            elif name == "/verificar":
                await reply("Verificacao solicitada.")
                background(check_send(pid))
            elif name == "/pausar":
                db.run("UPDATE products SET active=0 WHERE id=?", (pid,))
                await reply(
                    "Pausado. Uma leitura ja iniciada pode terminar; alertas ficam suspensos."
                )
            elif name == "/retomar":
                db.run("UPDATE products SET active=1,next_due=0 WHERE id=?", (pid,))
                await reply("Retomado; consulta agendada.")
            elif name == "/remover":
                db.run("DELETE FROM products WHERE id=?", (pid,))
                await reply("Produto e dados associados removidos.")
            elif name == "/alertas":
                if len(args) != 2 or args[1].lower() not in ("todas", "quedas"):
                    return await reply("Use /alertas ID todas ou /alertas ID quedas.")
                mode = "all" if args[1].lower() == "todas" else "drops"
                db.run("UPDATE products SET alert_mode=? WHERE id=?", (mode, pid))
                await reply(
                    "Avisos de aumentos e quedas ativados."
                    if mode == "all"
                    else "Avisos somente de quedas, respeitando os filtros."
                )
            elif name == "/configurar":
                from decimal import Decimal

                if len(args) != 4:
                    return await reply(
                        "Use /configurar ID reais porcentagem alvo (ou -)."
                    )
                minimum, percent = Decimal(args[1]), Decimal(args[2])
                target = None if args[3] == "-" else Decimal(args[3])
                values = [minimum, percent] + ([] if target is None else [target])
                if any(not v.is_finite() or v < 0 for v in values):
                    raise ValueError()
                db.run(
                    "UPDATE products SET minimum=?,percent=?,target=?,alert_mode='drops' WHERE id=?",
                    (
                        int(minimum * 100),
                        str(percent),
                        None if target is None else int(target * 100),
                        pid,
                    ),
                )
                await reply(
                    "Filtros atualizados; modo somente quedas ativado. Use /alertas ID todas para voltar a qualquer alteracao."
                )
            elif name == "/historico":
                rows = db.rows(
                    """SELECT h.at,h.status,h.detail,c.id AS cid FROM checks h JOIN candidates c ON c.id=h.candidate
                    WHERE c.product=? ORDER BY h.id DESC LIMIT 30""",
                    (pid,),
                )
                import json

                lines = []
                for r in rows:
                    when = datetime.fromtimestamp(
                        r["at"], ZoneInfo("America/Sao_Paulo")
                    ).isoformat(timespec="seconds")
                    detail = json.loads(r["detail"]) if r["detail"] else {}
                    lines.append(
                        f"{when} | oferta {r['cid']} | {r['status']} | {detail}"
                    )
                for s in db.rows(
                    "SELECT s.* FROM series s JOIN candidates c ON c.id=s.candidate WHERE c.product=?",
                    (pid,),
                ):
                    lines.append(
                        f"Oferta {s['candidate']} | {s['seller']} | {s['condition']} | {s['payment']} | ultimo R$ {s['last']/100:.2f}; menor R$ {s['lowest']/100:.2f}"
                    )
                await reply("\n".join(lines) or "Sem historico.")
        except Exception:
            await reply(
                "Comando ou configuracao invalida. Consulte /ajuda; nenhum erro de leitura representa preco zero."
            )

    for name in (
        "start",
        "ajuda",
        "status",
        "buscar",
        "buscarml",
        "monitorar",
        "lista",
        "opcoes",
        "historico",
        "pausar",
        "retomar",
        "remover",
        "verificar",
        "confirmar",
        "configurar",
        "alertas",
    ):
        app.add_handler(CommandHandler(name, command))

    async def choose(update, context):
        await handle_choice(
            update, config, db, send, lambda pid: background(check_send(pid))
        )

    app.add_handler(CallbackQueryHandler(choose, pattern=r"^choose:"))

    async def subscription(update, context):
        await handle_subscription(
            update, config, db, app.bot, send, lambda pid: background(check_send(pid))
        )

    app.add_handler(CallbackQueryHandler(subscription, pattern=r"^(?:watch|scope):"))

    async def error_handler(update, context):
        # Excecoes omitidas intencionalmente para nao expor credenciais.
        pass

    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=False)
    instance.close()


if __name__ == "__main__":
    main()

```

## monitor/presentation.py

```python
"""Mensagens de oferta com foto e rotulos claros, sem inferir dados ausentes."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .models import normalize

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def rank_offers(offers):
    """Ranking visual da busca, sem alterar series ou regras de alerta."""
    groups, unranked = {}, []
    seen = set()
    for reading, url, store in offers:
        key = (reading.currency, normalize(reading.payment), reading.condition)
        identity = (url,) + key
        if identity in seen:
            continue
        seen.add(identity)
        if (
            not isinstance(reading.price, int)
            or isinstance(reading.price, bool)
            or reading.price <= 0
            or reading.currency != "BRL"
            or not reading.payment
            or reading.stock != "in_stock"
        ):
            unranked.append((reading, url, store, None, False))
        else:
            groups.setdefault(key, []).append((reading, url, store))
    result = []
    for items in groups.values():
        items.sort(key=lambda item: item[0].price)
        levels = {
            price: i + 1
            for i, price in enumerate(sorted({item[0].price for item in items}))
        }
        for reading, url, store in items:
            result.append(
                (
                    reading,
                    url,
                    store,
                    levels[reading.price],
                    not bool(reading.condition),
                )
            )
    return result + unranked


def offer_text(reading, store="", rank=None, provisional=False, ad_id=None):
    price = (
        'R$ ' + f'{reading.price // 100:,}'.replace(',', '.') + f',{reading.price % 100:02d}'
        if reading.price is not None else 'nao lido'
    )
    stock = {
        "in_stock": "✅ Disponivel segundo a pagina",
        "out_of_stock": "❌ INDISPONIVEL",
        "unknown": "❓ Nao confirmado pela pagina",
    }.get(reading.stock, "❓ Nao confirmado pela pagina")
    condition = {
        "NewCondition": "🆕 Novo",
        "UsedCondition": "⚠️ USADO",
        "RefurbishedCondition": "⚠️ RECONDICIONADO",
        "DamagedCondition": "⚠️ DANIFICADO",
    }.get(reading.condition, "❓ Nao declarada pela pagina")
    parts = [reading.title[:350], '']
    if rank in MEDALS:
        parts.insert(
            0,
            f"{MEDALS[rank]} {rank}º menor valor desta busca — {reading.payment[:100]}",
        )
        parts.insert(
            1,
            (
                "⚠️ Ranking provisorio: condicao nao declarada."
                if provisional
                else "Ranking entre ofertas da mesma condicao e pagamento."
            ),
        )
        parts.insert(
            2, "🔎 Os modelos desta busca podem ser diferentes; confira o produto."
        )
    if store:
        parts.append("🏪 Loja: " + store[:80])
    parts += [
        f"💰 Preco: {price}",
        f'💳 Pagamento: {reading.payment[:100] or "❓ Nao declarado para este preco"}',
        f'👤 Vendedor: {reading.seller[:100] or "❓ Nao declarado pela pagina"}',
        f"Condicao: {condition}",
        f"Estoque: {stock}",
        "🚚 Frete nao incluido.",
        '',
    ]
    if not reading.comparable:
        missing = []
        if not reading.condition:
            missing.append("condicao")
        if not reading.payment:
            missing.append("pagamento")
        if not reading.seller:
            missing.append("vendedor")
        if reading.price is None:
            missing.append("preco")
        if reading.currency != "BRL":
            missing.append("moeda BRL")
        parts.append(
            "⏸️ Alertas de preco suspensos: falta confirmar " + ", ".join(missing) + "."
        )
    parts.append("🔎 Confira o modelo exato antes de monitorar.")
    if ad_id is not None:
        parts.insert(0, f"🆔 Anuncio ID: {ad_id}\n")
        parts.append(f"\n🔔 Monitorar: /monitorar {ad_id}")
    return "\n".join(parts)


async def send_offer(
    bot, chat, reading, url, store="", rank=None, provisional=False, ad_id=None
):
    text = offer_text(reading, store, rank, provisional, ad_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Abrir oferta", url=url)]])
    if ad_id is not None:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"🔔 Monitorar anuncio {ad_id}", callback_data=f"watch:{ad_id}"
                    )
                ],
                [InlineKeyboardButton("🔗 Abrir oferta", url=url)],
            ]
        )
    if reading.image:
        fits_caption = len(text.encode('utf-16-le')) // 2 <= 1024
        try:
            await bot.send_photo(
                chat, photo=reading.image,
                caption=text if fits_caption else reading.title[:200] + '\n📋 Detalhes na proxima mensagem.',
                reply_markup=keyboard
            )
        except Exception:
            pass
        else:
            if fits_caption:
                return
    await bot.send_message(chat, text + "\n" + url, reply_markup=keyboard)

```

## monitor/search_results.py

```python
"""Entrega de buscas com resumo final, sem transformar erros em ofertas."""
from .adapters import adapter
from .adapters.base import ReadError
from .discovery import REASONS, relevance
from .presentation import rank_offers, send_offer
from .search import search_error_message


async def deliver_search(monitor, fetcher, db, bot, chat, query, send, marketplace_only=False):
    sent = failed = unverified = 0
    notices = []
    interrupted = False
    try:
        if marketplace_only:
            urls = await monitor.search.marketplace_links(query)
        else:
            urls = [query] if query.startswith('https://') else await monitor.search.links(query)
        notices = getattr(urls, 'notices', [])
        if not urls:
            await send('Nenhuma oferta descoberta.')
        offers = []
        for url in urls:
            candidate = getattr(urls, 'candidates', {}).get(url)
            external = candidate is not None and candidate.source == 'Tavily Search'
            if external:
                _, domain = fetcher.canonical(url)
                if domain == 'mercadolivre.com.br' and not adapter(domain).is_product_url(url):
                    await send(discovered_text(candidate))
                    unverified += 1
                    continue
            try:
                readings = await monitor.read(url)
                if not readings:
                    raise ReadError('structured_product_missing_or_ambiguous')
                if not query.startswith('https://') and any(not relevance(query, r.title) for r in readings):
                    raise ReadError('different_model')
                _, domain = fetcher.canonical(url)
                offers.extend((r, url, adapter(domain).name) for r in readings)
            except Exception as exc:
                failed += 1
                reason = REASONS.get(str(exc), 'falha de leitura nao identificada') if isinstance(exc, ReadError) else 'falha interna de leitura'
                if external:
                    await send(discovered_text(candidate) + '\nLeitura da pagina: ' + reason + '.')
                    unverified += 1
                else:
                    await send('Nao foi possivel ler esta oferta: ' + reason + '.\n' + url)
        for r, url, store, rank, provisional in rank_offers(offers):
            ad = db.save_ad(url, store, r)
            await send_offer(bot, chat, r, url, store, rank, provisional, ad['id'])
            sent += 1
        if notices:
            await send('Avisos da pesquisa:\n' + '\n'.join(notices))
    except ReadError as exc:
        interrupted = True
        await send(search_error_message(str(exc)))
    except Exception:
        interrupted = True
        await send('Busca interrompida por uma falha. Tente novamente mais tarde.')
    finally:
        status = 'Pesquisa encerrada com falha' if interrupted else 'Pesquisa concluida'
        await send(f'{status}. Ofertas enviadas: {sent}. Links com falha de leitura: {failed}. Avisos das lojas: {len(notices)}. Links para conferencia: {unverified}.')


def discovered_text(candidate):
    from urllib.parse import urlsplit
    domain = urlsplit(candidate.url).hostname.removeprefix('www.')
    store = adapter('mercadolivre.com.br' if domain == 'produto.mercadolivre.com.br' else domain).name
    return (
        '🔎 ' + store + ' — link encontrado\n\n'
        + candidate.title[:350] + '\n\n'
        + '📌 Fonte: indice externo Tavily Search; titulo ainda nao conferido na pagina.\n'
        + '❓ Preco, estoque, vendedor, condicao e pagamento nao verificados.\n'
        + '⚠️ Confira o modelo, a oferta e o vendedor ao abrir. Catalogos podem alternar vendedores.\n'
        + '⏸️ Este resultado nao ativa monitoramento nem alertas.\n\n'
        + '🔗 ' + candidate.url
    )

```

## monitor/selection.py

```python
"""Cartoes e confirmacao de ofertas no Telegram, testaveis sem rede."""

import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def identity(candidate):
    value = f"{candidate['product']}\n{candidate['url']}\n{candidate['title']}"
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def authorized(update, config):
    return bool(
        update.effective_user
        and update.effective_chat
        and update.effective_user.id == config.user
        and update.effective_chat.id == config.chat
    )


async def send_card(bot, chat, candidate):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Monitorar esta oferta",
                    callback_data=f"choose:{candidate['id']}:{identity(candidate)}",
                )
            ],
            [InlineKeyboardButton("Abrir na loja", url=candidate["url"])],
        ]
    )
    text = (
        f"Anuncio ID: {candidate['ad_id'] if 'ad_id' in candidate.keys() and candidate['ad_id'] else 'nao atribuido'}\n"
        f"Qual destas ofertas corresponde ao produto que voce quer?\n"
        f"Produto {candidate['product']} | Oferta {candidate['id']}\n"
        f"{candidate['title'][:500]}\nLoja: {candidate['store'][:100]}\n"
        f"Confira modelo, Wi-Fi e versao antes de escolher.\n"
        f"A foto e ilustrativa da pagina; nao comprova o modelo ou estoque.\n"
        f"Voce pode escolher mais de uma oferta.\n"
        f"Alternativa: /confirmar {candidate['id']}"
    )
    if candidate["image"]:
        try:
            await bot.send_photo(
                chat, photo=candidate["image"], caption=text, reply_markup=keyboard
            )
            return
        except Exception:
            # Imagem bloqueada, invalida ou grande: manter a escolha por texto.
            pass
    await bot.send_message(chat, text + "\nFoto indisponivel.", reply_markup=keyboard)


async def handle_choice(update, config, db, send, on_confirm=None):
    query = update.callback_query
    if not query:
        return
    if not authorized(update, config):
        await query.answer(
            "Somente o usuario autorizado pode escolher.", show_alert=True
        )
        return
    parts = (query.data or "").split(":")
    if len(parts) != 3 or parts[0] != "choose" or not parts[1].isdigit():
        await query.answer("Escolha invalida.", show_alert=True)
        return
    candidate = db.confirm_candidate(int(parts[1]), parts[2])
    if candidate is None:
        await query.answer(
            "Oferta removida ou alterada. Use /opcoes PRODUTO_ID.", show_alert=True
        )
        return
    if candidate["confirmed"]:
        await query.answer("Esta oferta ja foi selecionada.")
        return
    await query.answer("Oferta selecionada!")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await send(
        f"Oferta {candidate['id']} selecionada: {candidate['title']}\n"
        f"Produto {candidate['product']}. Somente ofertas confirmadas geram comparacoes.\n"
        f"Consultando para registrar o preco inicial, se os dados forem suficientes."
    )
    if on_confirm:
        on_confirm(candidate["product"])

```

## monitor/subscriptions.py

```python
"""Escolha de abrangencia persistente para anuncios encontrados."""

import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .selection import authorized


def ad_fingerprint(ad):
    return hashlib.sha256(
        f"{ad['id']}\n{ad['url']}\n{ad['title']}\n{ad['title_key']}".encode()
    ).hexdigest()[:20]


async def ask_scope(bot, chat, db, ad_id):
    ad = db.get_ad(ad_id)
    if ad is None:
        await bot.send_message(
            chat,
            "Anuncio nao encontrado. Execute /buscar nome e use o ID exibido no resultado.",
        )
        return
    token = db.request_scope(ad_id)
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "So esta oferta neste site", callback_data=f"scope:{token}:site"
                )
            ],
            [
                InlineKeyboardButton(
                    "Outras lojas tambem", callback_data=f"scope:{token}:all"
                )
            ],
        ]
    )
    await bot.send_message(
        chat,
        f"Anuncio ID: {ad_id}\n{ad['title'][:500]}\n{ad['url']}\n"
        "Onde deseja acompanhar este produto?\n"
        "Avisarei aumentos e quedas, a cada 5 horas, sem prazo para encerrar.\n"
        "Outras lojas: somente o mesmo modelo; resultados ambiguos exigem confirmacao.\n"
        "Bloqueios das lojas e dados insuficientes podem impedir comparacoes.",
        reply_markup=markup,
    )


async def handle_subscription(update, config, db, bot, send, on_confirm):
    query = update.callback_query
    if not query:
        return
    if not authorized(update, config):
        await query.answer(
            "Somente o usuario autorizado pode escolher.", show_alert=True
        )
        return
    parts = (query.data or "").split(":")
    if len(parts) == 2 and parts[0] == "watch" and parts[1].isdigit():
        await query.answer()
        await ask_scope(bot, config.chat, db, int(parts[1]))
        return
    if len(parts) != 3 or parts[0] != "scope" or parts[2] not in ("site", "all"):
        await query.answer("Escolha invalida.", show_alert=True)
        return
    result = db.subscribe(parts[1], parts[2], config)
    if result is None or result[0] is None:
        await query.answer(
            "Escolha antiga ou monitoramento removido. Use /monitorar ID_DO_ANUNCIO.",
            show_alert=True,
        )
        return
    pid, created = result
    await query.answer(
        "Monitoramento ativado!" if created else "Este monitoramento ja existe."
    )
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    if not created:
        await send(
            f"Monitoramento {pid} ja cadastrado. Use /lista para consultar o status ou /retomar {pid} se estiver pausado."
        )
        return
    scope = (
        "somente esta oferta"
        if parts[2] == "site"
        else "mesmo modelo nas lojas autorizadas que permitirem acesso"
    )
    await send(
        f"✅ Monitoramento {pid} ativado: {scope}.\n"
        "🚨 Alertas de aumentos e quedas; verificacao a cada 5 horas, sem data de encerramento.\n"
        f"Controle com /pausar {pid}, /retomar {pid} e /historico {pid}.\n"
        "Registrando o preco inicial. Dados insuficientes suspendem os alertas, sem inventar valores."
    )
    on_confirm(pid)

```

## monitor/service.py

```python
async def options(self, pid, only_new=False):
        extra = " AND c.notified=0 AND p.active=1" if only_new else ""
        pending = self.db.rows(
            """SELECT c.* FROM candidates c JOIN products p ON p.id=c.product
            WHERE c.product=? AND c.confirmed=0 AND c.title<>''"""
            + extra
            + " ORDER BY c.id",
            (pid,),
        )
        for candidate in pending:
            if self.send_candidate:
                await self.send_candidate(candidate)
            else:
                await self.send(
                    f"Oferta {candidate['id']}: {candidate['title']}\n{candidate['url']}\nEscolha com /confirmar {candidate['id']}."
                )
            self.db.run(
                "UPDATE candidates SET notified=1 WHERE id=?", (candidate["id"],)
            )
        return len(pending)

async def check(self, pid):
        lock = self.locks.setdefault(pid, asyncio.Lock())
        if lock.locked():
            return "Verificacao ja em andamento."
        async with lock:
            products = self.db.rows("SELECT * FROM products WHERE id=?", (pid,))
            if not products:
                return "Produto nao encontrado."
            p = products[0]
            seed_ad = self.db.get_ad(p["seed_ad"]) if p["seed_ad"] else None
            seed_reading = (
                Reading(**json.loads(seed_ad["reading"])) if seed_ad else None
            )
            notes = []
            try:
                if p["query"].startswith("https://"):
                    urls = [p["query"]]
                else:
                    try:
                        urls = await self.search.links(p["query"])
                        notes.extend(getattr(urls, "notices", []))
                    except ReadError as exc:
                        urls = []
                        notes.append(search_error_message(str(exc)))
                if seed_ad and seed_ad["url"] not in urls:
                    urls = list(urls) + [seed_ad["url"]]
                for url in urls:
                    _, domain = self.fetcher.canonical(url)
                    self.db.candidate(pid, url, adapter(domain).name)
                candidates = self.db.rows(
                    "SELECT * FROM candidates WHERE product=? ORDER BY id", (pid,)
                )
                if not candidates and not notes:
                    notes.append(
                        "Nenhuma oferta descoberta nesta consulta. Tente um nome mais curto ou cadastre um link."
                    )
                for candidate in candidates:
                    try:
                        readings = await self.read(candidate["url"])
                        # Produto pode ter sido removido enquanto aguardava a rede.
                        current = self.db.rows(
                            "SELECT * FROM candidates WHERE id=?", (candidate["id"],)
                        )
                        if not current:
                            continue
                        for reading in readings:
                            relation = (
                                same_product(seed_reading, reading)
                                if seed_reading
                                else None
                            )
                            if relation is False:
                                self.db.failure(candidate["id"], "different_model")
                                continue
                            ad = self.db.save_ad(
                                candidate["url"], candidate["store"], reading
                            )
                            self.db.run(
                                "UPDATE candidates SET ad_id=? WHERE id=?",
                                (ad["id"], candidate["id"]),
                            )
                            if (
                                p["scope"] == "all"
                                and relation is True
                                and not current[0]["confirmed"]
                            ):
                                self.db.run(
                                    "UPDATE candidates SET confirmed=1,title=? WHERE id=?",
                                    (reading.title, candidate["id"]),
                                )
                            fresh = self.db.rows(
                                "SELECT * FROM candidates WHERE id=?",
                                (candidate["id"],),
                            )[0]
                            info = self.db.record(fresh, reading)
                            price = (
                                f"R$ {reading.price/100:.2f}"
                                if reading.price is not None
                                else "preco nao lido"
                            )
                            notes.append(
                                f"Anuncio ID: {ad['id']} | Oferta {candidate['id']}: {reading.title}\n{price}; estoque: {reading.stock}; pagamento: {reading.payment or 'nao identificado'}\n{info}\n{candidate['url']}"
                            )
                    except Exception as exc:
                        # Nunca colocar excecoes de bibliotecas/URLs com tokens em logs ou mensagens.
                        code = (
                            str(exc) if isinstance(exc, ReadError) else "reading_error"
                        )
                        if self.db.rows(
                            "SELECT id FROM candidates WHERE id=?", (candidate["id"],)
                        ):
                            self.db.failure(candidate["id"], code)
                        notes.append(
                            f"Oferta {candidate['id']}: {code}. Ultimo preco preservado."
                        )
                await self.options(pid, only_new=True)
                await self.deliver()
            finally:
                self.db.run(
                    "UPDATE products SET next_due=? WHERE id=?",
                    (time.time() + self.config.interval, pid),
                )
            return "\n\n".join(notes)
```

## monitor/db.py

```python
def record(self, candidate, reading):
        now = time.time()
        with self.conn:
            self.conn.execute(
                "UPDATE candidates SET image=? WHERE id=?",
                (reading.image, candidate["id"]),
            )
            self.conn.execute(
                "INSERT INTO checks(candidate,at,status,detail) VALUES (?,?,?,?)",
                (
                    candidate["id"],
                    now,
                    "ok",
                    json.dumps(asdict(reading), ensure_ascii=False),
                ),
            )
            if not candidate["confirmed"]:
                self.conn.execute(
                    "UPDATE candidates SET title=? WHERE id=?",
                    (reading.title, candidate["id"]),
                )
                return "Pendente: confirme o modelo com /confirmar %s" % candidate["id"]
            if normalize(candidate["title"]) != normalize(reading.title):
                self.conn.execute(
                    "UPDATE candidates SET confirmed=0,notified=0,title=? WHERE id=?",
                    (reading.title, candidate["id"]),
                )
                return (
                    "Titulo alterado: nova confirmacao necessaria /confirmar %s"
                    % candidate["id"]
                )
            if not reading.comparable:
                return "Leitura registrada; faltam dados explicitos para comparar."
            key = (
                candidate["id"],
                normalize(reading.title),
                reading.seller,
                reading.condition,
                reading.payment,
                reading.currency,
            )
            row = self.conn.execute(
                "SELECT * FROM series WHERE candidate=? AND title=? AND seller=? AND condition=? AND payment=? AND currency=?",
                key,
            ).fetchone()
            if row is None:
                cursor = self.conn.execute(
                    "INSERT INTO series(candidate,title,seller,condition,payment,currency,last,lowest) VALUES (?,?,?,?,?,?,?,?)",
                    key + (reading.price, reading.price),
                )
                sid = cursor.lastrowid
                result = "Nova oferta/condicao: preco inicial registrado; sem preco anterior."
            else:
                sid = row["id"]
                episode = row["episode"] + int(row["last"] != reading.price)
                self.conn.execute(
                    "UPDATE series SET last=?,lowest=MIN(lowest,?),episode=? WHERE id=?",
                    (reading.price, reading.price, episode, sid),
                )
                p = self.conn.execute(
                    "SELECT * FROM products WHERE id=?", (candidate["product"],)
                ).fetchone()
                changed = reading.price != row["last"]
                notify = changed and (
                    p["alert_mode"] == "all"
                    or qualifies(
                        row["last"],
                        reading.price,
                        p["minimum"],
                        p["percent"],
                        p["target"],
                    )
                )
                if reading.stock == "in_stock" and notify:
                    delta = row["last"] - reading.price
                    from datetime import datetime
                    from zoneinfo import ZoneInfo

                    direction = (
                        "📉 Queda de preco" if delta > 0 else "📈 Aumento de preco"
                    )
                    variation = "Economia" if delta > 0 else "Aumento"
                    msg = (
                        f"🚨🚨 ALERTA DE PRECO 🚨🚨\n{direction}: {reading.title}\nMonitoramento {candidate['product']} | Oferta {candidate['id']}\nLoja: {candidate['store']}\nVendedor: {reading.seller}\n"
                        f"Condicao: {reading.condition}\nAnterior: R$ {row['last']/100:.2f}\nAtual: R$ {reading.price/100:.2f}\n"
                        f"{variation}: R$ {abs(delta)/100:.2f} ({abs(delta)/row['last']*100:.2f}%)\n"
                        f"Menor historico: R$ {min(row['lowest'],reading.price)/100:.2f}\nPagamento: {reading.payment}\n"
                        f"Estoque: disponivel segundo a pagina\nFrete nao incluido.\n"
                        f"{datetime.fromtimestamp(now,ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}\n{candidate['url']}"
                    )
                    self.conn.execute(
                        "INSERT OR IGNORE INTO alerts(series,episode,message) VALUES (?,?,?)",
                        (sid, episode, msg),
                    )
                result = f'Atual: R$ {reading.price/100:.2f}; menor: R$ {min(row["lowest"],reading.price)/100:.2f}'
            self.conn.execute(
                "INSERT INTO prices(series,at,price,stock) VALUES (?,?,?,?)",
                (sid, now, reading.price, reading.stock),
            )
        return result
```

## monitor/search.py

```python
def search_error_message(code):
    return {
        'marketplace_not_authorized': 'Adicione mercadolivre.com.br a ALLOWED_DOMAINS no .env e reinicie o servico.',
        "search_not_configured": (
            "A busca por nome nao esta configurada: falta SEARCH_API_KEY no arquivo .env.\n"
            "Crie uma chave em https://api-dashboard.search.brave.com/ e preencha:\n"
            "SEARCH_PROVIDER=brave\nSEARCH_API_KEY=sua_chave\n"
            "Depois salve e reinicie o robo. O token do Telegram nao substitui essa chave."
        ),
        "search_disabled": "A busca por nome esta desativada. Use SEARCH_PROVIDER=direct no .env para pesquisar nas lojas sem chave, ou cadastre um link.",
        "search_provider_invalid": "SEARCH_PROVIDER invalido. Use direct (sem chave), brave (opcional) ou disabled.",
        "search_auth_error": "A API de busca recusou a chave ou a permissao. Confira sua chave e o acesso no painel Brave Search.",
        "search_rate_limit_deferred": "A API de busca limitou as consultas. Aguarde antes de tentar novamente.",
        "search_unavailable": "A API de busca nao respondeu apos as tentativas. Tente novamente mais tarde.",
    }.get(code, "A API de busca retornou um erro. Confira sua conta e tente novamente.")
```

## monitor/discovery.py

```python
REASONS = {
    'selenium_not_installed': 'Selenium nao instalado; atualize com deploy/update.sh',
    'amazon_offers_http_error': 'Amazon recusou ou nao entregou o painel de ofertas',
    'amazon_offers_unavailable': 'nao foi possivel carregar as opcoes de compra Amazon no navegador',
    'different_model': 'titulo real da pagina nao corresponde ao produto pesquisado',
    'external_search_limited': 'limite da busca externa sem chave atingido; aguarde antes de tentar novamente',
    'external_search_unavailable': 'indice externo indisponivel; nenhum resultado foi inventado',
    'mercadolivre_api_token_missing': 'API oficial exige MERCADOLIVRE_ACCESS_TOKEN no .env',
    'mercadolivre_api_token_expired': 'token da API invalido ou expirado; atualize MERCADOLIVRE_ACCESS_TOKEN',
    'mercadolivre_api_access_denied': 'API oficial recusou acesso (403); verifique permissoes do aplicativo, token pode nao ser suficiente',
    'mercadolivre_api_failed': 'API oficial indisponivel ou resposta invalida',
    "marketplace_individual_listing_required": "exige link de anuncio individual; catalogo pode trocar de vendedor",
    "browser_not_installed": "Chromium indisponivel; execute o instalador com --with-browser",
    "browser_navigation_failed_TimeoutError": "tempo limite ao carregar a pagina no Chromium",
    "browser_connection_failed": "conexao com a loja interrompida",
    "browser_navigation_failed_Error": "falha de navegacao no Chromium",
    "browser_resource_refused": "recurso da pagina recusado por seguranca ou falha de rede",
    "structured_product_missing_or_ambiguous": "pagina sem dados estruturados de um produto unico",
    "redirect_changed_store": "redirecionamento para outra loja recusado",
    "blocked_no_bypass": "acesso bloqueado pela loja; sem tentativa de contorno",
    "captcha_no_bypass": "CAPTCHA detectado; consulta interrompida",
    "robots_unavailable": "nao foi possivel obter robots.txt; acesso suspenso",
    "robots_disallowed": "robots.txt nao permite esta consulta",
    "search_form_not_supported": "formulario de busca nao suportado; exige adaptacao",
    "network_or_rate_limit": "erro de rede ou limite de consultas",
    "rate_limit_deferred": "limite de consultas; tentar em outro ciclo",
    "page_removed": "pagina de busca indisponivel",
}
```

## monitor/deals/telegram.py

```python
"""Assistente efemero de consulta; nenhum job ou registro de monitoramento."""
import secrets
import time
from dataclasses import dataclass, field
from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard
from ..selection import authorized
from .adapters import ADAPTERS
from .models import DiscountFilter
from .formatting import messages


@dataclass
class Session:
    nonce: str = field(default_factory=lambda: secrets.token_hex(4))
    created: float = field(default_factory=time.monotonic)
    stage: str = 'category'
    discount: DiscountFilter | None = None
    stores: set = field(default_factory=set)
    cep: str = ''


class PromotionsTelegram:
    def __init__(self, config, deals, send, background):
        self.config, self.deals, self.send, self.background = config, deals, send, background
        self.session = None
        self.running = False

    @property
    def domains(self):
        return [d for d in ADAPTERS if d in self.config.domains]

    async def command(self, update, context):
        if not authorized(update, self.config):
            return
        reply = update.effective_message.reply_text
        name = update.effective_message.text.split()[0].split('@')[0].lower()
        if self.running:
            return await reply('Já existe uma pesquisa de promoções em andamento; os demais comandos continuam disponíveis.')
        if name == '/promocoes':
            self.session = Session(stores=set(self.domains))
            return await reply('🏷️ Busca pontual de promoções. Escolha a categoria:', reply_markup=self.keyboard([('Hardware', 'hardware')]))
        session = self.session
        if not session or time.monotonic() - session.created > 1800:
            return await reply('Inicie com /promocoes. A seleção expira em 30 minutos.')
        try:
            if name == '/descontopromo' and session.stage == 'filter':
                session.discount = DiscountFilter.parse(' '.join(context.args))
                session.stage = 'stores'
                return await self.show_stores(reply)
            if name == '/ceppromo':
                cep = ''.join(context.args).replace('-', '')
                if len(cep) != 8 or not cep.isdigit():
                    raise ValueError('Use /ceppromo 01001000. Frete só será incluído se houver cotação verificável; por enquanto será informado como não consultado.')
                session.cep = cep
                return await reply('CEP registrado apenas nesta pesquisa. Frete ainda não é cotado pelos adaptadores; preços serão apresentados sem frete.')
            return await reply('Escolha a etapa pelos botões. Percentual personalizado: /descontopromo >=25,5 na etapa de desconto.')
        except ValueError as exc:
            return await reply(str(exc))

    def keyboard(self, buttons):
        return Keyboard([[Button(label, callback_data=f'promo:{self.session.nonce}:{action}')] for label, action in buttons])

    async def show_stores(self, reply):
        choices = [('✅ ' if d in self.session.stores else '⬜ ') + ADAPTERS[d].store for d in self.domains]
        buttons = [(label, 'store' + str(i)) for i, label in enumerate(choices)]
        buttons += [('Todas as lojas habilitadas', 'all'), ('🔎 Pesquisar agora', 'run')]
        return await reply('Selecione as lojas. Toque para marcar/desmarcar e depois em Pesquisar agora. Opcional: /ceppromo 01001000. A consulta é limitada e não ativa alertas.', reply_markup=self.keyboard(buttons))

    async def callback(self, update, context):
        if not authorized(update, self.config):
            return
        query = update.callback_query
        session = self.session
        parts = (query.data or '').split(':')
        if (len(parts) != 3 or not session or session.nonce != parts[1]
                or time.monotonic() - session.created > 1800 or self.running):
            return await query.answer('Seleção expirada ou pesquisa em andamento.', show_alert=True)
        await query.answer()
        action = parts[2]
        reply = query.message.reply_text
        if action == 'hardware' and session.stage == 'category':
            session.stage = 'subcategory'
            return await reply('Hardware > escolha a subcategoria:', reply_markup=self.keyboard([('Placas-mãe', 'motherboards')]))
        if action == 'motherboards' and session.stage == 'subcategory':
            session.stage = 'filter'
            return await reply('Escolha o desconto anunciado ou use /descontopromo >25,5. >30 exclui 30%; >=30 inclui 30%.', reply_markup=self.keyboard([('Maior que 30%', 'gt30'), ('Maior ou igual a 30%', 'ge30')]))
        if action in ('gt30', 'ge30') and session.stage == 'filter':
            session.discount = DiscountFilter.parse('>30' if action == 'gt30' else '>=30')
            session.stage = 'stores'
            return await self.show_stores(reply)
        if session.stage != 'stores':
            return await reply('Este botão pertence a uma etapa anterior. Use a seleção mais recente.')
        if action == 'all':
            session.stores = set(self.domains)
            return await self.show_stores(reply)
        if action.startswith('store') and action[5:].isdigit():
            index = int(action[5:])
            if index < len(self.domains):
                domain = self.domains[index]
                session.stores.symmetric_difference_update({domain})
                return await self.show_stores(reply)
        if action == 'run':
            if not session.stores:
                return await reply('Selecione pelo menos uma loja.')
            self.running = True  # Antes do primeiro await: callbacks duplicados nao iniciam outro job.
            session.stage = 'running'
            self.background(self.execute(session))
            await reply('🔎 Pesquisa pontual iniciada. Até 2 páginas de categoria e 12 produtos por loja; comparações complementares limitadas. Pode levar alguns minutos. Nenhum monitoramento será criado.')

    async def execute(self, session):
        try:
            report = await self.deals.run('hardware/placas-mae', session.discount, sorted(session.stores), session.cep)
            for text in messages(report):
                await self.send(text)
        except Exception:
            await self.send('Pesquisa de promoções encerrada com falha inesperada. Nenhum acompanhamento foi criado; tente novamente com menos lojas.')
        finally:
            self.running = False
            self.session = None

```

## monitor/deals/formatting.py

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from .adapters import CATEGORIES


def reais(cents):
    return 'R$ ' + f'{cents / 100:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def messages(report):
    for result in report.results:
        offer, r = result.offer, result.offer.reading
        condition = {'NewCondition': 'Novo', 'UsedCondition': 'Usado',
                     'RefurbishedCondition': 'Recondicionado', 'DamagedCondition': 'Danificado'}.get(r.condition, 'não declarada')
        text = (f'🏆 {r.title}\nLoja: {offer.store}\n'
                f'De: {reais(offer.previous)}\nPor: {reais(r.price)}\n'
                f'Desconto anunciado: {offer.percent:.2f}%\n'
                f'Pagamento: {r.payment or "não declarado para este preço"}\n'
                f'Vendedor: {r.seller or "não declarado"}\n'
                f'Condição: {condition}\n'
                f'Estoque: disponível segundo a página\nComparação: {result.comparison}.\n')
        if offer.model:
            text += f'Modelo declarado: {offer.model}\n'
        if r.identifiers:
            text += 'Identificadores: ' + '; '.join(f'{k.upper()}: {v}' for k, v in r.identifiers.items()) + '\n'
        text += f'Referência: {offer.reference_source or "preço anterior explícito da oferta"}.\n'
        if result.lowest:
            text += f'Menor preço comparável: {result.lowest.store}, {reais(result.lowest.reading.price)}.\n'
        text += 'Preços em outras lojas: '
        if len(result.options) == 1:
            text += 'nenhuma correspondência confirmada nas mesmas condições.\n'
        else:
            text += '\n' + '\n'.join(f'{o.store}: {reais(o.reading.price)} ({o.reading.payment}); {o.url}' for o in result.options[1:]) + '\n'
        text += 'Cupom: ' + (offer.coupon or 'nenhum requisito confirmado; não foi aplicado desconto adicional') + '\n'
        text += 'Assinatura: ' + (offer.members or 'nenhum requisito identificado; confira condições da loja') + '\n'
        text += 'Frete: não incluído; ' + (f'não consultado para o CEP {report.cep}.' if report.cep else 'CEP não informado.') + '\n'
        if offer.suspicious:
            text += '⚠️ Preço de referência suspeito: desconto de 70% ou mais; confira na loja.\n'
        if offer.notes:
            text += '\n'.join(offer.notes) + '\n'
        text += f'Link: {offer.url}'
        yield text
    title = ' > '.join(CATEGORIES[report.category])
    text = f'✅ Pesquisa concluída — {title}; filtro {report.filter}. Ofertas válidas apresentadas: {len(report.results)}.\n'
    text += 'Desconto anunciado calculado sobre a referência da própria loja; não comprova queda histórica. Comparações usam o preço do produto, sem frete.\n'
    text += f'Consulta: {datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")}\nCobertura parcial (não é o site inteiro):\n'
    for cov in report.coverage:
        text += (f'• {cov.store}: {cov.category_pages} página(s) de categoria tentada(s), '
                 f'{cov.product_pages} oferta(s) tentada(s), {cov.comparison_pages} oferta(s) complementares; '
                 f'{cov.discovery_pages} documento(s) de descoberta complementar ({cov.discovery_loaded} lidos); '
                 f'{cov.discovered} links descobertos, {cov.excluded} produtos sem oferta apta.\n')
        if cov.notices:
            text += '\n'.join('  ⚠️ ' + n for n in dict.fromkeys(cov.notices)) + '\n'
    text += 'Contagem por página lógica, sem somar robots.txt, recursos do navegador, redirecionamentos ou retentativas. Descoberta pode usar cache ou índice externo; preços são lidos na oferta. Comparação complementar limitada; não cobre todos os anúncios. Nenhum acompanhamento ou alerta futuro foi cadastrado.'
    yield text

```

## monitor/deals/models.py

```python
class DiscountFilter:
    inclusive: bool
    value: Decimal

    @classmethod
    def parse(cls, text):
        match = re.fullmatch(r'\s*(>=|>)\s*(\d{1,3}(?:[.,]\d{1,4})?)\s*%?\s*', text)
        if not match:
            raise ValueError('Use >30 ou >=30, com percentual entre 0 e 100.')
        value = Decimal(match[2].replace(',', '.'))
        if value > 100:
            raise ValueError('Percentual deve estar entre 0 e 100.')
        return cls(match[1] == '>=', value)

    def accepts(self, old, current):
        if not valid_price(old) or not valid_price(current) or old <= current:
            return False
        left, right = Decimal(old - current) * 100, self.value * old
        return left >= right if self.inclusive else left > right

    def __str__(self):
        return ('>=' if self.inclusive else '>') + str(self.value) + '%'
```
