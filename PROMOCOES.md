# Busca de promocoes com evidencia de preco

Versao `2026.10.25-market-evidence.1`. O percentual anunciado no site e informativo; o filtro usa economia comparada ou uma queda documentada no historico observado. Veja as regras e exemplos em [COMPARACAO-DE-PRECOS.md](COMPARACAO-DE-PRECOS.md).

## Fluxo no Telegram

1. Escolha a categoria e a subcategoria, ou Tudo nesta categoria.
2. Escolha Maior que 5%, 10%, 20%, 30%, 40%, 50%, 60%, 70% ou 80%. A comparacao e estrita: exatamente 5% nao passa no filtro Maior que 5%.
3. Para Lacoste, escolha tamanho ou ignorar tamanho.
4. Marque as lojas; nenhuma comeca marcada. TODAS marca as compativeis com a categoria. Para comprovar vantagem de mercado sem historico, selecione ao menos tres lojas.
5. Escolha busca Ampliada (48 produtos/loja) ou Rapida (12) e toque em Pesquisar agora.

Somente produtos com identificacao e condicoes comparaveis confirmam economia. Cupons, assinatura, variante, estoque e forma de pagamento sao considerados. Frete nao esta incluido. Nao se aceita o percentual da loja como prova, nem preco de resultado de busca externa. Se faltarem dados, o bot informa que nao conseguiu comprovar, sem afirmar que nao existe promocao.

O resultado termina em Pesquisa finalizada. Cartoes com vantagem trazem os precos e links usados. Queda observada apenas no historico e rotulada separadamente, sem afirmar melhor preco do mercado. Os avisos tecnicos continuam no diagnostico, sem inundar o Telegram.

A pesquisa pode registrar observacoes para futuras comparacoes, mas nao cria monitoramentos, jobs de alerta nem mensagens automaticas de queda. O acompanhamento continua dependendo da escolha explicita do usuario.

## Fontes por loja

KaBuM e Terabyte usam categorias mapeadas. Pichau prioriza sitemap publico filtrado. Lacoste usa Sale/categorias e sitemap de imagens para descoberta textual. Patoloco usa categorias observadas e microdados Product/Offer da pagina. Outras lojas usam os adaptadores existentes, quando habilitadas e compativeis com a categoria. O preco e lido novamente na loja.

As comparacoes complementares sao limitadas e ocorrem somente nas lojas escolhidas, inclusive para categorias mapeadas. Os limites globais evitam multiplicar buscas por cada produto. Bloqueios e restricoes de acesso sao respeitados e pausas sobrevivem ao reinicio. `/lojas` informa o estado atual de acesso.

Amostra ampliada nao e varredura integral. Uma loja pode omitir dados essenciais ou bloquear acesso; isso nao e transformado em promocao confirmada. Categorias, links livres, CEP e tamanho continuam sujeitos a validacao. O CEP nao gera cotacao de frete. A selecao expira em trinta minutos.
