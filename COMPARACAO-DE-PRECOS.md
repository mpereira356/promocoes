# Avaliação de preços — 2026.10.25-market-evidence.1

## O que o bot considera evidência

**Vigilância de preço publicado:** `/vigiar ID MINUTOS` é uma modalidade separada para acompanhar variações do preço divulgado em cada anúncio confirmado. Pode trabalhar com condição ausente, que permanece desconhecida, sem presumir Novo. Vendedor, pagamento, moeda, disponibilidade e identidade do produto continuam necessários. Esse modo não altera a validação abaixo: condição ausente não comprova equivalência comercial entre lojas, e não entra automaticamente como promoção comprovada. Os monitoramentos comuns mantêm a regra estrita até uma escolha explícita por `/vigiar`.

A opção Promoções usa `validation=market`. O preço riscado e o percentual do anúncio não determinam se a oferta é boa.

Para validar vantagem de mercado, o bot precisa ler a oferta e o mesmo produto em **duas outras lojas**, com identificadores fortes, mesma variante, condição e pagamento, requisitos de cupom/assinatura compatíveis e estoque disponível. Dados sem condição, vendedor ou pagamento não comprovam equivalência. As leituras usadas têm até quinze minutos; resultado de índice de busca nunca serve de preço.

A referência é o **menor preço entre as outras lojas**, não a média de anúncios caros. A economia é `(referência - preço atual) / referência × 100`, calculada sem arredondamento antes do filtro.

| Preço avaliado | Outras lojas | Resultado |
| --- | --- | --- |
| R$ 45,00, anunciado como 40% OFF | R$ 42,00 e R$ 42,00 | Descartado: não é mais barato. |
| R$ 42,00, anunciado como 40% OFF | R$ 45,00 e R$ 46,00 | Vantagem de 6,67%, não de 40%. Passa em Maior que 5%, não em Maior que 10%. |
| R$ 30,00 | R$ 45,00 e R$ 46,00 | Vantagem de 33,33%, se produto e condições forem comparáveis. |

O cartão mostra a economia calculada, preços e links das ofertas comparadas, condição e requisitos. Uma referência anunciada muito acima dos preços comparados recebe observação, sem acusação de fraude: desconto em relação a um preço anterior e vantagem sobre o mercado são conceitos diferentes.

## Histórico observado

As leituras válidas também alimentam `price_observations`, separada de monitoramentos e alertas. Nenhum acompanhamento é criado automaticamente. O histórico anterior dos monitoramentos permanece intacto.

As novas observações começam nesta versão. Mantêm uma mínima por janela de seis horas e expiram após noventa dias. A avaliação consulta até trinta dias anteriores e exclui as últimas 24 horas, impedindo que a consulta valide a si própria. Exige duas datas de observação com intervalo de pelo menos 24 horas. Pagamento, vendedor, condição e variante não são misturados.

Quando há histórico suficiente, sua mínima limita a referência: um produto que já custava o mesmo valor não vira promoção por ter um “de” maior. Sem comparação suficiente entre lojas, uma queda documentada pode ser apresentada como **Queda no preço observado**, explicitamente sem confirmação de vantagem de mercado. Um preço concorrente conhecido igual ou menor impede essa classificação. Dados genéricos de histórico não validam cupons ou assinaturas.

Ausência de evidência é informada como **não foi possível comprovar**, sem afirmar que não existe promoção. A comparação exclui frete e não garante menor custo entregue, acesso futuro, legitimidade de vendedor ou cobertura integral da internet.

## Pesquisa ampliada e acesso

O padrão é Ampliada: até quatro páginas por categoria, 48 produtos por loja, nove candidatos priorizados e doze consultas complementares no total. Cada loja tem até oito leituras complementares. A opção Rápida usa doze produtos. As categorias de Tudo são amostradas entre fontes, preservando os limites. Uma consulta ampliada não examina todo o catálogo.

Até três lojas diferentes são examinadas em paralelo para reduzir o tempo total. Dentro de cada loja, os limites e intervalos do transporte continuam valendo. Uma falha isolada preserva os resultados das demais.

As lojas começam desmarcadas. TODAS marca as compatíveis com a categoria. Só as lojas escolhidas entram na pesquisa e comparação; escolher ao menos três dá mais possibilidade de comprovar vantagem sem histórico.

Consultas idênticas reutilizam links e páginas da mesma execução, sem reaproveitar preços de snippets. Sitemaps públicos continuam em cache. Pausas por 403, CAPTCHA e limite HTTP são persistidas em `data/store-backoff.json`, inclusive entre reinícios. Não há rotação de IP, disfarce de identidade ou resolução de CAPTCHA. `/lojas` mostra as pausas e o último estado de acesso; HTTP 200 sozinho não significa preço verificado.

## Fontes e configuração

Patoloco foi adicionada após leitura real da busca, categoria publicada no menu e microdados do produto. A amostra de MSI X870E Tomahawk retornou R$ 2.453,89 em Pix/boleto. Não foi declarada condição do produto: esse campo permanece vazio e a oferta não serve como prova de equivalência de condição. A fixture pública reduzida é `tests/fixtures/patoloco_product_real.html`; preços são históricos de teste, sem promessa de valor atual.

Configuração opcional no `.env`:

```dotenv
PROMOTIONS_DEPTH=expanded
TAVILY_API_KEY=
```

Uma chave própria usa a [autenticação oficial Tavily](https://help.tavily.com/articles/4840311948-tavily-search-api), em vez do modo público limitado. Nenhuma conta ou contratação é criada. Quotas e custos dependem da conta configurada. A chave só descobre URLs; preço e estoque continuam vindo da loja. Também permanece disponível o provedor Brave já suportado.

As APIs de [preços do Mercado Livre](https://developers.mercadolivre.com.br/devcenter/api-de-precos) e [Amazon Creators API](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding) exigem acesso/credenciais próprios. Não se inventou acesso a elas nem se apresentou uma integração não executada como funcional.

O instalador amplia listas padrão antigas para incluir Patoloco, preservando listas personalizadas. Nelas, adicione `patoloco.com.br` se desejar. O diagnóstico sem Telegram está disponível em `python -m scripts.diagnose_deals --discount '>5' --products 12 --comparisons 2 --browser`. `--validation announced` existe apenas para diagnóstico legado e não comprova vantagem; o Telegram usa o modo de evidência.
