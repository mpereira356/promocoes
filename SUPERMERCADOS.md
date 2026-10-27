# Supermercados e preço público por quilo

Versão `2026.10.27-store-visit.1`.

## Uso no Telegram

1. Abra **Supermercados: localização e entrega** no menu ou envie `/mercados`. Escolha **Posso ir à loja** (padrão) ou **Preciso de entrega**. O botão **Alterar localização** recebe os oito números do CEP na próxima mensagem. Também existe `/cep` seguido do CEP. As preferências ficam no SQLite, sobrevivem ao reinício e têm prioridade sobre `GROCERY_POSTAL_CODE` e `GROCERY_MODE` do `.env`.
2. Pesquise `/buscar Picanha Maturatta` ou consulte uma URL individual.
3. Quando houver preço regional validado, use o botão Monitorar do anúncio e escolha a abrangência.
4. Para receber somente quedas, use `/alertas ID quedas`. O primeiro preço válido é a referência inicial; os avisos começam em verificações posteriores. O intervalo continua configurado por `INTERVAL_HOURS`.

Sem CEP, os mercados apresentam somente links quando disponíveis. Sem unidade, região ou condições verificáveis, não se cria uma oferta monitorável.

**Posso ir à loja:** a falta de entrega ou o estoque online indisponível não eliminam um preço público positivo validado para a loja e região consultadas. O cartão informa o modo, a disponibilidade no site, a ausência de confirmação do estoque físico e, quando fornecido, o endereço da loja. Não afirma que existe retirada agendada nem que o preço online vale no balcão. Os alertas acompanham esse preço publicado mesmo sem entrega; confirme oferta e estoque antes de ir.

**Preciso de entrega:** mantém a exigência de estoque e validação regional de entrega. A opção fica salva pelo botão correspondente. Trocar de modo inicia outra série de preços para evitar comparar condições diferentes como se fossem desconto. `GROCERY_MODE=visit|delivery` configura o padrão quando ainda não existe preferência salva.

## O que foi validado

- **Extra Mercado:** API pública usada pela própria loja para opções de entrega, pesquisa e produto individual. A loja de atendimento é obtida pelo CEP, sem usar o estabelecimento padrão. O preço vem de `variableWeightPrice.sellPrice` e deve coincidir com a referência explícita de 1 kg. O total estimado da peça não é usado como preço/kg. Consulta sem benefícios de cliente cadastrado (`isClienteMais=false`, `customerPlus=false`). Condições promocionais não compreendidas são recusadas.
- **Carrefour Mercado:** seleção regional pública em sessão anônima separada por CEP; releitura da página individual com dados recentes. O CEP precisa reaparecer no payload do produto. O SKU da URL, título principal, moeda, unidade e preço por kg exibido devem concordar. O preço/kg não é calculado dividindo o total aproximado da peça. O payload público é decodificado como JSON, sem executar JavaScript. Estoque é o declarado pelo catálogo regional, não garantia de entrega final.
- **Atacadão:** descoberta por arquivos de produtos do sitemap publicado, com limite de documentos e indicação de cobertura parcial. Consulta regional de vendedores e simulação pública isolada, sem adicionar itens ou efetuar compra. Exige SKU, vendedor e preço/kg coerentes; no modo de entrega, também exige estoque e opção de entrega. No modo de visita, preserva preço positivo publicado mesmo quando a simulação não oferece entrega, identificando a ausência de confirmação física. A leitura atual recusa multiplicador diferente de 1 kg e condições que não consegue validar.
- **Boa Supermercados:** validação pública da sessão regional e pesquisa de produtos pela operação usada na loja. Os identificadores das operações são descobertos no bundle público atual, sem chave privada. O teste real encontrou a Maturatta resfriada indisponível e com preço zero; isso é tratado como indisponibilidade, nunca promoção. O payload observado não declara a unidade do preço positivo: enquanto essa unidade não puder ser validada, a integração não habilita alertas de preço no Boa.

Uma consulta real no modo de visita, com um CEP fornecido privadamente, confirmou preços publicados por kg no Extra, Carrefour e Atacadão. No Atacadão, a publicação apareceu mesmo sem estoque/entrega confirmados na simulação. O Boa continuou com preço zero, que permanece recusado. Isso não comprova preço ou estoque em loja física, nem garante acesso permanente. O CEP, endereços do usuário e cookies não são incluídos nas capturas de teste publicadas.

## Significado dos alertas

Esses alertas acompanham **o preço público por kg, da mesma loja e do mesmo CEP**. A forma de pagamento permanece explicitamente não confirmada, e o total depende da pesagem. Essa modalidade tem contexto próprio e não relaxa a exigência de pagamento das ofertas comuns. Uma mudança de loja/CEP inicia outra série, evitando interpretar a troca de região como desconto.

Nenhum alerta chama automaticamente uma queda de preço de promoção comprovada sobre o mercado. Não se comparam preço/kg e total da embalagem, congelada e resfriada, nem um corte com hambúrguer ou tempero. Identificadores de peso variável de lojas diferentes não são tratados como EAN universal de produto idêntico.

O menu **Promoções por percentual dos supermercados ainda não está habilitado**: a validação exige evidência comparável suficiente e histórico. Use a busca e o acompanhamento de preço público por kg. Preço zero ou sem unidade/região verificáveis continua sendo somente link de conferência. No modo de visita, o preço publicado pode ser acompanhado com estoque físico desconhecido; no modo de entrega, estoque/entrega pendentes impedem a oferta monitorável.

## Diagnóstico e limites

`/lojas` mostra o CEP configurado e o último resultado regional consultado; HTTP 200 não comprova leitura de preço. `python -m scripts.diagnose_groceries --cep SEU_CEP` consulta uma página individual por mercado, grava relatório em `data/` e não cria monitoramentos nem envia Telegram.

Listas padrão do instalador incluem os quatro mercados; listas personalizadas são preservadas. As rotas públicas respeitam robots.txt, recusas de acesso, limites e pausas do Fetcher. Os POSTs ficam restritos a seleção regional, validação de sessão, busca pública e simulação isolada; não permitem publicar pedidos ou pagamentos. A busca HTML do Extra é proibida por robots.txt e não é utilizada; a API pública tem suas próprias regras verificadas.

Os testes sintéticos cobrem região divergente, persistência do CEP/modo, botões e entrada de localização, preço/kg versus total, produto errado, estoque, entrega, mudança de série por região/modo e alertas sem pagamento ou disponibilidade física inventados. A suíte tem 655 testes aprovados. Consulte a [referência oficial do Checkout VTEX](https://developers.vtex.com/docs/api-reference/checkout-api) e a [referência dos campos e unidades](https://developers.vtex.com/docs/guides/orderform-fields).
