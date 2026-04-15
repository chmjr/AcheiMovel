# Radar Imobiliário Floripa — Especificação Técnica do MVP

> Sistema pessoal de arbitragem imobiliária para Florianópolis e região metropolitana.
> Encontra, analisa e ranqueia oportunidades de compra → reforma → revenda.

---

## 1. Visão Geral

### 1.1. Tese
Identificar imóveis com potencial real de gerar **lucro líquido ≥ R$ 80.000** em **6 a 12 meses**, usando até **R$ 300.000 de capital inicial** (com ou sem financiamento), em Florianópolis, São José, Palhoça e Biguaçu.

### 1.2. Princípios de design
- **Motor financeiro antes de scraping.** Sem cálculo correto, dado bruto não vale nada.
- **Dado bruto nunca é descartado.** Toda coleta vai para `raw_listings` e pode ser reprocessada.
- **Mediana e percentis, nunca só média.** Mercado imobiliário tem outliers demais.
- **Ranking por lucro líquido e capital empregado**, não por preço barato.
- **Leilão é categoria separada**, com pesos e cortes próprios.
- **Conectores isolados.** Cada fonte é um módulo plugável.

### 1.3. Critérios de corte (filtros duros, antes do score)
| Critério | Corte |
|---|---|
| Capital inicial necessário | > R$ 300.000 → descarta |
| Lucro líquido estimado | < R$ 80.000 → descarta |
| Margem estimada | < 30% → descarta |
| Prazo estimado | > 12 meses → penaliza pesado |
| Score | < 50 → fora do radar principal |
| Leilão ocupado + desconto < 45% | → descarta |
| Sem matrícula/edital em leilão | → fila manual |

---

## 2. Arquitetura

### 2.1. Stack
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic
- **Frontend:** Next.js 15 (App Router) + TypeScript + TailwindCSS + shadcn/ui
- **Banco:** PostgreSQL 16
- **Fila/jobs:** RQ + Redis (mais simples que Celery para o MVP)
- **Scraping:** Playwright + httpx + selectolax
- **Alertas:** Telegram Bot API
- **Auth:** Token estático via header `X-Radar-Token` + allowlist de IP opcional
- **Deploy:** Railway (monorepo)
- **Observabilidade:** Logfire ou Sentry + logs estruturados (structlog)

### 2.2. Fluxo de dados
```
[Scrapers] → raw_listings → [Normalizer] → properties
                                              ↓
                                        [Deduplicator]
                                              ↓
                                    [Market Estimator] ← neighborhood_stats
                                              ↓
                                       [Deal Analyzer] → deal_analyses
                                              ↓
                                      [Scoring Engine]
                                              ↓
                              [Dashboard Web] + [Telegram Alerts]
```

### 2.3. Estrutura de pastas (monorepo)
```
radar-floripa/
├── apps/
│   ├── api/                    # FastAPI
│   │   ├── radar/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── models/         # SQLAlchemy
│   │   │   ├── schemas/        # Pydantic
│   │   │   ├── routes/
│   │   │   ├── services/
│   │   │   │   ├── analyzer.py
│   │   │   │   ├── scoring.py
│   │   │   │   ├── market.py
│   │   │   │   └── renovation.py
│   │   │   ├── scrapers/
│   │   │   │   ├── base.py
│   │   │   │   ├── caixa.py
│   │   │   │   ├── olx.py
│   │   │   │   ├── zap.py
│   │   │   │   └── leiloes/
│   │   │   ├── workers/
│   │   │   │   ├── scrape_jobs.py
│   │   │   │   └── analyze_jobs.py
│   │   │   ├── alerts/
│   │   │   │   └── telegram.py
│   │   │   └── auth.py
│   │   ├── alembic/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── web/                    # Next.js
│       ├── app/
│       │   ├── (dashboard)/
│       │   │   ├── page.tsx              # Ranking
│       │   │   ├── deals/[id]/page.tsx   # Detalhe
│       │   │   ├── settings/page.tsx
│       │   │   └── market/page.tsx       # Stats por bairro
│       │   └── api/                      # BFF (proxy auth)
│       ├── components/
│       ├── lib/
│       ├── package.json
│       └── Dockerfile
├── packages/
│   └── shared-types/           # Tipos compartilhados (gerados do OpenAPI)
├── infra/
│   ├── railway.json
│   └── docker-compose.yml      # Dev local
├── .env.example
└── README.md
```

