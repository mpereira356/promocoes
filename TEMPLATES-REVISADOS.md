# Templates revisados do bot para Telegram

Revisão editorial de clareza, hierarquia visual, pontuação e acentuação. Os textos abaixo são propostas para substituir as mensagens exibidas pelo bot; não foram alterados código, regras, cálculos ou integrações.

## Convenções de aplicação

- Usar quebras de linha e blocos curtos para leitura no celular.

- Formatação sugerida em texto simples: os rótulos em negrito são apenas hierarquia editorial; se o bot não usar `parse_mode`, manter os rótulos sem os asteriscos.

- Manter literalmente comandos, argumentos, IDs e placeholders entre chaves.

- Não omitir ressalvas sobre dados não verificados, frete, cobertura parcial, bloqueios ou erros.

- Em resultados de `/promocoes`, usar sempre 🏆 como marcador de cada oferta. Medalhas 🥇🥈🥉 ficam exclusivas do ranking da busca comum.

- `/promocoes` é uma consulta pontual; não cria monitoramento nem alertas futuros.

---

# 1. Ajuda e comandos

## `/ajuda` e `/start`

```
🛍️ *Bot de ofertas e monitoramento*

*BUSCAS*
/buscar nome — buscar ofertas com ID, fotos e medalhas. Não ativa acompanhamento.
/buscarml nome — encontrar links do Mercado Livre. Resultados ainda não verificados serão identificados.
/promocoes — busca pontual por categoria, desconto e lojas. Não cria acompanhamento.
/descontopromo >=30 — informar percentual personalizado na etapa de desconto.
/ceppromo 01001000 — informar o CEP da consulta. O frete ainda não é cotado.

*MONITORAMENTO*
/monitorar ID_DO_ANUNCIO — escolher entre acompanhar só esta oferta ou procurar o mesmo produto em outras lojas.
/monitorar nome ou https://link — procurar anúncios para você escolher.
/lista — ver produtos, status e ofertas pendentes.
/opcoes PRODUTO_ID — reenviar ofertas candidatas com foto e botão de escolha.
/confirmar OFERTA_ID — confirmar exatamente o título e o link exibidos.
/historico ID — ver as últimas 30 leituras e os menores preços por modalidade.
/pausar ID — interromper o acompanhamento.
/retomar ID — reativar e agendar uma consulta imediata.
/remover ID — excluir o produto, o histórico e os alertas associados.
/verificar ID — consultar agora, mesmo se estiver pausado.
/configurar ID reais porcentagem alvo — definir filtros por produto; use - para remover o alvo.
/alertas ID todas|quedas — avisar sobre qualquer alteração ou somente sobre quedas que atendam aos filtros.

*Exemplo de filtros*
/configurar 1 50 5 1500
Os argumentos são: ID, valor mínimo em reais, percentual mínimo e preço-alvo.

/status — ver a versão instalada e o modo de acesso às lojas.

*Observações*
• A busca padrão consulta diretamente as lojas, sem chave de API.
• Os horários seguem America/Sao_Paulo.
• O frete não está incluído.
• Os monitoramentos não expiram. Por padrão, há avisos de aumentos e quedas quando os dados permitem comparação.
• ID de anúncio, ID de oferta e ID de monitoramento são diferentes. Confira qual ID cada mensagem solicita.
• Antes de confirmar uma oferta, confira o modelo, a variante e o link.
```

**Origem:** `monitor/__main__.py` — constante `HELP`.

## `/status`

```
ℹ️ *Status do bot*

Versão: {VERSION}
Busca: {config.provider}
Chromium: {'ativado' if config.browser else 'desativado'}

Pichau/Terabyte: descoberta por sitemaps.
Preço e estoque são conferidos na página da oferta. CAPTCHA e robots.txt continuam sendo respeitados.
```

**Origem:** `monitor/__main__.py` — comando `/status`.

---

