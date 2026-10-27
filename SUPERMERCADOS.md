# Supermercados: descoberta de links e preços regionais pendentes

Versão 2026.10.27-grocery-search.1.

Atacadão, Extra Mercado, Carrefour Mercado e Boa Supermercados estão registrados para descoberta de links públicos. **Monitoramento de preços regionais e Promoções desses mercados ainda não estão disponíveis.** Não basta adicionar os domínios para concluir essa integração.

A busca por cortes de carne prioriza os supermercados e os marketplaces gerais autorizados, sem consumir consultas em lojas de informática, móveis ou roupas. Utensílios como faca para picanha continuam na busca geral. Picanha resfriada não aceita congelada quando o usuário especifica resfriada; hambúrguer e tempero não substituem o corte.

Para picanha, o Carrefour usa sua categoria pública observada antes do índice externo. Em consulta real com o Fetcher em 27/10/2026, essa categoria forneceu nove links individuais. Isso comprova descoberta de links, não preço regional. A categoria bovina do Atacadão abriu sem links reconhecidos, portanto não foi habilitada como fonte operacional de descoberta.

Na consulta anterior, a página individual da Picanha Maturatta do Atacadão forneceu preço zero nos dados estruturados. Zero não é promoção. O Extra respondeu 403; abrir a página inicial dos outros mercados não comprova acesso às ofertas.

Os adaptadores conservam título e identificadores, mas retiram preço e disponibilidade não regionalizados para impedir histórico e alertas incorretos. Os resultados aparecem como links para conferência, sem botão de monitoramento e sem cadastro de anúncio monitorável. O resumo diferencia falta de verificação de falta de estoque e informa a conclusão da pesquisa. O menu de Promoções avisa sobre a pendência regional.

Para concluir: obter o CEP do usuário, validar a seleção pública da loja de atendimento e a persistência da região nas verificações. Exigir preço por kg vinculado ao produto; distinguir total estimado por peça, clube, quantidade mínima, congelada/resfriada e forma de pagamento. Não usar preços de snippets, contas privadas, CAPTCHA ou contorno de bloqueios.

Listas padrão do instalador incluem os quatro domínios; listas personalizadas são preservadas. Testes sintéticos verificam roteamento, descoberta nativa, acentos e proteção contra alertas indevidos. Não comprovam cobertura operacional de preços nos quatro mercados.
