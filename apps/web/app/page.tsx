import type { ReactNode } from "react";
import { DealTable } from "../components/deal-table";
import { fetchDeals, formatCurrency } from "../lib/api";

type SearchParams = Record<string, string | string[] | undefined>;

type PageProps = {
  searchParams?: Promise<SearchParams>;
};

export default async function DashboardPage({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const filters = {
    min_score: numberParam(params.min_score, 50),
    max_capital: numberParam(params.max_capital, 300000),
    min_roi: numberParam(params.min_roi, 0),
    min_margin: numberParam(params.min_margin, 0),
    min_profit: numberParam(params.min_profit, 0),
    city: textParam(params.city),
    category: textParam(params.category),
    source: textParam(params.source),
    property_type: textParam(params.property_type),
    decision: textParam(params.decision),
    order_by: textParam(params.order_by) || "annualized_roi",
  };
  const data = await fetchDeals(filters);
  const totalProfit = data.items.reduce((sum, deal) => sum + Number(deal.estimated_profit), 0);
  const avgScore =
    data.items.length === 0
      ? 0
      : data.items.reduce((sum, deal) => sum + Number(deal.score), 0) / data.items.length;

  return (
    <main className="min-h-screen">
      <section className="border-b border-moss/20 px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <p className="text-sm font-semibold uppercase tracking-normal text-clay">Radar Imobiliário Floripa</p>
          <h1 className="mt-2 max-w-4xl text-4xl font-semibold leading-tight text-ink">
            Oportunidades acima do corte, com capital até R$ 300 mil.
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-ink/68">
            Use os filtros para separar capital, ROI, lucro, cidade, fonte e tipo de imovel. A nota privilegia
            retorno financeiro antes de volume ou preco baixo.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <Kpi label="Oportunidades" value={String(data.total)} />
            <Kpi label="Nota média" value={avgScore.toFixed(0)} />
            <Kpi label="Lucro potencial" value={formatCurrency(totalProfit)} />
          </div>
        </div>
      </section>

      <section className="px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold">Ranking</h2>
              <p className="mt-1 text-sm text-ink/70">
                Exibe apenas imóveis com nota mínima 50 e margem compatível com a tese.
              </p>
            </div>
          </div>
          <DealFilters filters={filters} />
          <DealTable deals={data.items} />
        </div>
      </section>
    </main>
  );
}

function DealFilters({ filters }: { filters: Record<string, string | number> }) {
  return (
    <form className="mb-5 border border-moss/20 bg-white p-4" method="get">
      <div className="grid gap-3 md:grid-cols-4 lg:grid-cols-6">
        <Field label="Nota min.">
          <input className="field" min="0" name="min_score" type="number" defaultValue={filters.min_score} />
        </Field>
        <Field label="Capital max.">
          <input className="field" min="0" name="max_capital" type="number" defaultValue={filters.max_capital} />
        </Field>
        <Field label="ROI a.a. min.">
          <input className="field" name="min_roi" type="number" defaultValue={filters.min_roi} />
        </Field>
        <Field label="Margem min.">
          <input className="field" name="min_margin" type="number" defaultValue={filters.min_margin} />
        </Field>
        <Field label="Lucro min.">
          <input className="field" name="min_profit" type="number" defaultValue={filters.min_profit} />
        </Field>
        <Field label="Ordenar por">
          <select className="field" name="order_by" defaultValue={filters.order_by}>
            <option value="annualized_roi">ROI a.a.</option>
            <option value="profit">Lucro</option>
            <option value="score">Nota</option>
            <option value="capital_required">Menor capital</option>
          </select>
        </Field>
        <Field label="Cidade">
          <select className="field" name="city" defaultValue={filters.city}>
            <option value="">Todas</option>
            <option value="Florianopolis">Florianopolis</option>
            <option value="Florianópolis">Florianopolis acentuado</option>
            <option value="Sao Jose">Sao Jose</option>
            <option value="São José">Sao Jose acentuado</option>
            <option value="Palhoca">Palhoca</option>
            <option value="Palhoça">Palhoca acentuado</option>
            <option value="Biguacu">Biguacu</option>
            <option value="Biguaçu">Biguacu acentuado</option>
          </select>
        </Field>
        <Field label="Tipo">
          <select className="field" name="property_type" defaultValue={filters.property_type}>
            <option value="">Todos</option>
            <option value="apartamento">Apartamento</option>
            <option value="casa">Casa</option>
            <option value="terreno">Terreno</option>
            <option value="imovel">Imovel</option>
          </select>
        </Field>
        <Field label="Categoria">
          <select className="field" name="category" defaultValue={filters.category}>
            <option value="">Todas</option>
            <option value="common">Anuncio comum</option>
            <option value="auction">Leilao</option>
            <option value="bank_owned">Retomado</option>
          </select>
        </Field>
        <Field label="Fonte">
          <select className="field" name="source" defaultValue={filters.source}>
            <option value="">Todas</option>
            <option value="brognoli">brognoli</option>
            <option value="chaves_na_mao">chaves_na_mao</option>
            <option value="loft">loft</option>
            <option value="mega_leiloes">mega_leiloes</option>
            <option value="quintoandar">quintoandar</option>
            <option value="superbid">superbid</option>
          </select>
        </Field>
        <Field label="Decisao">
          <select className="field" name="decision" defaultValue={filters.decision}>
            <option value="">Todas</option>
            <option value="priority">Prioridade</option>
            <option value="analyze">Analisar</option>
            <option value="monitor">Monitorar</option>
            <option value="discard">Descartar</option>
          </select>
        </Field>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="border border-moss bg-moss px-4 py-2 text-sm font-medium text-white" type="submit">
          Aplicar filtros
        </button>
        <a className="border border-moss/30 px-4 py-2 text-sm font-medium text-moss" href="/">
          Limpar
        </a>
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="text-xs font-medium text-ink/65">
      {label}
      {children}
    </label>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-moss/20 bg-white p-5 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-normal text-ink/50">{label}</div>
      <div className="mt-2 text-3xl font-semibold text-ink">{value}</div>
    </div>
  );
}

function textParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function numberParam(value: string | string[] | undefined, fallback: number) {
  const raw = textParam(value);
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}