# 2. Respostas rápidas e erros de comando

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Erro inesperado durante verificação | `⚠️ Não foi possível concluir a verificação. Os dados válidos anteriores foram preservados.` | `monitor/__main__.py` — `check_send` |
| Falta nome/link ou excede o limite | `Informe um nome ou link com até 600 caracteres.` | `monitor/__main__.py` — comandos `/monitorar`, `/buscar`, `/buscarml` |
| Falta ID | `Informe um ID. Consulte os comandos disponíveis em /ajuda.` | `monitor/__main__.py` — validação comum |
| Oferta sem título lido | `Oferta não encontrada ou ainda sem título lido. Execute /verificar PRODUTO_ID e tente novamente.` | `monitor/__main__.py` — `/confirmar` |
| Produto não encontrado | `Produto não encontrado. Confira o ID e tente novamente.` | `monitor/__main__.py` e `monitor/service.py` |
| Nenhuma oferta pendente | `Não há ofertas pendentes de escolha. Use /verificar ID para buscar novamente.` | `monitor/__main__.py` — `/opcoes` |
| Verificação solicitada | `🔎 Verificação solicitada. Avisarei quando a consulta terminar.` | `monitor/__main__.py` — `/verificar` |
| Verificação em andamento | `⏳ Já existe uma verificação em andamento para este produto.` | `monitor/service.py` — `check` |
| Pausar | `⏸️ Monitoramento pausado. Uma leitura já iniciada ainda pode terminar; os alertas ficam suspensos.` | `monitor/__main__.py` — `/pausar` |
| Retomar | `▶️ Monitoramento retomado. Uma consulta foi agendada.` | `monitor/__main__.py` — `/retomar` |
| Remover | `🗑️ Produto, histórico e alertas associados foram removidos.` | `monitor/__main__.py` — `/remover` |
| Formato de `/alertas` incorreto | `Use: /alertas ID todas ou /alertas ID quedas.` | `monitor/__main__.py` — `/alertas` |
| Todos os alertas | `🔔 Alertas de aumentos e quedas ativados.` | `monitor/__main__.py` — `/alertas` |
| Só quedas | `📉 Alertas somente para quedas ativados, respeitando os filtros configurados.` | `monitor/__main__.py` — `/alertas` |
| Formato de `/configurar` incorreto | `Use: /configurar ID reais porcentagem alvo (ou - para remover o alvo ).` | `monitor/__main__.py` — `/configurar` |
| Filtros alterados | `✅ Filtros atualizados. O modo de alertas está definido como somente quedas. Para receber avisos de qualquer alteração, use /alertas ID todas.` | `monitor/__main__.py` — `/configurar` |
| Comando/configuração inválida | `⚠️ Comando ou configuração inválida. Consulte /ajuda. Uma falha de leitura nunca é tratada como preço zero.` | `monitor/__main__.py` — tratamento de exceções |
| Sem histórico | `Ainda não há histórico para este produto.` | `monitor/__main__.py` — `/historico` |
| Sem produtos na lista | `Sua lista ainda está vazia. Use /buscar nome ou /monitorar nome para começar.` | `monitor/__main__.py` — `/lista` |

---

# 3. Lista de produtos e histórico

## `/lista` — cabeçalho de cada monitoramento

```
🔔 *Monitoramento {p['id']}* — {p['query']}
Status: {'ativo' if p['active'] else 'pausado'}
Anúncio de referência: {p['seed_ad'] or 'legado'}
Abrangência: {p['scope']}
Alertas: {p['alert_mode']}
Prazo: sem vencimento
Próxima consulta: {datetime.fromtimestamp(p['next_due'], ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}
```

## `/lista` — cada oferta associada

```
  🏷️ Anúncio {c['ad_id'] or 'pendente'} · Oferta {c['id']}
  Confirmação: {'confirmada' if c['confirmed'] else 'aguardando confirmação'}
  Produto: {c['title']}
  Última leitura: {last[0]['status'] if last else 'pendente'}
  {c['url']}
```

## `/historico` — cada leitura e série

```
🕒 {when}
Oferta {r['cid']} · Status: {r['status']}
Detalhes: {detail}
```

```
📊 Oferta {s['candidate']}
Vendedor: {s['seller']} · Condição: {s['condition']}
Pagamento: {s['payment']}
Último preço: R$ {s['last'] / 100:.2f} · Menor registrado: R$ {s['lowest'] / 100:.2f}
```

**Origem:** `monitor/__main__.py` — `/lista` e `/historico`.

---

# 4. Busca comum: `/buscar`

## Mensagens de andamento e resultado

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Consulta de páginas | `🔎 Consultando as páginas das ofertas...` | `monitor/__main__.py` |
| Nenhuma oferta localizada | `Não encontramos ofertas nesta consulta.` | `monitor/search_results.py` |
| Link externo do Mercado Livre encontrado | Ver template abaixo | `monitor/search_results.py` — `discovered_text` |
| Falha ao ler uma oferta | `⚠️ Não foi possível ler esta oferta. Motivo: {reason}.\n{url}` | `monitor/search_results.py` |
| Avisos retornados pelas lojas | `⚠️ *Avisos da pesquisa*\n\n{notices}` | `monitor/search_results.py` |
| Busca interrompida | `⚠️ A busca foi interrompida por uma falha. Tente novamente mais tarde.` | `monitor/search_results.py` |