### 2.4. Serviços no Railway
1. **api** — FastAPI (web)
2. **worker** — RQ worker (scrapers + análise)
3. **scheduler** — rq-scheduler (cron jobs)
4. **web** — Next.js
5. **postgres** — plugin Railway
6. **redis** — plugin Railway

---

## 3. Modelagem do Banco

### 3.1. Tabelas principais

```sql
-- Imóveis canônicos (após normalização e dedup)
CREATE TABLE properties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint     TEXT UNIQUE NOT NULL,        -- hash p/ dedup
    property_type   TEXT NOT NULL,               -- apartamento, casa, terreno, comercial
    city            TEXT NOT NULL,
    neighborhood    TEXT NOT NULL,
    address         TEXT,
    lat             NUMERIC(10,7),
    lng             NUMERIC(10,7),
    area_privative  NUMERIC(10,2),
    area_total      NUMERIC(10,2),
    bedrooms        INT,
    bathrooms       INT,
    parking_spots   INT,
    floor           INT,
    has_elevator    BOOLEAN,
    age_years       INT,
    condition       TEXT,                        -- novo, bom, regular, reforma_leve, reforma_media, reforma_pesada
    category        TEXT NOT NULL,               -- common, bank_owned, auction
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_properties_city_neigh ON properties(city, neighborhood);
CREATE INDEX idx_properties_category ON properties(category);

-- Anúncios brutos (1 imóvel pode ter N source_listings)
CREATE TABLE source_listings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID REFERENCES properties(id) ON DELETE CASCADE,
    source          TEXT NOT NULL,               -- caixa, olx, zap, vivareal, leilao_x
    source_url      TEXT NOT NULL,
    source_id       TEXT,                        -- id do anúncio na fonte
    title           TEXT,
    description     TEXT,
    price           NUMERIC(14,2),
    condo_fee       NUMERIC(10,2),
    iptu_yearly     NUMERIC(10,2),
    photos          JSONB,                       -- array de URLs
    raw_payload     JSONB,                       -- HTML/JSON cru do scraper
    listed_at       TIMESTAMPTZ,
    last_seen_at    TIMESTAMPTZ DEFAULT now(),
    is_active       BOOLEAN DEFAULT true,
    UNIQUE(source, source_id)
);

CREATE INDEX idx_source_listings_active ON source_listings(is_active, last_seen_at);

-- Histórico de preço (cada vez que o preço muda, grava)
CREATE TABLE price_history (
    id              BIGSERIAL PRIMARY KEY,
    source_listing_id UUID REFERENCES source_listings(id) ON DELETE CASCADE,
    price           NUMERIC(14,2) NOT NULL,
    captured_at     TIMESTAMPTZ DEFAULT now()
);

-- Dados específicos de leilão
CREATE TABLE auction_details (
    source_listing_id UUID PRIMARY KEY REFERENCES source_listings(id) ON DELETE CASCADE,
    auction_type    TEXT,                        -- judicial, extrajudicial
    auctioneer      TEXT,
    appraisal_value NUMERIC(14,2),
    minimum_bid     NUMERIC(14,2),
    discount_pct    NUMERIC(5,2),
    is_occupied     BOOLEAN,
    auction_date    TIMESTAMPTZ,
    second_auction_date TIMESTAMPTZ,
    matricula       TEXT,
    debts_disclosed NUMERIC(14,2),
    auctioneer_fee_pct NUMERIC(5,2),
    edital_url      TEXT,
    financeable     BOOLEAN
);

-- Dados de imóvel de banco
CREATE TABLE bank_owned_details (
    source_listing_id UUID PRIMARY KEY REFERENCES source_listings(id) ON DELETE CASCADE,
    bank            TEXT NOT NULL,               -- caixa, santander, itau, etc
    sale_modality   TEXT,                        -- venda direta, licitação, leilão SFI
    discount_pct    NUMERIC(5,2),
    financeable     BOOLEAN,
    fgts_allowed    BOOLEAN,
    minimum_entry_pct NUMERIC(5,2)
);

-- Estatísticas de mercado por bairro
CREATE TABLE neighborhood_stats (
    id              BIGSERIAL PRIMARY KEY,
    city            TEXT NOT NULL,
    neighborhood    TEXT NOT NULL,
    property_type   TEXT NOT NULL,
    sample_size     INT NOT NULL,
    price_per_sqm_p25  NUMERIC(10,2),
    price_per_sqm_p50  NUMERIC(10,2),            -- mediana
    price_per_sqm_p65  NUMERIC(10,2),
    price_per_sqm_p75  NUMERIC(10,2),
    avg_days_listed INT,
    liquidity_score NUMERIC(3,1),                -- 0-10
    computed_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE(city, neighborhood, property_type)
);

-- Análise financeira (1 por property + cenário)
CREATE TABLE deal_analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID REFERENCES properties(id) ON DELETE CASCADE,
    scenario        TEXT NOT NULL,               -- conservative, base, optimistic
    financing_mode  TEXT NOT NULL,               -- cash, financed
    purchase_price  NUMERIC(14,2),
    estimated_market_value NUMERIC(14,2),
    estimated_resale_value NUMERIC(14,2),
    renovation_level TEXT,                       -- light, medium
    renovation_cost NUMERIC(14,2),
    transaction_costs NUMERIC(14,2),             -- ITBI, cartório
    holding_costs   NUMERIC(14,2),               -- condo + IPTU + custo capital
    selling_costs   NUMERIC(14,2),               -- corretagem
    contingency     NUMERIC(14,2),
    total_cost      NUMERIC(14,2),
    capital_required NUMERIC(14,2),              -- entrada + reforma + custos (o que sai do bolso)
    estimated_profit NUMERIC(14,2),
    margin_pct      NUMERIC(5,2),
    roi_pct         NUMERIC(5,2),
    annualized_roi_pct NUMERIC(6,2),
    estimated_months INT,
    risk_level      TEXT,                        -- low, medium, high
    risk_flags      JSONB,                       -- ["ocupado", "matricula_indisponivel", ...]
    score           NUMERIC(5,2),
    decision        TEXT,                        -- discard, monitor, analyze, priority, immediate
    score_breakdown JSONB,                       -- {discount: 25, margin: 20, ...}
    computed_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_deal_analyses_score ON deal_analyses(score DESC) WHERE scenario = 'base';
CREATE INDEX idx_deal_analyses_decision ON deal_analyses(decision);

-- Configurações do investidor (singleton para uso pessoal)
CREATE TABLE investor_profile (
    id              INT PRIMARY KEY DEFAULT 1,
    max_capital     NUMERIC(14,2) DEFAULT 300000,
    min_profit      NUMERIC(14,2) DEFAULT 80000,
    min_margin_pct  NUMERIC(5,2) DEFAULT 30,
    min_score       INT DEFAULT 50,
    max_months      INT DEFAULT 12,
    allow_financing BOOLEAN DEFAULT true,
    default_entry_pct NUMERIC(5,2) DEFAULT 25,
    interest_rate_yearly NUMERIC(5,2) DEFAULT 11,  -- pra custo de capital
    target_cities   JSONB DEFAULT '["Florianópolis","São José","Palhoça","Biguaçu"]',
    CONSTRAINT singleton CHECK (id = 1)
);

-- Watchlist manual
CREATE TABLE watchlist (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID REFERENCES properties(id) ON DELETE CASCADE,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Regras de alerta
CREATE TABLE alert_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    enabled         BOOLEAN DEFAULT true,
    conditions      JSONB NOT NULL,              -- {min_score: 80, max_capital: 250000, ...}
    channel         TEXT NOT NULL,               -- telegram, email
    cooldown_minutes INT DEFAULT 60
);

CREATE TABLE alerts_sent (
    id              BIGSERIAL PRIMARY KEY,
    alert_rule_id   UUID REFERENCES alert_rules(id),
    property_id     UUID REFERENCES properties(id),
    sent_at         TIMESTAMPTZ DEFAULT now()
);

-- Logs de scraping
CREATE TABLE scrape_runs (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    started_at      TIMESTAMPTZ DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT,                        -- running, success, partial, failed
    items_collected INT DEFAULT 0,
    items_new       INT DEFAULT 0,
    items_updated   INT DEFAULT 0,
    error           TEXT
);
```

