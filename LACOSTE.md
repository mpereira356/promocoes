# Lacoste Brasil

No Telegram, use `/promocoes lacoste`, escolha a categoria e siga os botões:

1. Desconto anunciado: maior que (`>30`), maior ou igual (`>=30`), menor que (`<30`) ou menor ou igual (`<=30`). O botão de outro percentual aceita, por exemplo, `/descontopromo >=25,5`.
2. Tamanho: escolha uma opção ou digite outro tamanho. `/tamanhopromo 42` filtra por 42; `/tamanhopromo todos` ignora tamanho. Não existe conversão automática entre M e a numeração Lacoste.
3. Confirme a loja e toque em Pesquisar agora. Categorias Lacoste deixam somente essa loja marcada inicialmente.

Categorias iniciais: Sale, masculino, feminino e polos masculinos/femininos. Também é possível informar um link brasileiro de categoria com `/categoria https://www.lacoste.com/br/lacoste/sale/`.

Os resultados mostram preço anterior, preço atual, percentual calculado, cor e tamanhos com disponibilidade explícita. Um tamanho apenas listado, sem confirmação de estoque, não atende ao filtro. Sem filtro, itens com tamanho desconhecido podem aparecer, identificados como tal. Não se somam descontos de carrinho, cupons ou preços de parcelas ao desconto anunciado. Um item sem preço anterior verificável não qualifica como promoção percentual.

A busca segue os limites existentes: até duas páginas de categoria, doze produtos por loja e três resultados apresentados. O resumo informa cobertura parcial. Esta consulta não cria acompanhamento automático.

## Instalação e validação

`lacoste.com` foi incluído nos domínios padrão, no `.env.example` e no `.env` local. O instalador e `deploy/update.sh` atualizam listas padrão antigas para incluir a Lacoste, inclusive quando Amazon está escrita com `www.`. Listas personalizadas são preservadas: nesse caso, acrescente `lacoste.com` a `ALLOWED_DOMAINS` e reinicie o bot após atualizar o código.

Na busca geral, `/buscar Boné Esportivo Leve` consulta também a Lacoste quando habilitada. `/buscar Boné Esportivo Leve Lacoste` exige a marca, que pode estar no título ou declarada na ficha do produto. O filtro exige a categoria pedida: fones que compartilhem apenas os adjetivos “esportivo” e “leve” não entram como bonés.

Em 21/10/2026, o Fetcher de produção obteve respostas HTTP 200 para robots.txt, catálogo de imagens, Sale e produtos, permitindo validar a leitura real. Foram lidos o Boné Esportivo Leve (R$ 469,00, azul-marinho, tamanho TU) e uma camiseta Pima (R$ 299,00, preço anterior R$ 429,00, branca). São valores da amostra, sem garantia de preço atual. Capturas reduzidas estão em `tests/fixtures/lacoste_cap_real.html` e `lacoste_product_real.html`. Algumas tentativas anteriores receberam 403; a disponibilidade pode mudar por ambiente e momento.

O adaptador aceita o Product Schema.org principal e estoque de tamanho explicitamente declarado. A busca usa os nomes publicados no sitemap de imagens `/br/sitemap_1-image.xml`, sem consultar a rota `/br/search/`, proibida pelo robots.txt. Os nomes do sitemap servem apenas para descobrir links: preço e estoque são relidos na página do produto.

O HTML da camiseta não inclui a disponibilidade dos tamanhos: o seletor depende de uma rota `/on/demandware.store/` também proibida pelo robots.txt. Esses tamanhos ficam desconhecidos e não atendem a um filtro específico. O tamanho TU do boné está atribuído explicitamente à oferta individual disponível e pode ser usado. Nenhum tamanho é inferido da descrição do modelo ou do guia de medidas.

Referências oficiais: [Lacoste Sale](https://www.lacoste.com/br/lacoste/sale/) e [exemplo de produto com cor selecionada](https://www.lacoste.com/br/lacoste/masculino/vestu%C3%A1rio/camisetas/TH6710-23.html?color=001).