## Resultado com oferta lida — estrutura sugerida

```
{MEDALS[rank]} {rank}º na lista por preço — {reading.payment[:100]}
{“⚠️ Condição não informada; confira na loja.” se provisional; caso contrário, “Confira pagamento e condição antes de comprar.”}
🔎 Os modelos desta busca podem ser diferentes. Confira se a oferta corresponde ao produto desejado.

{reading.title[:350]}

🏪 *Loja:* {store[:80]}
💰 *Preço:* {price}
💳 *Pagamento:* {reading.payment[:100] or '❓ Não declarado para este preço'}
👤 *Vendedor:* {reading.seller[:100] or '❓ Não declarado pela página'}
📦 *Condição:* {condition}
📊 *Estoque:* {stock}
🚚 Frete não incluído.

{se não comparável: “⏸️ Alertas de preço suspensos: faltam dados confirmados — {missing}.”}
🔎 Confira o modelo exato antes de monitorar.

🆔 *ID do anúncio:* {ad_id}
```

Valores literais de `price` e `condition` devem manter a informação retornada: preço em BRL quando disponível ou `não lido`; condição como novo/usado/recondicionado/danificado ou não declarada. Estoque: disponível segundo a página, indisponível ou não confirmado pela página. Não inferir dados ausentes.

**Botões:** `🔔 Monitorar anúncio {ad_id}` e `🔗 Abrir oferta`.

**Origem:** `monitor/presentation.py` — `offer_text` e `send_offer`.

## Cartao longo e falha de foto

Cartoes maiores que a legenda permitida usam apenas texto. Foto explicitamente rejeitada admite alternativa em texto; timeout ou falha de rede nao gera novo cartao, evitando duplicacao quando a entrega inicial e incerta.

## Resultado do resumo da busca

```
✅ *Pesquisa concluída*
Ofertas enviadas: {sent}
Links com falha de leitura: {failed}
Avisos das lojas: {len(notices)}
Links para conferência: {unverified}
```

Se a pesquisa for interrompida, trocar o título por `⚠️ Pesquisa encerrada com falha`, sem alterar as contagens.

**Origem:** `monitor/search_results.py` — `deliver_search`.

---

# 5. Links de índice externo ainda não verificados

```
🔎 *{store} — link encontrado*

{candidate.title[:350]}

📌 Fonte: índice externo Tavily Search. O título ainda não foi conferido na página.
❓ Preço, estoque, vendedor, condição e forma de pagamento não foram verificados.
⚠️ Ao abrir, confira o modelo, a oferta e o vendedor. Catálogos podem alternar vendedores.
⏸️ Este resultado não ativa monitoramento nem alertas.

🔗 {candidate.url}
```

Se a leitura posterior falhar, anexar:

```
⚠️ Leitura da página: {reason}.
```

**Origem:** `monitor/search_results.py` — `discovered_text` e `deliver_search`.

---

# 6. Escolha e confirmação de oferta

## Cartão de oferta para escolher

```
🆔 *ID do anúncio:* {candidate['ad_id'] if 'ad_id' in candidate.keys() and candidate['ad_id'] else 'não atribuído'}

Qual destas ofertas corresponde ao produto que você procura?

📦 Produto {candidate['product']} · Oferta {candidate['id']}
{candidate['title'][:500]}
🏪 Loja: {candidate['store'][:100]}

Confira o modelo, o Wi‑Fi e a versão antes de escolher.
A foto é ilustrativa da página; não comprova o modelo nem o estoque.
Você pode escolher mais de uma oferta.

Alternativa: /confirmar {candidate['id']}
```

**Botões:** `Monitorar esta oferta` e `Abrir na loja`.

Se não houver imagem, acrescentar: `📷 Foto indisponível; você ainda pode escolher pelos botões acima.`

## Respostas à escolha

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Usuário sem autorização | `Somente o usuário autorizado pode fazer essa escolha.` | `monitor/selection.py` |
| Escolha inválida | `Essa escolha não é válida. Atualize as opções com /opcoes PRODUTO_ID.` | `monitor/selection.py` |
| Oferta mudou ou foi removida | `Esta oferta foi removida ou alterada. Use /opcoes PRODUTO_ID para ver as opções atuais.` | `monitor/selection.py` |
| Oferta já selecionada | `Esta oferta já foi selecionada.` | `monitor/selection.py` |
| Escolha aceita | `✅ Oferta selecionada.` | `monitor/selection.py` |

Após selecionar:

