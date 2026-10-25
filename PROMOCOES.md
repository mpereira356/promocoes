# Busca pontual de promocoes

Versao `2026.10.25-completion.1`.

## Fluxo no Telegram

1. Toque em Promocoes ou envie `/promocoes`.
2. Escolha o grupo e a subcategoria. Em Computadores aparecem Placas-mae, Mouse, Teclado, Processadores, Memoria RAM e outras categorias mapeadas. Subcategorias podem ter novas subdivisoes. Tudo nesta categoria inclui as fontes mapeadas dos departamentos descendentes.
3. Escolha um dos sete botoes: Maior que 20%, 30%, 40%, 50%, 60%, 70% ou 80%. O comparador e sempre estrito: exatamente 30% nao atende a Maior que 30%. Nao e necessario digitar operadores.
4. Para Lacoste, escolha o tamanho ou Ignorar tamanho.
5. Marque as lojas. Nenhuma loja comeca marcada. TODAS marca somente as lojas compativeis com a categoria escolhida; Limpar selecao desmarca todas.
6. Toque em Pesquisar agora. Sem lojas marcadas, o bot pede uma selecao e nao inicia uma tarefa.

As categorias sao ligadas a URLs observadas de cada loja. Quando existe apenas uma categoria-pai mapeada, os titulos sao filtrados pela subcategoria solicitada. Nao se enviam buscas por Computadores a lojas de roupas ou eletrodomesticos. Categorias mapeadas nao usam o indice externo para pesquisas genericas em lojas sem mapa. As ofertas das lojas escolhidas sao comparadas entre si quando existe identidade suficiente; nao ha novas buscas externas para completar uma consulta por categoria.

Categoria livre por termo e link direto permanecem disponiveis via `/categoria`. Consultas explicitamente por termo tem cobertura parcial e usam somente as lojas marcadas. O bot continua sem agendamentos ou gravacoes no banco de precos para esta funcao.

## Descoberta por loja

| Loja | Fonte de descoberta de promocoes |
| --- | --- |
| KaBuM | Categoria mapeada, catalogo NEXT_DATA e paginacao declarada. |
| Pichau | Sitemap publico, filtrado pela categoria; produtos lidos individualmente. Se o sitemap nao tem dados aplicaveis, tenta a pagina mapeada, salvo bloqueio ou restricao. |
| Terabyte | Categoria mapeada, links de produto e paginacao declarada. |
| Lacoste | Sale/categorias mapeadas, preservando cor; preco riscado do produto principal. Busca textual usa sitemap publico de imagens. |
| Sensetup, Elements, Flexform | Categorias mapeadas; preco anterior depende de dados atribuidos ao produto/variante. |
| Brastemp, Frigelar | Categorias mapeadas; SKU e preco anterior precisam ser verificaveis. |
| Amazon, Mercado Livre, Shopee, Magalu | Categorias mapeadas ou link informado; dados estruturados precisam identificar a oferta e o preco anterior. Acesso e referencias podem estar ausentes. |

Nenhuma referencia de desconto e inventada. HTTP 403, CAPTCHA e restricoes de robots.txt interrompem a leitura correspondente. Um bloqueio de acesso da loja nao e contornado e nao impede continuar nas outras lojas selecionadas.

## Cobertura e entrega

Amostra limitada a doze produtos por loja. Na selecao Tudo, o orcamento de produtos e distribuido entre as categorias, com uma pagina de cada fonte e ate doze fontes por loja. Categorias individuais usam ate duas paginas. O resumo e explicito sobre a cobertura parcial.

A ultima mensagem sempre comeca com Pesquisa finalizada. Ela informa o resultado do filtro e agrupa as lojas com precos verificados e as lojas que nao puderam ser verificadas. Se nenhuma loja retornar dados, diz que nao foi possivel verificar ofertas, sem afirmar que nao existem descontos. Contagens tecnicas, paginas, sitemaps e avisos de extracao nao sao enviados ao usuario. Falhas de consulta e de entrega tambem encerram com uma mensagem explicita, quando o Telegram permite a entrega. Os detalhes de cobertura continuam disponiveis no relatorio interno para diagnostico.

O frete nao e cotado e nao entra no desconto. A selecao expira em trinta minutos. Botoes de telas anteriores sao recusados.

## Cálculo, condições e comparação

O desconto anunciado é `(anterior - atual) / anterior * 100`. Só entram referências positivas maiores que o preço total atual, em reais e com disponibilidade explícita. Valor de parcela, desconto escrito em banner e preço antigo de um produto recomendado não são referências. O preço atual vem do leitor já existente, e o anterior é extraído do **mesmo HTML**, evitando misturar momentos ou vendedores.

O preço normal `price` da KaBuM não substitui um `oldPrice` ausente. O preço Pix já descontado não recebe um segundo desconto. Cupons divulgados em selos são mostrados como informação, sem aplicação automática ou pressuposição de que já foram usados. Exclusividade Prime declarada é sinalizada quando associada ao preço. Requisitos ausentes não são garantias de que não existem: a mensagem distingue informações identificadas e pede conferência das condições da loja. A leitura de cupons/assinaturas não está integralmente validada em todas as lojas.

Referências que impliquem desconto de 70% ou mais recebem aviso de preço de referência suspeito, uma heurística para conferência, não prova de fraude. Este módulo não consulta histórico e **nunca afirma que aconteceu uma queda histórica real**.

Para comparação são exigidos GTIN válido, MPN e marca iguais, ou marca e modelo explicitamente declarados iguais, sem conflitos de variante. Título parecido não confirma identidade. DDR4/DDR5, Wi-Fi, revisão, condição, pagamento e requisitos de cupom/assinatura precisam ser compatíveis. Ausência de informações deixa a comparação não confirmada; não se assume que todo produto é novo. O mesmo título pode evitar duplicata na lista, mas não serve de prova para comparar preços.

Os três produtos distintos com maior percentual anunciado são apresentados com 🏆. Cada resultado mantém o preço de/por da loja que anunciou o desconto e, separadamente, indica o menor preço comparável encontrado, com até três opções no total. Não completa a lista com itens fora do filtro. A comparação considera apenas preço do produto, sem frete e dentro das lojas e limites consultados. Faltar correspondência confirmada não autoriza declarar menor preço.

## Diagnóstico e testes

Sem enviar Telegram ou abrir o banco:

```bash
python -m scripts.diagnose_deals --browser --stores kabum.com.br,pichau.com.br --discount ">=30" --pages 1 --products 3 --comparisons 1
python -m scripts.diagnose_deals --browser --stores pichau.com.br --category pets --pages 1 --products 2
python -m scripts.diagnose_categories --list
python -m scripts.diagnose_categories --refresh --browser
```

Na VPS instalada, use `/opt/price-monitor/.venv/bin/python` como `pricebot`. O diagnóstico padrão é menor que a busca do Telegram para limitar acessos. Rode a suíte local com `python -m pytest -q` (dependências de teste em `requirements.txt`).

Os testes locais usam respostas simuladas, além de um recorte histórico de HTML Pichau real. Não enviam mensagens reais, não verificam preços atuais e não demonstram disponibilidade permanente das lojas. Veja `VALIDACAO.md` para a validação ao vivo separada.
