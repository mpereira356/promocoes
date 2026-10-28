# Menu de botões no Telegram

Se houver uma tarefa em andamento, novos pedidos entram em fila, inclusive
cliques em botões. O bot confirma o recebimento e executa cada pedido após
concluir os resultados do anterior. A fila não sobrevive ao reinício do bot.

Envie **/start** para ativar os atalhos fixos do teclado e abrir a central. **/menu** abre a central novamente. Os comandos antigos continuam disponíveis. A lista nativa de comandos do Telegram também é configurada ao iniciar, quando a API permite.

## Central de ofertas

O cartão de monitoramento mostra abrangência, frequência, quantidade de ofertas com histórico de preço e data do último preço registrado. **Oferta confirmada** significa aprovação da identidade do produto; não garante que houve preço comparável lido. Sem histórico, o cartão avisa que os alertas ainda aguardam um preço inicial válido.

**Outras lojas também** amplia o monitoramento existente, preservando ID, histórico, ofertas confirmadas e filtros. Alternativa: `/abrangencia ID todas`. Não retoma um monitoramento pausado. Se o mesmo anúncio já tiver outro monitoramento com essa abrangência, o bot informa o ID existente sem fundir nem excluir históricos. O modelo continua exato: MSI MAG X870 Tomahawk WiFi não é substituído por X870E ou kit.

`/intervalo ID MINUTOS` define a frequência desse monitoramento (15 a 1440 minutos), mantida após reiniciar. A agenda considera o fim da consulta, a fila e limites das lojas; não representa detecção instantânea. O comando não altera a frequência dos outros produtos. `/verificar ID` solicita consulta manual; `/historico ID` permite conferir os preços efetivamente registrados.

Para placas-mãe, a descoberta considera fontes autorizadas pertinentes: KaBuM, Pichau, Terabyte, Patoloco, Amazon Brasil, Mercado Livre, Magalu e Shopee quando habilitadas. Não desperdiça consultas em supermercados, roupas ou móveis. Novas fontes autorizadas não são excluídas por desconhecimento de categoria. Lista de lojas habilitadas não comprova leitura de preço nelas: bloqueios, falta de estoque ou dados incompletos podem impedir alertas, e ofertas de identidade ambígua continuam exigindo confirmação.

Ao buscar carnes sem CEP salvo, o bot abre a entrada de localização e guarda a consulta. Depois de receber um CEP válido, salva a preferência e retoma a busca automaticamente. Uma entrada inválida mantém a busca aguardando correção.

- **📍 Supermercados: localização e entrega:** abre `/mercados`, com os botões Posso ir à loja e Preciso de entrega. O primeiro é o padrão e não exige entrega, mas não garante preço ou estoque no balcão. Alterar localização recebe o CEP na mensagem seguinte. As preferências ficam salvas após reiniciar.

- **🔎 Buscar produto:** toque e digite o nome ou link na próxima mensagem, sem escrever `/buscar`.
- **🏷️ Promoções:** escolha categoria e subcategoria, ou Tudo nesta categoria. Use os botões Maior que 20% até Maior que 80%, marque as lojas e pesquise. Nenhuma loja começa selecionada; TODAS marca somente as compatíveis com a categoria escolhida.
- **🔔 Meus monitoramentos:** lista paginada de seis itens, com situação ativa/pausada. Toque no produto para abrir suas ações.
- **➕ Monitorar produto:** informe nome, link ou ID de anúncio. A escolha da oferta e da abrangência continua obrigatória; o menu não cadastra automaticamente qualquer resultado parecido.
- **🛒 Mercado Livre:** abre uma entrada dedicada à pesquisa na loja, mantendo os avisos de links e dados não verificados.
- **🗂️ Categorias, 💡 Exemplos, ❓ Ajuda e ℹ️ Status:** atalhos para os recursos existentes.

Os cartões de ofertas e mensagens de acompanhamento têm um botão para voltar ao menu. As telas do menu são editadas quando possível, reduzindo mensagens repetidas. Se uma mensagem não puder ser editada, a próxima tela é enviada normalmente.