```
✅ *Oferta {candidate['id']} selecionada*
{candidate['title']}

Produto {candidate['product']}. Somente ofertas confirmadas entram nas comparações.
Consultando a oferta para registrar o preço inicial, se houver dados suficientes.
```

## Confirmação por `/confirmar OFERTA_ID`

```
✅ *Modelo confirmado*
{candidate['title']}

A próxima leitura válida registrará o preço inicial.
```

**Origem:** `monitor/selection.py` e `monitor/__main__.py`.

---

# 7. Escolha da abrangência e ativação

## Anúncio não encontrado

```
Não encontramos esse anúncio. Execute /buscar nome e use o ID exibido no resultado.
```

## Pergunta de abrangência

```
🆔 *ID do anúncio:* {ad_id}
{ad['title'][:500]}
{ad['url']}

Onde deseja acompanhar este produto?

🔔 Enviarei avisos de aumentos e quedas a cada 5 horas, sem data para encerrar.
• Em outras lojas, a comparação considera somente o mesmo modelo; resultados ambíguos exigem confirmação.
• Bloqueios das lojas ou dados insuficientes podem impedir comparações.
```

**Botões:** `Só esta oferta neste site` e `Outras lojas também`.

## Respostas e ativação

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Usuário sem autorização | `Somente o usuário autorizado pode fazer essa escolha.` | `monitor/subscriptions.py` |
| Escolha inválida | `Essa escolha não é válida. Inicie novamente com /monitorar ID_DO_ANUNCIO.` | `monitor/subscriptions.py` |
| Escolha antiga | `Esta escolha expirou ou o monitoramento foi removido. Use /monitorar ID_DO_ANUNCIO para começar novamente.` | `monitor/subscriptions.py` |
| Já existe monitoramento | `O monitoramento {pid} já está cadastrado. Use /lista para consultar o status ou /retomar {pid} se estiver pausado.` | `monitor/subscriptions.py` |
| Ativação | `✅ Monitoramento ativado!` | `monitor/subscriptions.py` |
| Já existe | `Este monitoramento já existe.` | `monitor/subscriptions.py` |

```
✅ *Monitoramento {pid} ativado*
Abrangência: {scope}.

🚨 Alertas de aumentos e quedas. Consultas a cada 5 horas, sem data de encerramento.
Controle: /pausar {pid} · /retomar {pid} · /historico {pid}

Registrando o preço inicial. Se os dados forem insuficientes, os alertas ficam suspensos; nenhum valor será inventado.
```

Valores de `scope`:

- `somente esta oferta`

- `mesmo modelo nas lojas autorizadas que permitirem acesso`

**Origem:** `monitor/subscriptions.py` — `ask_scope` e `handle_subscription`.

---

# 8. Opções, leitura e alteração de título

## Ofertas pendentes em `/opcoes`

```
🏷️ *Oferta {candidate['id']}*
{candidate['title']}
{candidate['url']}

Para escolher esta oferta, use /confirmar {candidate['id']}.
```

## Consulta manual `/verificar ID`

```
🆔 *Anúncio:* {ad['id']} · Oferta {candidate['id']}
{reading.title}

💰 Preço: {price}; estoque: {reading.stock}; pagamento: {reading.payment or 'não identificado'}
{info}
{candidate['url']}
```

Se não houver preço legível: `Preço não lido` — nunca substituir por zero.

## Estados de leitura

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Leitura sem dados suficientes | `Leitura registrada, mas ainda faltam dados explícitos para comparar preços.` | `monitor/db.py` |
| Nova oferta/condição sem comparação anterior | `Nova oferta ou condição: preço inicial registrado. Ainda não há preço anterior comparável.` | `monitor/db.py` |
| Oferta pendente de confirmação | `Confirme o modelo com /confirmar %s` | `monitor/db.py` |
| Título alterado | `O título da oferta mudou. É necessária uma nova confirmação com /confirmar %s` | `monitor/db.py` |
| Falha em uma oferta | `⚠️ Oferta {candidate['id']}: {code}. O último preço válido foi preservado.` | `monitor/service.py` |
| Nenhuma oferta descoberta | `Não encontramos ofertas nesta consulta. Tente um nome mais curto ou cadastre um link.` | `monitor/service.py` |
| Anúncio confirmado, próxima base | `O preço inicial será registrado na próxima leitura válida.` | `monitor/__main__.py` |

---

# 9. Alertas de preço

## Alerta de queda ou aumento

