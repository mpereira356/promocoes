# Auditoria de buscas — 21/10/2026

Versão: `2026.10.21-store-search.1`. Consultas pertinentes a cada loja, com o transporte de produção, sem Telegram ou alterações no SQLite. Resultados locais não comprovam acesso na VPS nem disponibilidade futura. Ler preço não significa estoque disponível ou dados suficientes para alertas.

| Loja | Resultado da amostra |
| --- | --- |
| KaBuM | Busca e preço lidos: SSD Kingston NV3 1TB. |
| Pichau | Busca e preço lidos: Gigabyte B550 Aorus Elite V2. |
| Terabyte | Busca e preço lidos: B550 Aorus Elite V2; produto indisponível. |
| Mercado Livre | Links encontrados; robots.txt do host de ofertas retornou 403. Catálogos não são ofertas individuais. |
| Amazon | Busca de boné e preço lidos. Pagamento e condição ausentes na amostra. |
| Sensetup | Busca e preço de cadeira lidos; estoque não confirmado. |
| Elements | Busca e preço de cadeira lidos. |
| Flexform | Busca e preço de cadeira lidos. |
| Shopee | Links de bonés encontrados; página retornou somente a estrutura JavaScript, sem oferta verificável. |
| Magalu | Links de freezers encontrados; página do produto retornou 403. |
| Frigelar | Busca e preço de freezer lidos; produto indisponível. |
| Brastemp | Busca e preço de freezer lidos; produto indisponível. |
| Lacoste | Busca do boné pelo sitemap e preço lidos. Sale retornou camisetas de R$ 429,00 por R$ 299,00 em três cores. |

O sitemap de imagens da Lacoste substituiu a rota de pesquisa proibida pelo robots.txt. Corrigidos aliases por EAN/referência-cor, identificação de cor, tamanho TU e preço riscado no bloco do produto. O seletor de tamanhos da camiseta depende de rota proibida: tamanhos desconhecidos continuam excluídos quando há filtro.

Detalhes JSON locais em `data/all-stores-audit-20261021.json`, `data/clothing-live-corrected-20261021.json`, `data/lacoste-verified-20261021.json` e `data/lacoste-promotions-live-20261021.json`. Consultas com acentos corrompidos no primeiro diagnóstico foram substituídas por consultas corretas no segundo. Somente capturas públicas reduzidas foram incluídas nas fixtures, sem dados de sessão.

## Conferir no servidor

Depois de instalar esta versão:

```bash
cd /opt/price-monitor
sudo -u pricebot .venv/bin/python -m scripts.diagnose_all_stores --browser
```

Verifica todas as lojas habilitadas, continua após falhas e grava `data/all-stores-diagnostic.json`. Distingue preço lido, links sem preço, bloqueio, ausência de resultado e tempo esgotado. Não envia mensagens nem grava preços no banco. Limite por loja: 90 segundos, configurável com `--timeout`.

Os 13 adaptadores estão configurados. Não se afirma que os 13 sites permitem leitura automática: Mercado Livre, Magalu e Shopee continuaram sem preço verificável nesta amostra. Links externos não substituem preço lido na página.