---

## 4. Fórmulas

### 4.1. Custo total (modo à vista)
```
total_cost = purchase_price
           + ITBI (3% Florianópolis)
           + cartório/registro (~1.5%)
           + renovation_cost
           + (condo_fee + iptu_monthly) × estimated_months
           + selling_costs (6% sobre revenda)
           + contingency (12% sobre reforma + custos)
```

### 4.2. Capital empregado (modo financiado) — **o número que importa**
```
entry          = purchase_price × default_entry_pct
financing_costs = purchase_price × 4% (avaliação, registro, seguros)
monthly_payment = PMT(financed_amount, rate, term)
holding_finance = monthly_payment × estimated_months

capital_required = entry
                 + financing_costs
                 + ITBI
                 + cartório
                 + renovation_cost
                 + holding_finance
                 + contingency
```
> **Esse é o filtro de R$ 300.000.** Não o total_cost.

### 4.3. Valor de revenda
```
base_price_per_sqm = neighborhood_stats.price_per_sqm_p50

# Ajustes (cada um aplica multiplicador)
adjustments = {
    'condition_post_reno': 1.10 if reforma_media else 1.05,
    'no_parking': 0.93,
    'no_elevator_4plus_floor': 0.92,
    'low_floor_apt': 0.97,
    'high_condo_fee': 0.95,
    'long_listed_neighborhood': 0.95,
}

resale_conservative = area × p50 × Π(adjustments) × 0.95
resale_base         = area × p50 × Π(adjustments)
resale_optimistic   = area × p65 × Π(adjustments)
```