```
{“📉 QUEDA DE PREÇO” se direction indicar queda; senão “📈 AUMENTO DE PREÇO”}

{direction}: {reading.title}
Monitoramento {candidate['product']} · Oferta {candidate['id']}

🏪 Loja: {candidate['store']}
👤 Vendedor: {reading.seller}
📦 Condição: {reading.condition}

💰 Preço anterior: R$ {row['last'] / 100:.2f}
💰 Preço atual: R$ {reading.price / 100:.2f}
{variation}: R$ {abs(delta) / 100:.2f} ({abs(delta) / row['last'] * 100:.2f}%)
📉 Menor preço registrado: R$ {min(row['lowest'], reading.price) / 100:.2f}
💳 Pagamento: {reading.payment}
📊 Estoque: disponível segundo a página
🚚 Frete não incluído.

Consulta: {datetime.fromtimestamp(now, ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}
{candidate['url']}
```

`{variation}` permanece `Economia` para queda e `Aumento` para alta. Não apresentar este alerta quando faltarem dados comparáveis. O menor valor é o menor histórico registrado para aquela série, não uma promessa de preço futuro.

**Origem:** `monitor/db.py` — `record`.

## Leitura sem alerta

```
Preço atual: R$ {reading.price / 100:.2f} · Menor registrado: R$ {min(row['lowest'], reading.price) / 100:.2f}
```

**Origem:** `monitor/db.py`.

---

# 10. Busca de promoções — consulta pontual

## Entrada e seleção

```
🏷️ *Busca pontual de promoções*
Escolha uma categoria:
```

Botão de categoria: `Hardware`.

```
Inicie uma consulta com /promocoes. Esta seleção expira em 30 minutos.
```

```
Escolha a etapa pelos botões. Para informar um percentual personalizado, use /descontopromo >=30 na etapa de desconto.
```

Botão: `Todas as lojas habilitadas`.

```
Selecione as lojas. Toque para marcar ou desmarcar e depois escolha *Pesquisar agora*.

Opcional: informe o CEP com /ceppromo 01001000.
A consulta é limitada e não ativa alertas futuros.
```

Botão: `🔎 Pesquisar agora`.

## Subcategoria e filtro de desconto

```
Hardware · escolha a subcategoria:
```

Botão: `Placas-mãe`.

```
Escolha o desconto anunciado ou informe um percentual personalizado com /descontopromo >25,5.

>30 exclui 30%; >=30 inclui 30%.
```

Botões: `Maior que 30%` e `Maior ou igual a 30%`.

## Ajuda e respostas de seleção

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Outra busca já em andamento | `Já há uma busca de promoções em andamento. Os demais comandos continuam disponíveis.` | `monitor/deals/telegram.py` |
| CEP sem argumento | `Use /ceppromo 01001000. O frete só será incluído se houver uma cotação verificável; por enquanto, será indicado como não consultado.` | `monitor/deals/telegram.py` |
| CEP registrado | `📍 CEP registrado somente para esta pesquisa. Os adaptadores ainda não cotam o frete; os preços serão apresentados sem frete.` | `monitor/deals/telegram.py` |
| Seleção expirada ou consulta em andamento | `Esta seleção expirou ou já há uma pesquisa em andamento. Inicie outra com /promocoes.` | `monitor/deals/telegram.py` |
| Botão de etapa anterior | `Este botão pertence a uma etapa anterior. Use a seleção mais recente.` | `monitor/deals/telegram.py` |
| Nenhuma loja selecionada | `Selecione pelo menos uma loja para continuar.` | `monitor/deals/telegram.py` |
| Consulta iniciada | `🔎 Busca pontual iniciada. Serão consultadas até 2 páginas de categoria e 12 produtos por loja, com comparações complementares limitadas. Isso pode levar alguns minutos. Nenhum monitoramento será criado.` | `monitor/deals/telegram.py` |
| Falha inesperada | `⚠️ A busca de promoções terminou com uma falha inesperada. Nenhum acompanhamento foi criado. Tente novamente com menos lojas.` | `monitor/deals/telegram.py` |

## Validação de entrada

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Operador ou percentual malformado | `Use >30 ou >=30, com um percentual entre 0 e 100.` | `monitor/deals/models.py` |
| Percentual fora do intervalo | `O percentual deve estar entre 0 e 100.` | `monitor/deals/models.py` |
| Limites inválidos | `Os limites devem estar entre 1 e 100.` | `monitor/deals/service.py` |
| Categoria/loja não habilitada | `Esta categoria ou loja não está habilitada.` | `monitor/deals/service.py` |
| CEP inválido | `O CEP deve conter oito dígitos.` | `monitor/deals/service.py` |
| Consulta já em andamento | `Já existe uma consulta de promoções em andamento.` | `monitor/deals/service.py` |

