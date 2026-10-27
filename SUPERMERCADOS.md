# Supermercados e preço público por quilo

Versão `2026.10.27-grocery-region.1`.

## Uso no Telegram

1. Salve sua região com `/cep` seguido de oito números. A preferência fica no SQLite, sobrevive ao reinício e tem prioridade sobre `GROCERY_POSTAL_CODE` do `.env`.
2. Pesquise `/buscar Picanha Maturatta` ou consulte uma URL individual.
3. Quando houver preço regional validado, use o botão Monitorar do anúncio e escolha a abrangência.
4. Para receber somente quedas, use `/alertas ID quedas`. O primeiro preço válido é a referência inicial; os avisos começam em verificações posteriores. O intervalo continua configurado por `INTERVAL_HOURS`.

Sem CEP, os mercados apresentam somente links quando disponíveis. Sem unidade, região ou condições verificáveis, não se cria uma oferta monitorável.

## O que foi validado

- **Extra Mercado:** API pública usada pela própria loja para opções de entrega, pesquisa e produto individual. A loja de atendimento é obtida pelo CEP, sem usar o estabelecimento padrão. O preço vem de `variableWeightPrice.sellPrice` e deve coincidir com a referência explícita de 1 kg. O total estimado da peça não é usado como preço/kg. Consulta sem benefícios de cliente cadastrado (`isClienteMais=false`, `customerPlus=false`). Condições promocionais não compreendidas são recusadas.
- **Carrefour Mercado:** seleção regional pública em sessão anônima separada por CEP; releitura da página individual com dados recentes. O CEP precisa reaparecer no payload do produto. O SKU da URL, título principal, moeda, unidade e preço por kg exibido devem concordar. O preço/kg não é calculado dividindo o total aproximado da peça. O payload público é decodificado como JSON, sem executar JavaScript. Estoque é o declarado pelo catálogo regional, não garantia de entrega final.
- **Atacadão:** descoberta por arquivos de produtos do sitemap publicado, com limite de documentos e indicação de cobertura parcial. Consulta regional de vendedores e simulação pública isolada, sem adicionar itens ou efetuar compra. Exige SKU, vendedor, preço/kg, estoque e opção de entrega coerentes. A leitura atual recusa multiplicador diferente de 1 kg e condições que não consegue validar. No teste real da Maturatta congelada não houve oferta com estoque e entrega confirmados nas lojas consultadas.
- **Boa Supermercados:** validação pública da sessão regional e pesquisa de produtos pela operação usada na loja. Os identificadores das operações são descobertos no bundle público atual, sem chave privada. O teste real encontrou a Maturatta resfriada indisponível e com preço zero; isso é tratado como indisponibilidade, nunca promoção. O payload observado não declara a unidade do preço positivo: enquanto essa unidade não puder ser validada, a integração não habilita alertas de preço no Boa.

Uma consulta real com um CEP fornecido privadamente confirmou preços públicos por kg com estoque informado no Extra e no Carrefour, e resultados sem oferta disponível no Atacadão e no Boa. Isso não garante acesso permanente ou disponibilidade de todos os produtos. O CEP, endereços e cookies não são incluídos nas capturas de teste publicadas.

## Significado dos alertas

Esses alertas acompanham **o preço público por kg, da mesma loja e do mesmo CEP**. A forma de pagamento permanece explicitamente não confirmada, e o total depende da pesagem. Essa modalidade tem contexto próprio e não relaxa a exigência de pagamento das ofertas comuns. Uma mudança de loja/CEP inicia outra série, evitando interpretar a troca de região como desconto.

Nenhum alerta chama automaticamente uma queda de preço de promoção comprovada sobre o mercado. Não se comparam preço/kg e total da embalagem, congelada e resfriada, nem um corte com hambúrguer ou tempero. Identificadores de peso variável de lojas diferentes não são tratados como EAN universal de produto idêntico.

O menu **Promoções por percentual dos supermercados ainda não está habilitado**: a validação exige evidência comparável suficiente e histórico. Use a busca e o acompanhamento de preço público por kg. Sem estoque, com preço zero ou com dados pendentes, os resultados são links de conferência sem botão para monitorar.

## Diagnóstico e limites

`/lojas` mostra o CEP configurado e o último resultado regional consultado; HTTP 200 não comprova leitura de preço. `python -m scripts.diagnose_groceries --cep SEU_CEP` consulta uma página individual por mercado, grava relatório em `data/` e não cria monitoramentos nem envia Telegram.

Listas padrão do instalador incluem os quatro mercados; listas personalizadas são preservadas. As rotas públicas respeitam robots.txt, recusas de acesso, limites e pausas do Fetcher. Os POSTs ficam restritos a seleção regional, validação de sessão, busca pública e simulação isolada; não permitem publicar pedidos ou pagamentos. A busca HTML do Extra é proibida por robots.txt e não é utilizada; a API pública tem suas próprias regras verificadas.

Os testes sintéticos cobrem região divergente, persistência do CEP, preço/kg versus total, produto errado, estoque, entrega, mudança de série por região e alertas sem pagamento inventado. Consulte a [referência oficial do Checkout VTEX](https://developers.vtex.com/docs/api-reference/checkout-api) e a [referência dos campos e unidades](https://developers.vtex.com/docs/guides/orderform-fields).