### 4.4. Lucro, margem, ROI
```
profit             = resale_value - total_cost
margin_pct         = profit / resale_value × 100
roi_pct            = profit / capital_required × 100
annualized_roi_pct = ((1 + roi_pct/100) ^ (12/months) - 1) × 100
```

### 4.5. Reforma (R$/m² para Floripa, ajustável)
```
reforma_leve  = area × R$ 600/m²    (range R$ 400-800)
reforma_media = area × R$ 1.200/m²  (range R$ 900-1.600)
```

### 4.6. Score 0-100
```python
def compute_score(deal: DealAnalysis) -> tuple[float, dict]:
    breakdown = {}

    # 1. Desconto vs mercado (30 pts)
    discount = (deal.estimated_market_value - deal.purchase_price) / deal.estimated_market_value
    if discount >= 0.30:   breakdown['discount'] = 30
    elif discount >= 0.20: breakdown['discount'] = 20
    elif discount >= 0.10: breakdown['discount'] = 10
    else:                  breakdown['discount'] = 0

    # 2. Margem líquida (25 pts)
    if deal.margin_pct >= 35:   breakdown['margin'] = 25
    elif deal.margin_pct >= 30: breakdown['margin'] = 20
    elif deal.margin_pct >= 25: breakdown['margin'] = 12
    elif deal.margin_pct >= 15: breakdown['margin'] = 6
    else:                       breakdown['margin'] = 0

    # 3. Liquidez do bairro (15 pts)
    breakdown['liquidity'] = min(15, deal.liquidity_score * 1.5)

    # 4. Risco (10 pts) — invertido
    breakdown['risk'] = {'low': 10, 'medium': 5, 'high': 0}[deal.risk_level]

    # 5. Reforma (10 pts)
    breakdown['renovation'] = {'light': 10, 'medium': 6, 'heavy': 2}[deal.renovation_level]

    # 6. Qualidade dos dados (5 pts)
    breakdown['data_quality'] = score_data_completeness(deal)  # 0-5

    # 7. Compatibilidade de capital (5 pts)
    ratio = deal.capital_required / investor.max_capital
    if ratio <= 0.6:   breakdown['capital_fit'] = 5
    elif ratio <= 0.8: breakdown['capital_fit'] = 4
    elif ratio <= 1.0: breakdown['capital_fit'] = 2
    else:              breakdown['capital_fit'] = 0

    total = sum(breakdown.values())
    return total, breakdown
```

### 4.7. Decisão
```
score < 50           → discard
50-65 + margin ≥ 30  → monitor
66-80                → analyze
81-90                → priority
91-100               → immediate
```

---

## 5. API REST

### 5.1. Auth
Todo endpoint exige header `X-Radar-Token: <token>`. Token vem de env var `RADAR_API_TOKEN`. Middleware retorna 401 se ausente/inválido.

Opcionalmente: allowlist de IPs via `RADAR_ALLOWED_IPS` (CSV).

### 5.2. Endpoints

```
GET  /health
GET  /api/v1/deals                  # ranking principal, com filtros via query
     ?min_score=50&max_capital=300000&city=Florianópolis&category=auction
     &order_by=score|profit|annualized_roi|capital_required
     &limit=50&offset=0

GET  /api/v1/deals/{id}             # detalhe completo
     # retorna: property, source_listings, deal_analyses (3 cenários × 2 modos),
     # comparables, price_history, risk_flags, checklist

GET  /api/v1/properties/{id}/comparables
     # imóveis similares no bairro

POST /api/v1/properties/{id}/recompute
     # reanalisa com configs atuais

GET  /api/v1/market/stats
     ?city=Florianópolis&neighborhood=Centro&type=apartamento

GET  /api/v1/market/heatmap         # dados pro mapa

GET  /api/v1/watchlist
POST /api/v1/watchlist
DEL  /api/v1/watchlist/{id}

GET  /api/v1/settings               # investor_profile
PUT  /api/v1/settings

GET  /api/v1/alerts/rules
POST /api/v1/alerts/rules
PUT  /api/v1/alerts/rules/{id}
DEL  /api/v1/alerts/rules/{id}

POST /api/v1/scrapers/{source}/trigger   # disparo manual
GET  /api/v1/scrapers/runs               # histórico
```