Em grupos, as entradas guiadas também abrem uma resposta ao bot, direcionada ao usuário autorizado quando sua mensagem está disponível. Isso permite receber as respostas com o modo de privacidade do Telegram ativo, sem solicitar sua desativação. Mensagens comuns do grupo não abrem menus automaticamente quando não há uma entrada pendente.

## Ações de cada monitoramento

O cartão mostra nome, ID de monitoramento, situação, abrangência, modo de alerta, próxima consulta e identificadores das ofertas vinculadas. Não agrega preços de modalidades diferentes como se fossem uma única oferta.

Botões: **Verificar agora**, **Histórico**, **Pausar/Retomar**, **Alertas e filtros**, **Ofertas para escolher** e **Remover**. Cada ação utiliza o ID do produto selecionado e reutiliza o tratamento dos comandos existentes. A remoção pelo menu pede uma confirmação separada e avisa que excluirá histórico e alertas.

## Filtros sem decorar argumentos

Em **Alertas e filtros → Configurar passo a passo**, o bot pergunta:

1. Queda mínima em reais: por exemplo, **50** exige pelo menos R$ 50,00 de redução; **0** não exige mínimo em reais.
2. Queda mínima percentual: por exemplo, **5** exige pelo menos 5%; **0** não exige percentual mínimo.
3. Preço-alvo: por exemplo, **1500** limita o preço final a R$ 1.500,00. **Sem alvo** remove essa condição.

Cada etapa permite manter o valor atual. A entrada guiada aceita vírgula ou ponto para decimais, sem separador de milhar. Antes de aplicar, o bot mostra um resumo e o botão **Aplicar filtros**. Até essa confirmação, nenhuma configuração é alterada. Aplicar filtros ativa o modo de quedas; o botão de avisar aumentos e quedas volta ao modo geral.

As condições são combinadas com **E**: todas precisam ser atendidas, na mesma oferta e modalidade. Um preço já abaixo do alvo, sem queda, não gera alerta. A comparação continua dependendo de dados válidos e comparáveis.

## Entradas e seleções antigas

**Cancelar**, **Menu**, **Voltar** ou `/cancelar` encerram a entrada atual; não interrompem consultas que já começaram nem desativam monitoramentos. As entradas expiram em 15 minutos e os cartões de controle em 30 minutos. Após reiniciar o serviço, abra uma nova lista/menu; as seleções temporárias não são gravadas no banco.

Confirmações são de uso único. Cartões removidos são invalidados para impedir que um ID reutilizado no banco reative um botão antigo. Todos os comandos, textos recebidos e callbacks continuam restritos ao usuário e chat autorizados.

O menu melhora a navegação; não altera limitações de acesso, frete ou extração das lojas. A validação desta interface usa Telegram simulado, conforme `VALIDACAO.md`.
# Dinheiro emprestado

No menu principal: **💸 Dinheiro emprestado**. Atalho: `/emprestimos`.

- **➕ Emprestar:** nome → valor (ex.: `150` ou `1.250,50`) → data (`25/12/2026`).
- **⏳ Pendentes:** lista paginada com total e identificação dos atrasados.
- Abra um empréstimo para **✅ Marcar como pago** (com confirmação),
  **⏳ Falta pagar** (mantém a pendência) ou **📅 Prorrogar** (escolhe nova data).
- **✅ Pagos:** histórico dos empréstimos quitados.
- Lembretes: 09h e 18h em America/Sao_Paulo, no chat configurado, dois por data.
  Após reinício, avisos pendentes são recuperados com intervalo mínimo de uma hora.
  Pagos não recebem novos avisos. Manter pendente não repete lembretes diariamente.
- Para atualizar os atalhos abaixo do campo de mensagem, envie `/start` novamente.



Promocoes agora usa evidencia de mercado ou historico observado, com filtros de 5% a 80% e busca rapida/ampliada. O botao nao usa o desconto riscado como prova de economia. Consulte `/lojas` para ver acesso e pausas por loja.