---

# 11. Cartão de promoção

> Manter 🏆 em todas as ofertas desta busca. Não usar medalhas de ranking nesta seção.

```
🏆 {r.title}

🏪 *Loja:* {offer.store}
De: {reais(offer.previous)}
Por: {reais(r.price)}
📣 Desconto anunciado: {offer.percent:.2f}%
💳 Pagamento: {r.payment or 'não declarado para este preço'}
👤 Vendedor: {r.seller or 'não declarado'}
📦 Condição: {condition}
📊 Estoque: disponível segundo a página
🔎 Comparação: {result.comparison}.

{se houver modelo: “Modelo declarado: {offer.model}”}
{se houver identificadores: “Identificadores:\n{k.upper()}: {v}”}
Referência: {offer.reference_source or 'preço anterior explícito da oferta'}.

{se houver menor preço comparável: “Menor preço comparável: {result.lowest.store}, {reais(result.lowest.reading.price)}.”}
{se existirem preços em outras lojas: bloco abaixo}
{se não houver correspondência: “Ainda não há correspondências confirmadas nas mesmas condições.”}

{se houver cupom: “Cupom: {coupon}”; caso contrário: “Cupom: nenhum requisito confirmado; nenhum desconto adicional foi aplicado.”}
{se houver assinatura: “Assinatura: {subscription}”; caso contrário: “Assinatura: nenhum requisito identificado; confira as condições da loja.”}
🚚 Frete não incluído; {“não consultado para o CEP {report.cep}.” ou “CEP não informado.”}

{se referência suspeita: “⚠️ Preço de referência suspeito: desconto anunciado de 70% ou mais. Confira o valor diretamente na loja.”}
🔗 Link: {offer.url}
```

### Preços em outras lojas

```
*Preços em outras lojas*
{o.store}: {reais(o.reading.price)} ({o.reading.payment}); {o.url}
```

### Resumo da consulta de promoções

```
✅ *Busca pontual concluída — {title}*
Filtro: {report.filter}
Ofertas válidas apresentadas: {len(report.results)}

O desconto anunciado é calculado sobre a referência da própria loja; isso não comprova uma queda histórica. As comparações consideram o preço do produto, sem frete.

Consulta: {datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}

*Cobertura parcial — não representa o site inteiro:*
• {cov.store}: {cov.category_pages} página(s) de categoria tentada(s), {cov.product_pages} oferta(s) tentada(s), {cov.comparison_pages} oferta(s) complementar(es); {cov.discovery_pages} documento(s) de descoberta complementar ({cov.discovery_loaded} lido(s)); {cov.discovered} link(s) descoberto(s), {cov.excluded} produto(s) sem oferta apta.

A contagem considera páginas lógicas; não soma robots.txt, recursos do navegador, redirecionamentos ou novas tentativas. A descoberta pode usar cache ou índice externo; os preços são lidos na página da oferta. As comparações complementares são limitadas e não cobrem todos os anúncios.

⏸️ Esta consulta não cadastra monitoramento nem alertas futuros.
```

**Origem:** `monitor/deals/formatting.py` — `messages`.

---

# 12. Falhas de busca, lojas e leitura

## Erros de configuração da busca por nome

| Caso | Texto sugerido | Origem |
| --- | --- | --- |
| Domínio não autorizado | `Adicione mercadolivre.com.br a ALLOWED_DOMAINS no arquivo .env e reinicie o serviço.` | `monitor/search.py` |
| Chave SEARCH_API_KEY ausente | `A busca por nome não está configurada: falta SEARCH_API_KEY no arquivo .env.\n\nCrie uma chave em https://api-dashboard.search.brave.com/ e configure:\nSEARCH_PROVIDER=brave\nSEARCH_API_KEY=sua_chave\n\nDepois, salve e reinicie o robô. O token do Telegram não substitui essa chave.` | `monitor/search.py` |
| Busca desativada | `A busca por nome está desativada. Configure SEARCH_PROVIDER=direct no arquivo .env para pesquisar nas lojas sem chave, ou cadastre um link.` | `monitor/search.py` |
| Provedor inválido | `SEARCH_PROVIDER inválido. Use direct (sem chave ), brave (opcional) ou disabled.` | `monitor/search.py` |
| Chave/permissão recusada | `A API de busca recusou a chave ou a permissão. Confira a chave e o acesso no painel Brave Search.` | `monitor/search.py` |
| Limite de consultas | `A API de busca atingiu o limite de consultas. Aguarde antes de tentar novamente.` | `monitor/search.py` |
| Serviço sem resposta | `A API de busca não respondeu após as tentativas. Tente novamente mais tarde.` | `monitor/search.py` |
| Erro da API | `A API de busca retornou um erro. Confira sua conta e tente novamente.` | `monitor/search.py` |