### 5.3. Schema de exemplo (GET /deals)
```json
{
  "items": [{
    "property_id": "uuid",
    "score": 84,
    "decision": "priority",
    "category": "bank_owned",
    "city": "São José",
    "neighborhood": "Kobrasol",
    "property_type": "apartamento",
    "purchase_price": 285000,
    "estimated_market_value": 410000,
    "estimated_resale_value": 470000,
    "renovation_cost": 48000,
    "total_cost": 392000,
    "capital_required": 178000,
    "estimated_profit": 78000,
    "margin_pct": 16.6,
    "roi_pct": 43.8,
    "annualized_roi_pct": 56.1,
    "estimated_months": 10,
    "risk_level": "low",
    "primary_source_url": "https://venda-imoveis.caixa.gov.br/...",
    "source_count": 2,
    "first_seen_at": "2026-04-10T09:00:00Z"
  }],
  "total": 23,
  "facets": { "by_category": {...}, "by_city": {...} }
}
```

---

## 6. Scrapers

### 6.1. Contrato base

```python
# apps/api/radar/scrapers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator
from decimal import Decimal

@dataclass
class RawListing:
    source: str
    source_id: str
    source_url: str
    title: str
    description: str | None
    price: Decimal | None
    condo_fee: Decimal | None
    iptu_yearly: Decimal | None
    city: str
    neighborhood: str | None
    address: str | None
    property_type: str
    area_privative: Decimal | None
    bedrooms: int | None
    bathrooms: int | None
    parking_spots: int | None
    photos: list[str]
    listed_at: str | None
    raw_payload: dict
    # Campos opcionais por categoria
    auction_data: dict | None = None
    bank_data: dict | None = None

class BaseScraper(ABC):
    source: str
    category: str  # common, bank_owned, auction

    @abstractmethod
    async def discover(self) -> AsyncIterator[str]:
        """Yields URLs de listagem para scrapear em detalhe."""

    @abstractmethod
    async def parse(self, url: str) -> RawListing | None:
        """Extrai dados de uma URL específica."""

    async def run(self, run_id: int) -> dict:
        stats = {'collected': 0, 'new': 0, 'updated': 0, 'errors': 0}
        async for url in self.discover():
            try:
                listing = await self.parse(url)
                if listing:
                    result = await persist(listing)  # upsert + dedup
                    stats[result] += 1
                stats['collected'] += 1
            except Exception as e:
                logger.exception("scrape_error", source=self.source, url=url)
                stats['errors'] += 1
        return stats
```

### 6.2. Caixa Imóveis (esqueleto)

A Caixa expõe consultas via formulário POST que retorna HTML paginado. A busca aceita filtros por UF e cidade.

