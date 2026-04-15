import { fetchMarketStats, formatSqm, traduzirTipoImovel } from "../../lib/api";

export default async function MarketPage() {
  const data = await fetchMarketStats();

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Mercado</p>
        <h1 className="mt-2 text-3xl font-semibold">Estatísticas por bairro</h1>
        <p className="mt-2 text-sm text-ink/70">
          Preço mediano por m² calculado a partir dos anúncios ativos coletados pelos scrapers.
          {data.total === 0
            ? " Nenhum dado disponível ainda — rode um scraper para popular."
            : ` ${data.total} grupos calculados.`}
        </p>

        {data.total === 0 ? (
          <EmptyState />
        ) : (
          <div className="mt-8 overflow-x-auto rounded border border-moss/20 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="bg-moss text-left text-white">
                <tr>
                  <th className="p-3">Cidade</th>
                  <th className="p-3">Bairro</th>
                  <th className="p-3">Tipo</th>
                  <th className="p-3 text-right">Amostras</th>
                  <th className="p-3 text-right">P25 (m²)</th>
                  <th className="p-3 text-right">P50 mediana (m²)</th>
                  <th className="p-3 text-right">P65 (m²)</th>
                  <th className="p-3 text-right">P75 (m²)</th>
                  <th className="p-3 text-right">Liquidez</th>
                  <th className="p-3">Atualizado</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((stat, i) => (
                  <tr key={i} className="border-t border-moss/10 hover:bg-paper/60">
                    <td className="p-3">{stat.city}</td>
                    <td className="p-3 font-medium">{stat.neighborhood}</td>
                    <td className="p-3 text-ink/70">{traduzirTipoImovel(stat.property_type)}</td>
                    <td className="p-3 text-right text-ink/70">{stat.sample_size}</td>
                    <td className="p-3 text-right">{formatSqm(stat.price_per_sqm_p25)}</td>
                    <td className="p-3 text-right font-semibold">{formatSqm(stat.price_per_sqm_p50)}</td>
                    <td className="p-3 text-right">{formatSqm(stat.price_per_sqm_p65)}</td>
                    <td className="p-3 text-right">{formatSqm(stat.price_per_sqm_p75)}</td>
                    <td className="p-3 text-right">
                      <LiquidityBadge score={stat.liquidity_score} />
                    </td>
                    <td className="p-3 text-xs text-ink/50">
                      {stat.computed_at ? new Date(stat.computed_at).toLocaleDateString("pt-BR") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <section className="mt-8 rounded border border-moss/20 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold">Como interpretar</h2>
          <div className="mt-3 grid gap-4 text-sm md:grid-cols-3">
            <Info
              label="P50 — mediana"
              value="Metade dos imóveis do bairro é vendida abaixo desse valor por m². Referência principal para o preço de mercado."
            />
            <Info
              label="P65 — faixa superior"
              value="Patamar pós-reforma, usado na estimativa de revenda. Imóveis reformados e bem posicionados atingem esse percentil."
            />
            <Info
              label="Liquidez"
              value="Índice de 0 a 10 baseado no volume de anúncios ativos. Quanto maior, mais fácil revender o imóvel."
            />
          </div>
        </section>
      </div>
    </main>
  );
}

function LiquidityBadge({ score }: { score: string | null }) {
  if (!score) return <span className="text-ink/40">—</span>;
  const n = Number(score);
  const color =
    n >= 7 ? "bg-green-100 text-green-800" : n >= 4 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-700";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${color}`}>
      {n.toFixed(1)}
    </span>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-semibold text-ink">{label}</div>
      <div className="mt-1 text-ink/70">{value}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mt-8 rounded border border-dashed border-moss/40 bg-paper p-8 text-center">
      <p className="text-lg font-semibold text-ink/70">Nenhuma estatística disponível</p>
      <p className="mt-2 text-sm text-ink/50">
        Acione qualquer scraper via <code className="rounded bg-moss/10 px-1">POST /api/v1/scrapers/&lt;fonte&gt;/trigger</code>
        {" "}e o sistema calculará os percentis automaticamente após a coleta.
      </p>
    </div>
  );
}
