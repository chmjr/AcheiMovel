export type Deal = {
  property_id: string;
  title: string;
  score: string;
  decision: string;
  category: string;
  city: string;
  neighborhood: string;
  property_type: string;
  purchase_price: string;
  estimated_market_value: string;
  estimated_resale_value: string;
  renovation_cost: string;
  total_cost: string;
  capital_required: string;
  estimated_profit: string;
  margin_pct: string;
  roi_pct: string;
  annualized_roi_pct: string;
  estimated_months: number;
  risk_level: string;
  source_name: string;
  primary_source_url?: string;
  is_demo: boolean;
  source_count: number;
};

export type DealListResponse = {
  items: Deal[];
  total: number;
  facets: Record<string, Record<string, number>>;
};

export type DealAnalysis = {
  scenario: string;
  financing_mode: string;
  renovation_level: string;
  purchase_price: string;
  estimated_market_value: string;
  estimated_resale_value: string;
  renovation_cost: string;
  transaction_costs: string;
  holding_costs: string;
  selling_costs: string;
  contingency: string;
  total_cost: string;
  capital_required: string;
  estimated_profit: string;
  margin_pct: string;
  roi_pct: string;
  annualized_roi_pct: string;
  estimated_months: number;
  risk_level: string;
  risk_flags: string[];
  score: string;
  decision: string;
  score_breakdown: Record<string, number>;
};

export type DealProperty = {
  property_id: string;
  title: string;
  city: string;
  neighborhood: string;
  property_type: string;
  category: string;
  area_privative: string | null;
  bedrooms: number | null;
  bathrooms: number | null;
  parking_spots: number | null;
  floor: number | null;
  has_elevator: boolean | null;
  source_name: string;
  source_url: string | null;
  source_count: number;
  is_demo: boolean;
};

export type DealDetailResponse = {
  property: DealProperty | null;
  analyses: DealAnalysis[];
};

export type NeighborhoodStat = {
  city: string;
  neighborhood: string;
  property_type: string;
  sample_size: number;
  price_per_sqm_p25: string | null;
  price_per_sqm_p50: string | null;
  price_per_sqm_p65: string | null;
  price_per_sqm_p75: string | null;
  liquidity_score: string | null;
  computed_at: string | null;
};

export type MarketStatsResponse = {
  items: NeighborhoodStat[];
  total: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.RADAR_API_TOKEN_WEB ?? "dev-token";

function headers() {
  return { "X-Radar-Token": API_TOKEN };
}

export async function fetchDeals(params?: {
  min_score?: number;
  max_capital?: number;
  city?: string;
  category?: string;
  order_by?: string;
}): Promise<DealListResponse> {
  const qs = new URLSearchParams({ min_score: String(params?.min_score ?? 50) });
  if (params?.max_capital) qs.set("max_capital", String(params.max_capital));
  if (params?.city) qs.set("city", params.city);
  if (params?.category) qs.set("category", params.category);
  if (params?.order_by) qs.set("order_by", params.order_by);

  const response = await fetch(`${API_URL}/api/v1/deals?${qs}`, {
    headers: headers(),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Falha ao carregar oportunidades: ${response.status}`);
  }
  return response.json();
}

export async function fetchDeal(id: string): Promise<DealDetailResponse> {
  const response = await fetch(`${API_URL}/api/v1/deals/${id}`, {
    headers: headers(),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Falha ao carregar imóvel: ${response.status}`);
  }
  return response.json();
}

export async function fetchMarketStats(params?: {
  city?: string;
  property_type?: string;
}): Promise<MarketStatsResponse> {
  const qs = new URLSearchParams();
  if (params?.city) qs.set("city", params.city);
  if (params?.property_type) qs.set("property_type", params.property_type);

  const response = await fetch(`${API_URL}/api/v1/market/stats?${qs}`, {
    headers: headers(),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Falha ao carregar estatísticas de mercado: ${response.status}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

export function formatCurrency(value: string | number) {
  return Number(value).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

export function formatSqm(value: string | number | null | undefined) {
  if (value == null) return "—";
  return `R$ ${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}/m²`;
}

export function traduzirCategoria(value: string) {
  return (
    {
      common: "Anúncio comum",
      bank_owned: "Retomado por banco",
      auction: "Leilão",
    }[value] ?? value
  );
}

export function traduzirDecisao(value: string) {
  return (
    {
      discard: "Descartar",
      monitor: "Monitorar",
      analyze: "Analisar",
      priority: "Prioridade",
      immediate: "Ação imediata",
    }[value] ?? value
  );
}

export function traduzirModo(value: string) {
  return (
    {
      cash: "À vista",
      financed: "Financiado",
    }[value] ?? value
  );
}

export function traduzirCenario(value: string) {
  return (
    {
      conservative: "Conservador",
      base: "Base",
      optimistic: "Otimista",
    }[value] ?? value
  );
}

export function traduzirReforma(value: string) {
  return (
    {
      light: "Leve",
      medium: "Média",
    }[value] ?? value
  );
}

export function traduzirTipoImovel(value: string) {
  return (
    {
      apartamento: "Apartamento",
      casa: "Casa",
      terreno: "Terreno",
      comercial: "Comercial",
      imovel: "Imóvel",
    }[value] ?? value
  );
}