```python
# apps/api/radar/scrapers/caixa.py
import httpx
from selectolax.parser import HTMLParser
from .base import BaseScraper, RawListing

CAIXA_SEARCH = "https://venda-imoveis.caixa.gov.br/sistema/carregaListaImoveis.asp"
CAIXA_DETAIL = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnImovel={id}"

class CaixaScraper(BaseScraper):
    source = "caixa"
    category = "bank_owned"

    CITIES = ["FLORIANÓPOLIS", "SÃO JOSÉ", "PALHOÇA", "BIGUAÇU"]

    async def discover(self):
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for city in self.CITIES:
                payload = {
                    "hdn_estado": "SC",
                    "hdn_cidade": city,
                    "hdn_tp_venda": "",          # todas as modalidades
                    "hdn_tp_imovel": "",
                    "hdn_area_util": "",
                    "hdn_qtd_quarto": "",
                    "hdn_vlr_venda": "",
                }
                r = await client.post(CAIXA_SEARCH, data=payload)
                tree = HTMLParser(r.text)
                for a in tree.css("a[onclick*='detalhe_imovel']"):
                    imovel_id = self._extract_id(a.attributes.get("onclick", ""))
                    if imovel_id:
                        yield CAIXA_DETAIL.format(id=imovel_id)

    async def parse(self, url: str) -> RawListing | None:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            tree = HTMLParser(r.text)

            # Caixa tem estrutura razoavelmente estável de <p><strong>label</strong> valor</p>
            fields = self._extract_fields(tree)

            return RawListing(
                source=self.source,
                source_id=fields["matricula_imovel"],
                source_url=url,
                title=fields.get("tipo_imovel", "Imóvel Caixa"),
                description=fields.get("descricao"),
                price=parse_brl(fields.get("valor_venda")),
                condo_fee=None,
                iptu_yearly=None,
                city=fields.get("cidade"),
                neighborhood=fields.get("bairro"),
                address=fields.get("endereco"),
                property_type=normalize_type(fields.get("tipo_imovel")),
                area_privative=parse_area(fields.get("area_privativa")),
                bedrooms=parse_int(fields.get("quartos")),
                bathrooms=parse_int(fields.get("banheiros")),
                parking_spots=parse_int(fields.get("vagas")),
                photos=self._extract_photos(tree),
                listed_at=None,
                raw_payload={"html": r.text, "fields": fields},
                bank_data={
                    "bank": "caixa",
                    "sale_modality": fields.get("modalidade_venda"),
                    "discount_pct": compute_discount(
                        parse_brl(fields.get("valor_avaliacao")),
                        parse_brl(fields.get("valor_venda"))
                    ),
                    "financeable": "financiamento" in (fields.get("aceita_financiamento", "").lower()),
                    "fgts_allowed": "fgts" in (fields.get("aceita_fgts", "").lower()),
                    "minimum_entry_pct": None,
                }
            )

    def _extract_id(self, onclick: str) -> str | None:
        # detalhe_imovel('1234567890') → 1234567890
        import re
        m = re.search(r"'(\d+)'", onclick)
        return m.group(1) if m else None
```

> **Atenção operacional:** o portal da Caixa muda layout/parâmetros com alguma frequência. Mantenha o `raw_payload` completo (HTML cru) — se o parser quebrar, você reprocessa offline sem perder coletas.

### 6.3. OLX (esqueleto com Playwright)

OLX usa proteção anti-bot (Cloudflare/Akamai) e infinite scroll, então Playwright é necessário.

```python
# apps/api/radar/scrapers/olx.py
from playwright.async_api import async_playwright
from .base import BaseScraper, RawListing

OLX_LIST = "https://www.olx.com.br/imoveis/venda/estado-sc/grande-florianopolis-e-litoral-norte"

class OlxScraper(BaseScraper):
    source = "olx"
    category = "common"

    async def discover(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                viewport={"width": 1366, "height": 900},
            )
            page = await ctx.new_page()

            for page_num in range(1, 15):
                await page.goto(f"{OLX_LIST}?o={page_num}", wait_until="networkidle")
                await page.wait_for_selector("[data-ds-component='DS-AdCard']", timeout=10000)
                links = await page.eval_on_selector_all(
                    "a[data-ds-component='DS-AdCard'][href*='/imovel/']",
                    "els => els.map(e => e.href)"
                )
                for href in links:
                    yield href
                await page.wait_for_timeout(1500)  # respeitar o servidor

            await browser.close()

    async def parse(self, url: str) -> RawListing | None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")

            # OLX expõe um JSON com todos os dados via __NEXT_DATA__
            data = await page.evaluate("""() => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? JSON.parse(el.textContent) : null;
            }""")
            await browser.close()

            if not data:
                return None

            ad = data["props"]["pageProps"]["ad"]
            props = {p["name"]: p["value"] for p in ad.get("properties", [])}
            location = ad.get("location", {})

            return RawListing(
                source=self.source,
                source_id=str(ad["listId"]),
                source_url=url,
                title=ad.get("subject", ""),
                description=ad.get("body"),
                price=Decimal(str(ad.get("priceValue", 0))),
                condo_fee=parse_brl(props.get("condominio")),
                iptu_yearly=parse_brl(props.get("iptu")),
                city=location.get("municipality"),
                neighborhood=location.get("neighbourhood"),
                address=None,
                property_type=normalize_type(props.get("category")),
                area_privative=parse_area(props.get("size")),
                bedrooms=parse_int(props.get("rooms")),
                bathrooms=parse_int(props.get("bathrooms")),
                parking_spots=parse_int(props.get("garage_spaces")),
                photos=[img["original"] for img in ad.get("images", [])],
                listed_at=ad.get("listTime"),
                raw_payload=data,
            )
```

### 6.4. Zap/VivaReal

