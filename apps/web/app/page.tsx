import { DealTable } from "../components/deal-table";
import { fetchDeals, formatCurrency } from "../lib/api";

export default async function DashboardPage() {
  const data = await fetchDeals();
  const totalProfit = data.items.reduce((sum, deal) => sum + Number(deal.estimated_profit), 0);
  const avgScore =
    data.items.length === 0
      ? 0
      : data.items.reduce((sum, deal) => sum + Number(deal.score), 0) / data.items.length;

  return (
    <main className="min-h-screen">
      <section className="border-b border-moss/20 bg-paper px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-sm font-semibold uppercase tracking-normal text-clay">Radar Imobiliário Floripa</p>
          <h1 className="mt-2 max-w-3xl text-4xl font-semibold leading-tight text-ink">
            Oportunidades acima do corte, com capital até R$ 300 mil.
          </h1>
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
          <DealTable deals={data.items} />
        </div>
      </section>
    </main>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-moss/20 bg-white p-4">
      <div className="text-sm text-ink/60">{label}</div>
      <div className="mt-2 text-3xl font-semibold">{value}</div>
    </div>
  );
}
