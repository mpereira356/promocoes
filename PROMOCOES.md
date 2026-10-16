# Busca pontual de promoções

No Telegram, envie `/promocoes` e escolha um departamento, subcategoria, filtro e lojas. As telas têm botões de próxima/anterior e permitem trocar de categoria. O catálogo distribuído reúne **201 categorias/subcategorias em 33 grupos**, com **215 links** observados nas lojas. Inclui Hardware, Periféricos, Monitores, Notebooks, Cadeiras, Casa e Lazer, Casa e Eletro, Games, Pets e outros. Só aparecem categorias com link em pelo menos uma loja habilitada em `ALLOWED_DOMAINS`.

Também pode digitar `/categoria monitores`, `/categoria pets`, `/categoria casa e lazer` ou `/promocoes notebooks`. Se houver mais de uma opção, escolha o resultado correto. Para qualquer outro tema, como `/categoria brinquedos`, o bot aceita a consulta e informa que a descoberta será **por termo**, com cobertura parcial, sem inventar uma URL de categoria. Alguns termos comuns têm equivalência de busca explícita, como celulares → smartphone. Não há garantia de que todo tema exista em todas as lojas.

Pode informar diretamente uma página: `/categoria https://www.pichau.com.br/pets`. A origem precisa ser uma loja autorizada. O extrator da loja será aplicado à página fornecida; ausência de dados ou formato não suportado será relatado, sem afirmar que a página foi lida com sucesso.

Use `/categorias atualizar` ou o botão de atualização para reler uma página de menu por loja. O catálogo anterior é preservado em caso de bloqueio; atualizações têm cache de uma hora e valem para a execução atual. O catálogo distribuído é carregado novamente após reinício. O menu é parcial: links descobertos não comprovam preços, estoque ou acesso a todas as páginas. Amazon/Mercado Livre ainda não têm descoberta automática de menus validada; aceitam categoria por termo ou URL, respeitando as limitações de acesso existentes.

Marque ou desmarque cada loja e toque em **Pesquisar agora**. Todas significa todas as lojas suportadas habilitadas em `ALLOWED_DOMAINS`. Quando uma loja não tiver página mapeada para a categoria escolhida, usa descoberta por termo e informa isso no resumo; o preço continua vindo da oferta.

Para outro percentual, na etapa do desconto envie `/descontopromo >25,5` ou `/descontopromo >=30`. O primeiro exige mais de 25,5%; o segundo aceita exatamente 30%. O filtro usa centavos e comparação exata, sem arredondar o percentual antes de filtrar. O valor exibido tem duas casas decimais.

Opcionalmente, envie `/ceppromo 01001000` antes de iniciar. **Os adaptadores ainda não fazem cotação de frete**; o CEP será mencionado e todos os preços serão explicitamente apresentados sem frete. Não é estimado frete zero. A seleção expira em 30 minutos.

A consulta acontece naquele momento, termina com uma mensagem de conclusão e não cadastra anúncios, produtos, histórico, jobs, acompanhamentos nem alertas. O banco não é uma dependência do serviço de promoções. Um monitoramento já existente continua independente. Só o usuário e o chat autorizados podem operar os comandos e botões.

## Cobertura inicial e limites

A navegação usa `monitor/deals/catalog.py` e o catálogo público `category_seed.json`. Os links vieram dos menus reais; não são fabricados a partir de nomes. O mapa de cada adaptador é preenchido a partir desse catálogo, e a seleção efetiva é passada ao serviço, sem fixar Hardware/Placas-mãe. Menus, busca por nome e URL livre compartilham os mesmos leitores, validação de preços e limites. Equivalências entre rotas são explícitas; a comparação do mesmo produto continua exigindo identidade forte.

Por pesquisa: até **2 páginas de categoria e 12 produtos por loja**. Para cada produto distinto que passar no filtro dentro dessa amostra, busca complementar de até **2 candidatos por outra loja selecionada**; os três melhores são apresentados. Os mesmos URLs são reutilizados em memória durante a consulta. A busca complementar reutiliza o provedor configurado; com `SEARCH_PROVIDER=direct` não exige chave de busca. Ela pode consultar sitemaps ou índice externo para descobrir links; nunca usa preços de snippets. Muitas ofertas aptas podem tornar a consulta demorada; o recebimento de comandos permanece ativo.

O resumo identifica páginas lógicas tentadas, produtos descobertos, leituras de ofertas, documentos de descoberta complementar, falhas e limites. Tentativas recusadas por robots ou bloqueio não são apresentadas como páginas lidas. Não é uma varredura integral, nem garantia de encontrar todas as promoções. Recursos internos de navegador, robots.txt, redirecionamentos e retentativas não são contados como novas páginas. Cache pode reduzir a contagem de documentos complementares.

| Loja | Extração de categoria | Referência de desconto | Situação |
|---|---|---|---|
| KaBuM | NEXT_DATA, incluindo JSON serializado duas vezes; paginação da categoria | `product.prices.oldPrice` vinculado a ID e título | Caminhos e estrutura observados em páginas reais |
| Pichau | Cards `data-cy=list-product` e próximo link da própria categoria | Bloco principal `price_from`, associado ao preço Pix lido | Estruturas observadas em páginas reais; depende de acesso da loja |
| Terabyte | Links de produto reconhecidos pelo adaptador existente e paginação declarada | Somente StrikethroughPrice estruturado da mesma oferta | Referência por HTML ainda não validada; categoria pode falhar |
| Amazon | URL mapeada/livre: ItemList/Product estruturados; sem mapa: descoberta por termo | Somente StrikethroughPrice estruturado da mesma oferta | Menu automático, HTML de categoria e referência por vendedor não validados; pode não produzir resultados |
| Mercado Livre | URL mapeada/livre: ItemList/Product estruturados e anúncios individuais; sem mapa: descoberta por termo | Somente StrikethroughPrice estruturado da mesma oferta | Menu automático não validado; acesso bloqueado nas verificações anteriores |

O suporte genérico a `priceSpecification`/`StrikethroughPrice` segue o contrato estruturado e é testado com simulações; **não comprova que essas lojas o fornecem**. Nenhum percentual é atribuído se não existir uma referência válida da própria oferta. Bloqueios/CAPTCHA/robots são respeitados e não são contornados.

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