Zap e VivaReal são do mesmo grupo e expõem uma API GraphQL semi-pública (a mesma que o site consome). Estratégia recomendada:

1. **Playwright** para abrir página de listagem e capturar a chamada XHR via `page.on("response", ...)`.
2. Extrair o token CSRF / x-domain header.
3. Replicar com `httpx` direto na API GraphQL para todas as buscas seguintes.

A API retorna JSON estruturado — uma vez obtido o token, é muito mais leve que renderizar páginas.

### 6.5. Leiloeiros

Cada leiloeiro tem site próprio (Mega Leilões, Sodré Santoro, Lance Já, etc.). Padrão:
- Lista paginada de lotes em SC.
- Detalhe com PDF do edital → futuramente OCR para extrair débitos, ocupação, matrícula.
- No MVP, capturar campos visíveis e marcar `risk_level=high` por default. Edital fica como link.

### 6.6. Boas práticas obrigatórias

- **Rate limit por fonte.** No mínimo 1.5s entre requests, jitter aleatório.
- **User-Agent rotativo** (lista de UAs realistas).
- **Respeitar robots.txt** quando indicar `Disallow` para o path.
- **Cache de URLs vistas** (Redis SET com TTL de 24h) para não reprocessar tudo todo dia.
- **Retry com backoff exponencial** (3 tentativas).
- **Circuit breaker:** se uma fonte dá > 30% de erro em 100 requests, pausa por 1h e alerta.
- **Salvar `raw_payload` SEMPRE.** Reprocessamento offline é o que salva quando o parser quebra.

---

## 7. Deduplicação

Estratégia em duas camadas:

**Camada 1 — Fingerprint determinístico:**
```python
def fingerprint(listing: RawListing) -> str:
    parts = [
        normalize(listing.city),
        normalize(listing.neighborhood),
        listing.property_type,
        round_to(listing.area_privative, 5),     # arredonda pra 5m²
        listing.bedrooms,
        round_to(listing.price, 10000),          # arredonda preço pra 10k
    ]
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()
```

**Camada 2 — Similaridade (job assíncrono):**
- pgvector com embeddings de título + descrição
- Comparação de hashes perceptuais (pHash) das primeiras 3 fotos
- Threshold combinado: cosine > 0.85 E pHash distance < 8 → mesmo imóvel

Quando há match, faz merge: cria nova `source_listing` apontando para `property_id` existente.

---

## 8. Frontend

### 8.1. Telas
1. **Dashboard (/)** — Tabela de oportunidades + filtros laterais + KPIs no topo (total deals, score médio, lucro potencial agregado).
2. **Detalhe (/deals/[id])** — Resumo executivo, fotos em galeria, tabela de cenários (3 × 2 = 6 simulações), comparáveis, histórico de preço (sparkline), risk flags, checklist de visita, botão "salvar na watchlist".
3. **Mercado (/market)** — Heatmap por bairro com R$/m² mediano, tabela de stats, gráfico de evolução.
4. **Configurações (/settings)** — Form do `investor_profile` + regras de alerta + status dos scrapers.
5. **Watchlist (/watchlist)** — Imóveis salvos com notas pessoais.

### 8.2. Componentes-chave
- Tabela com TanStack Table (sorting, filtros, virtual scroll).
- Mapa com Leaflet + marker cluster.
- Sparkline com Recharts.
- shadcn/ui para forms e dialogs.

### 8.3. Auth no frontend
Token guardado em cookie HttpOnly setado por uma rota Next `/api/auth/login` que recebe o token via env var. Páginas usam middleware para checar presença do cookie.

---

## 9. Alertas

### 9.1. Telegram
Bot dedicado. Cada alerta envia mensagem rica:

```
🔥 OPORTUNIDADE FORTE — Score 87

🏢 Apto 2/1 — Kobrasol, São José
💰 Compra: R$ 285.000  (33% abaixo do mercado)
🔧 Reforma média: ~R$ 48.000
💵 Capital necessário: R$ 178.000
📈 Lucro estimado: R$ 92.000  (margem 28%, ROI 51%)
⏱  Prazo: 10 meses  →  62% a.a.
🏷  Fonte: Caixa (financiável + FGTS)

[ Ver detalhes → radar.seudominio.com/deals/abc123 ]
```

### 9.2. Cooldown
Tabela `alerts_sent` impede reenvio do mesmo `(rule_id, property_id)` dentro do `cooldown_minutes`.

