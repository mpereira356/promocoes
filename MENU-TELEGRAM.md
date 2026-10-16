# Menu de botões no Telegram

Envie **/start** para ativar os atalhos fixos do teclado e abrir a central. **/menu** abre a central novamente. Os comandos antigos continuam disponíveis. A lista nativa de comandos do Telegram também é configurada ao iniciar, quando a API permite.

## Central de ofertas

- **🔎 Buscar produto:** toque e digite o nome ou link na próxima mensagem, sem escrever `/buscar`.
- **🏷️ Promoções:** escolha categoria, desconto e lojas. Os botões de categoria livre, percentual personalizado e CEP também aceitam respostas digitadas, sem precisar copiar comandos.
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