## Motivos de falha de descoberta/leitura

Usar como motivo conciso junto de uma mensagem de contexto, sem transformar falhas em ofertas:

| Motivo | Texto sugerido | Origem |
| --- | --- | --- |
| Selenium ausente | `Selenium não está instalado. Atualize o serviço com deploy/update.sh.` | `monitor/discovery.py` |
| Painel Amazon recusado/vazio | `A Amazon recusou a consulta ou não carregou o painel de ofertas.` | `monitor/discovery.py` |
| Opções Amazon indisponíveis | `Não foi possível carregar as opções de compra da Amazon no navegador.` | `monitor/discovery.py` |
| Produto divergente | `O título real da página não corresponde ao produto pesquisado.` | `monitor/discovery.py` |
| Limite de busca externa | `O limite da busca externa sem chave foi atingido. Aguarde antes de tentar novamente.` | `monitor/discovery.py` |
| Índice externo indisponível | `O índice externo está indisponível. Nenhum resultado foi inventado.` | `monitor/discovery.py` |
| Token Mercado Livre ausente | `A API oficial exige MERCADOLIVRE_ACCESS_TOKEN no arquivo .env.` | `monitor/discovery.py` |
| Token inválido/expirado | `O token da API é inválido ou expirou. Atualize MERCADOLIVRE_ACCESS_TOKEN.` | `monitor/discovery.py` |
| Acesso oficial recusado | `A API oficial recusou o acesso (403). Verifique as permissões do aplicativo; o token pode não ser suficiente.` | `monitor/discovery.py` |
| API oficial indisponível | `A API oficial está indisponível ou retornou uma resposta inválida.` | `monitor/discovery.py` |
| Link para catálogo | `É necessário um link de anúncio individual; um catálogo pode trocar de vendedor.` | `monitor/discovery.py` |
| Chromium ausente | `Chromium está indisponível. Execute o instalador com --with-browser.` | `monitor/discovery.py` |
| Tempo limite | `A página excedeu o tempo limite de carregamento no Chromium.` | `monitor/discovery.py` |
| Conexão interrompida | `A conexão com a loja foi interrompida.` | `monitor/discovery.py` |
| Navegação falhou | `Não foi possível navegar no Chromium.` | `monitor/discovery.py` |
| Recurso recusado | `Um recurso da página foi recusado por segurança ou por uma falha de rede.` | `monitor/discovery.py` |
| Produto não identificável | `A página não contém dados estruturados de um único produto.` | `monitor/discovery.py` |
| Redirecionamento recusado | `O redirecionamento para outra loja foi recusado.` | `monitor/discovery.py` |
| Acesso bloqueado | `A loja bloqueou o acesso. Nenhuma tentativa de contornar o bloqueio foi feita.` | `monitor/discovery.py` |
| CAPTCHA | `CAPTCHA detectado. A consulta foi interrompida.` | `monitor/discovery.py` |
| robots.txt inacessível | `Não foi possível obter o robots.txt; o acesso foi suspenso.` | `monitor/discovery.py` |
| robots.txt não permite consulta | `O robots.txt não permite esta consulta.` | `monitor/discovery.py` |
| Formulário não suportado | `O formulário de busca não é compatível e precisa de adaptação.` | `monitor/discovery.py` |
| Rede/limite | `Ocorreu uma falha de rede ou foi atingido o limite de consultas.` | `monitor/discovery.py` |
| Limite para próximo ciclo | `O limite de consultas foi atingido. Tente novamente em outro ciclo.` | `monitor/discovery.py` |
| Busca da loja indisponível | `A página de busca está indisponível.` | `monitor/discovery.py` |

## Avisos de cobertura por loja

```
{domain}: o domínio está autorizado para links, mas ainda não tem adaptador de busca direta. Autorizar o domínio não instala uma integração.
```

```
{store.name}: não encontramos um candidato compatível na fonte consultada (HTML, sitemap limitado ou índice externo). Isso não prova que o produto não exista.
```

```
{store.name}: {reason}.
```

```
Mercado Livre: a descoberta falhou nesta consulta. Isso não prova que o produto não exista.
```

**Origem:** `monitor/discovery.py` — mensagens de descoberta e erros.

---

# 13. Falhas e limites da consulta de promoções