### 9.3. Regras default
- `score >= 80` → imediato
- `category = bank_owned AND score >= 70` → imediato
- `category = auction AND score >= 75 AND auction_date < now() + 7 dias` → imediato
- Resumo diário às 8h: top 10 do dia anterior.

---

## 10. Jobs e Agendamento

```python
# apps/api/radar/workers/schedule.py
schedules = [
    # Scraping
    ("0 6 * * *",  "scrape_caixa"),         # diário 6h
    ("0 */4 * * *", "scrape_olx"),          # a cada 4h
    ("0 8,14,20 * * *", "scrape_zap"),      # 3x ao dia
    ("0 7 * * *",  "scrape_leiloes"),       # diário 7h

    # Análise
    ("*/30 * * * *", "analyze_pending"),    # a cada 30min
    ("0 3 * * *",   "recompute_market_stats"),  # 3h da manhã

    # Alertas
    ("*/15 * * * *", "evaluate_alert_rules"),
    ("0 8 * * *",   "send_daily_digest"),

    # Manutenção
    ("0 4 * * 0",   "deactivate_stale_listings"),  # domingos
]
```

---

## 11. Roadmap

### Sprint 0 (semana 1) — Fundação
- [ ] Repo, CI básico, Dockerfiles
- [ ] Setup Railway (api, web, postgres, redis)
- [ ] Migrations iniciais (Alembic)
- [ ] Auth por token + middleware
- [ ] Skeleton FastAPI + Next.js conectados
- [ ] `investor_profile` + tela de settings

### Sprint 1 (semana 2-3) — Motor financeiro
- [ ] Modelos SQLAlchemy completos
- [ ] `services/analyzer.py` com fórmulas de custo, ROI, capital
- [ ] `services/scoring.py`
- [ ] Cadastro manual de imóvel (form + API)
- [ ] Tela de detalhe com 6 cenários
- [ ] Ranking básico

### Sprint 2 (semana 4-5) — Primeiros scrapers
- [ ] Scraper Caixa em produção
- [ ] Scraper OLX em produção
- [ ] Worker RQ + scheduler
- [ ] Dedup camada 1 (fingerprint)
- [ ] Logs de scrape_runs no painel

### Sprint 3 (semana 6) — Mercado
- [ ] `neighborhood_stats` (job de cálculo)
- [ ] Tela de mercado com heatmap
- [ ] Comparáveis na tela de detalhe
- [ ] Histórico de preço

### Sprint 4 (semana 7) — Alertas e polish
- [ ] Bot Telegram
- [ ] Regras de alerta + cooldown
- [ ] Digest diário
- [ ] Watchlist
- [ ] Filtros avançados no ranking

### Sprint 5 (semana 8+) — Expansão
- [ ] Zap/VivaReal
- [ ] 2-3 leiloeiros
- [ ] Dedup camada 2 (similaridade)
- [ ] Bancos (Santander, Itaú, BB)

### Backlog (pós-MVP)
- OCR de editais
- Análise de fotos com vision model (estima estado/reforma)
- Modelo ML de previsão de revenda
- Mapa de calor de oportunidades

---

## 12. Variáveis de ambiente

```bash
# .env.example
DATABASE_URL=postgresql://radar:radar@localhost:5432/radar
REDIS_URL=redis://localhost:6379/0

RADAR_API_TOKEN=troque-isso-por-algo-longo-e-aleatorio
RADAR_ALLOWED_IPS=                 # CSV opcional, vazio = qualquer IP

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

SENTRY_DSN=
LOG_LEVEL=INFO

# Web
NEXT_PUBLIC_API_URL=https://api.radar.seudominio.com
RADAR_API_TOKEN_WEB=                # mesmo token, usado server-side no Next
```

---

## 13. Decisões em aberto (revisar antes do código)

1. **Custo de capital:** taxa fixa (11% a.a.) ou Selic dinâmica via API do BCB?
2. **ITBI Florianópolis:** confirmar alíquota atual (era 3% / 0.5% para imóvel financiado pelo SFH).
3. **Reforma R$/m²:** validar com 2-3 empreiteiros locais antes de virar default.
4. **Liquidez:** definir como calcular (volume de anúncios ativos / tempo médio listado / queda média de preço).
5. **Cidades fase 1:** confirmar se entra Governador Celso Ramos já no MVP.

---

## 14. Próximo passo concreto

Criar o repositório com a estrutura da seção 2.3, subir os serviços vazios no Railway, rodar a primeira migration e validar o ciclo `cadastro manual → análise → ranking` antes de tocar em qualquer scraper. Esse loop fechado em ~3 dias destrava todo o resto.
