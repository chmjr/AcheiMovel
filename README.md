# Radar Imobiliario Floripa

Sistema pessoal para encontrar, analisar e ranquear oportunidades imobiliarias em Florianopolis e regiao, com foco em compra, reforma leve/media e revenda.

## Escopo inicial

- API FastAPI com token via `X-Radar-Token`.
- Painel Next.js para ranking e configuracoes.
- Motor financeiro inicial com cenarios a vista e financiado.
- Score 0-100 com filtros de capital, lucro, margem e risco.
- Infra local com PostgreSQL e Redis via Docker Compose.

## Desenvolvimento local

1. Copie `.env.example` para `.env`.
2. Ajuste `RADAR_API_TOKEN` e `RADAR_API_TOKEN_WEB` para o mesmo valor.
3. Instale uma das opcoes de banco:

- Docker Desktop local; ou
- PostgreSQL no Railway.

4. Suba infra local, se estiver usando Docker:

```bash
docker compose -f infra/docker-compose.yml up -d
```

5. API:

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn radar.main:app --reload
```

6. Web:

```bash
cd apps/web
npm install
npm run dev
```

## Proximos marcos

- Conectar fontes automáticas que não bloqueiem coleta.
- Scraper Caixa com registro de bloqueio/execução.
- RQ worker e scheduler.
- Alertas Telegram.

## Banco de dados

A primeira migration cria as tabelas centrais do MVP:

- imoveis canonicos;
- anuncios brutos por fonte;
- historico de preco;
- detalhes de leilao e banco;
- estatisticas por bairro;
- analises financeiras;
- perfil do investidor;
- watchlist, alertas e logs de scraping.

Com PostgreSQL local rodando:

```bash
cd apps/api
.venv\Scripts\activate
alembic upgrade head
```

Use `DATABASE_URL=postgresql+psycopg://...` para apontar para PostgreSQL com o driver `psycopg` v3.

Para Railway usando TCP proxy, o formato fica assim:

```env
DATABASE_URL=postgresql+psycopg://USUARIO:SENHA@nozomi.proxy.rlwy.net:12948/NOME_DO_BANCO
```

No Railway, pegue `USUARIO`, `SENHA` e `NOME_DO_BANCO` nas variáveis do serviço PostgreSQL, normalmente `PGUSER`, `PGPASSWORD` e `PGDATABASE`.

## Coleta automática

O produto deve operar por scrapers, não por cadastro manual.

Para disparar a Caixa pela API:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/scrapers/caixa/trigger ^
  -H "X-Radar-Token: dev-token"
```

Para disparar Lance Já:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/scrapers/lanceja/trigger ^
  -H "X-Radar-Token: dev-token"
```

Para disparar Superbid e Leiloeiro Público:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/scrapers/superbid/trigger ^
  -H "X-Radar-Token: dev-token"

curl -X POST http://127.0.0.1:8000/api/v1/scrapers/leiloeiro-publico/trigger ^
  -H "X-Radar-Token: dev-token"

curl -X POST http://127.0.0.1:8000/api/v1/scrapers/mega-leiloes/trigger ^
  -H "X-Radar-Token: dev-token"

curl -X POST http://127.0.0.1:8000/api/v1/scrapers/quintoandar/trigger ^
  -H "X-Radar-Token: dev-token"

curl -X POST http://127.0.0.1:8000/api/v1/scrapers/olx/trigger ^
  -H "X-Radar-Token: dev-token"

curl -X POST http://127.0.0.1:8000/api/v1/scrapers/zap/trigger ^
  -H "X-Radar-Token: dev-token"
```

Para rodar por comando, útil em cron/Railway:

```bash
cd apps/api
.venv\Scripts\python.exe -m radar.workers.run_scrapers caixa
.venv\Scripts\python.exe -m radar.workers.run_scrapers lanceja
.venv\Scripts\python.exe -m radar.workers.run_scrapers superbid
.venv\Scripts\python.exe -m radar.workers.run_scrapers leiloeiro_publico
.venv\Scripts\python.exe -m radar.workers.run_scrapers mega_leiloes
.venv\Scripts\python.exe -m radar.workers.run_scrapers quintoandar
.venv\Scripts\python.exe -m radar.workers.run_scrapers olx
.venv\Scripts\python.exe -m radar.workers.run_scrapers zap
```

Para consultar o histórico:

```bash
curl http://127.0.0.1:8000/api/v1/scrapers/runs ^
  -H "X-Radar-Token: dev-token"
```

Observação: a Caixa pode responder com bloqueio anti-bot/captcha. O sistema registra isso em `scrape_runs` em vez de fingir sucesso.

## Estratégias permitidas para páginas difíceis

- Usar páginas públicas de categoria, cidade, sitemap ou busca.
- Ler JSON público embutido na página, como `__NEXT_DATA__`.
- Seguir paginação pública e links internos do próprio site.
- Usar Playwright para renderizar páginas JavaScript quando o conteúdo é público.
- Aplicar rate limit, retry com backoff e registro de falhas.
- Registrar bloqueio por captcha/bot manager em `scrape_runs`.

Não implementar bypass de captcha, login obrigatório, paywall, bloqueio anti-bot ou restrições explícitas do site.

Mais detalhes em `docs/FONTES_E_COLETA.md`.

## Cadastro manual de imóvel técnico

O endpoint manual existe apenas para teste técnico e carga controlada. Não é o fluxo principal do produto.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/properties/manual ^
  -H "Content-Type: application/json" ^
  -H "X-Radar-Token: dev-token" ^
  -d "{\"title\":\"Apartamento antigo no Kobrasol\",\"property_type\":\"apartamento\",\"category\":\"common\",\"city\":\"São José\",\"neighborhood\":\"Kobrasol\",\"purchase_price\":220000,\"area_privative\":72,\"condo_fee\":520,\"iptu_yearly\":1200,\"bedrooms\":2,\"bathrooms\":1,\"parking_spots\":1,\"source_name\":\"Cadastro manual\"}"
```

Esse fluxo cria:

- um imóvel canônico em `properties`;
- um anúncio de origem manual em `source_listings`;
- a primeira linha de histórico em `price_history`.