| Situação | Texto sugerido | Origem |
| --- | --- | --- |
| Falha ao ler uma oferta | `⚠️ Falha na leitura da oferta: {reason}` | `monitor/deals/service.py` |
| Categoria sem mapeamento | `Esta categoria ainda não foi mapeada para esta loja.` | `monitor/deals/service.py` |
| Nenhum link extraído | `Não foi possível extrair links: a página está vazia ou o formato da categoria ainda não foi validado.` | `monitor/deals/service.py` |
| Categoria não consultada | `A categoria não pôde ser consultada com sucesso: {reason}` | `monitor/deals/service.py` |
| Limite de páginas | `Limite de {self.limits.category_pages} páginas de categoria atingido.` | `monitor/deals/service.py` |
| Limite de produtos | `A leitura foi limitada aos primeiros {self.limits.products_per_store} produtos encontrados.` | `monitor/deals/service.py` |
| Comparação complementar indisponível | `A busca complementar está indisponível; a comparação será parcial.` | `monitor/deals/service.py` |
| Comparação não confirmada | `Comparação não confirmada` | `monitor/deals/service.py` |
| Oferta mais barata encontrada | `Foi encontrada uma oferta com preço menor` | `monitor/deals/service.py` |
| Menor preço | `Menor preço encontrado` | `monitor/deals/service.py` |

---

# 14. Revisão editorial: texto atual → texto sugerido

A tabela resume os principais ajustes; os templates completos acima são a versão sugerida para implementação.

| Texto atual/forma atual | Texto sugerido | Origem |
| --- | --- | --- |
| “Busca padrao: diretamente nas lojas, sem chave de API.” | “A busca padrão consulta diretamente as lojas, sem chave de API.” | `monitor/__main__.py` — ajuda |
| “Preco e estoque conferidos na oferta; CAPTCHA e robots.txt continuam respeitados.” | “Preço e estoque são conferidos na página da oferta. CAPTCHA e robots.txt continuam sendo respeitados.” | `/status` |
| Mensagem de oferta em linhas corridas: loja, preço, pagamento, vendedor, condição, estoque | Agrupamento visual com rótulos consistentes e ressalvas explícitas; ver seção 4 | `monitor/presentation.py` |
| “Nenhum novo cadastro foi criado.” | “Nenhum novo cadastro foi criado.” (mantido como salvaguarda após erro de configuração) | `monitor/__main__.py` |
| “Anuncio nao encontrado. Execute /buscar nome...” | “Não encontramos esse anúncio. Execute /buscar nome e use o ID exibido no resultado.” | `monitor/subscriptions.py` |
| “A proxima leitura valida registra a base inicial.” | “A próxima leitura válida registrará o preço inicial.” | `monitor/__main__.py` |
| “Consulta pontual iniciada... Nenhum monitoramento será criado.” | Mantido e separado em frases para destacar limites, duração e ausência de acompanhamento | `monitor/deals/telegram.py` |
| Cartão de promoção com “🏆”, desconto e comparação na mesma sequência | Blocos separados para preço, origem/referência, comparação, cupom/assinatura, frete e link; ver seção 11 | `monitor/deals/formatting.py` |
| “Frete nao incluido” / “nao consultado” | “Frete não incluído; não consultado para o CEP...” | Templates de oferta e promoção |
| “Pesquisa concluida. Ofertas enviadas...” | Resumo em linhas separadas, com contagens preservadas | `monitor/search_results.py` |
| “Links com falha de leitura” | Mantido como contagem distinta de links externos ainda não verificados | `monitor/search_results.py` |
| “Ranking provisorio” | “Ranking provisório: condição não declarada.” | `monitor/presentation.py` |
| “Menor historico” | “Menor preço registrado.” | `monitor/db.py` — alerta |
| “Comparacao: existe oferta mais barata” | “Comparação: foi encontrada uma oferta com preço menor.” | `monitor/deals/service.py` |

---

## Notas para implementação

1. Os campos entre chaves são placeholders da implementação original. Preservar nomes, expressões e especificadores de formato ao copiar para o código.

1. Os trechos com `{se ...}` ou texto entre aspas curvas descrevem variantes condicionais para adaptação editorial; não são expressões Python prontas.

1. A API do Telegram limita legendas de fotos. Usar uma unica mensagem de texto quando a legenda exceder o limite.

1. Para usar negrito, configurar o envio com parse mode compatível e escapar conteúdo dinâmico. Se isso não estiver implementado, enviar como texto simples mantendo os mesmos espaços e quebras de linha.

1. A revisão é de apresentação. Não muda as regras de confirmação, autorização, pesquisa, ranking, comparação, preço, estoque, frete, alertas ou periodicidade.
