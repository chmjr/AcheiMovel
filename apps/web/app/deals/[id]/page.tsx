import {
  fetchDeal,
  formatCurrency,
  traduzirCategoria,
  traduzirCenario,
  traduzirDecisao,
  traduzirModo,
  traduzirReforma,
  traduzirTipoImovel,
} from "../../../lib/api";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function DealDetailPage({ params }: PageProps) {
  const { id } = await params;
  const data = await fetchDeal(id);
  const analyses = data.analyses ?? [];
  const bestAnalysis = [...analyses].sort((a, b) => Number(b.score) - Number(a.score))[0];

  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <a className="text-sm text-clay underline-offset-4 hover:underline" href="/">
          ← Voltar ao ranking
        </a>

        <h1 className="mt-4 text-3xl font-semibold">
          {data.property?.title ?? "Imóvel não encontrado"}
        </h1>
        <p className="mt-1 text-ink/70">
          {data.property?.city} · {data.property?.neighborhood}
          {data.property?.area_privative ? ` · ${data.property.area_privative} m²` : ""}
          {data.property?.bedrooms ? ` · ${data.property.bedrooms} dorm.` : ""}
        </p>

        {/* Origin card */}
        {data.property ? (
          <section className="mt-6 border border-moss/20 bg-white p-5">
            <h2 className="text-xl font-semibold">Origem da oportunidade</h2>
            <div className="mt-3 grid gap-3 text-sm md:grid-cols-4">
              <Info label="Fonte" value={data.property.source_name} />
              <Info
                label="Categoria"
                value={traduzirCategoria(data.property.category)}
              />
              <Info
                label="Tipo"
                value={traduzirTipoImovel(data.property.property_type)}
              />
              <Info
                label="Fontes encontradas"
                value={String(data.property.source_count)}
              />
            </div>

            {data.property.is_demo ? (
              <p className="mt-4 border border-dashed border-clay/40 bg-paper p-3 text-sm text-ink/75">
                Massa de demonstração criada para validar o cálculo, o ranking e a navegação.
                Ainda não veio de OLX, Caixa, leiloeiro ou outro portal.
              </p>
            ) : data.property.source_url ? (
              <a
                className="mt-4 inline-block border border-clay px-4 py-2 font-medium text-clay underline-offset-4 hover:underline"
                href={data.property.source_url}
                rel="noreferrer"
                target="_blank"
              >
                Abrir anúncio original →
              </a>
            ) : (
              <p className="mt-4 text-sm text-ink/50">URL do anúncio não disponível.</p>
            )}
          </section>
        ) : null}

        {/* Best analysis summary */}
        {bestAnalysis ? (
          <section className="mt-6 grid gap-4 md:grid-cols-4">
            <ResumoItem label="Melhor nota" value={Number(bestAnalysis.score).toFixed(0)} />
            <ResumoItem label="Capital necessário" value={formatCurrency(bestAnalysis.capital_required)} />
            <ResumoItem label="Lucro estimado" value={formatCurrency(bestAnalysis.estimated_profit)} />
            <ResumoItem label="Decisão" value={traduzirDecisao(bestAnalysis.decision)} />
          </section>
        ) : null}

        {/* Reading guide */}
        <section className="mt-6 border border-moss/20 bg-white p-5">
          <h2 className="text-xl font-semibold">Como ler as simulações</h2>
          <p className="mt-2 text-sm text-ink/75">
            Cada linha combina um cenário de mercado, forma de compra e nível de reforma.
            Use primeiro a coluna &quot;Decisão&quot; e depois compare capital, lucro e retorno anualizado.
          </p>
          <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
            <Info label="Cenário" value="Conservador, base ou otimista para preço de revenda e prazo." />
            <Info label="Modo de compra" value="À vista usa mais caixa; financiado mede o capital que sai do bolso." />
            <Info label="Capital necessário" value="Entrada, reforma, taxas, custos até a venda e reserva de contingência." />
          </div>
        </section>

        {/* Analyses table */}
        <div className="mt-8 overflow-x-auto border border-moss/20 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-moss text-left text-white">
              <tr>
                <th className="p-3">Cenário</th>
                <th className="p-3">Compra</th>
                <th className="p-3">Reforma</th>
                <th className="p-3 text-right">Capital</th>
                <th className="p-3 text-right">Lucro</th>
                <th className="p-3 text-right">Margem</th>
                <th className="p-3 text-right">ROI a.a.</th>
                <th className="p-3 text-right">Prazo</th>
                <th className="p-3 text-right">Nota</th>
                <th className="p-3">Decisão</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((a, i) => {
                const isBest = a === bestAnalysis;
                return (
                  <tr key={i} className={`border-t border-moss/10 ${isBest ? "bg-paper" : ""}`}>
                    <td className="p-3">{traduzirCenario(a.scenario)}</td>
                    <td className="p-3">{traduzirModo(a.financing_mode)}</td>
                    <td className="p-3">{traduzirReforma(a.renovation_level)}</td>
                    <td className="p-3 text-right">{formatCurrency(a.capital_required)}</td>
                    <td className="p-3 text-right">{formatCurrency(a.estimated_profit)}</td>
                    <td className="p-3 text-right">{Number(a.margin_pct).toFixed(1)}%</td>
                    <td className="p-3 text-right">{Number(a.annualized_roi_pct).toFixed(1)}%</td>
                    <td className="p-3 text-right">{a.estimated_months} meses</td>
                    <td className="p-3 text-right font-semibold">{Number(a.score).toFixed(0)}</td>
                    <td className="p-3">
                      {traduzirDecisao(a.decision)}
                      {isBest && (
                        <div className="text-xs font-medium text-clay">Melhor simulação</div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Cost breakdown for best analysis */}
        {bestAnalysis && (
          <section className="mt-8 border border-moss/20 bg-white p-5">
            <h2 className="text-xl font-semibold">Composição do custo total — melhor simulação</h2>
            <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
              <CostItem label="Preço de compra" value={formatCurrency(bestAnalysis.purchase_price)} />
              <CostItem label="Reforma" value={formatCurrency(bestAnalysis.renovation_cost)} />
              <CostItem label="Custos de transação (ITBI + cartório)" value={formatCurrency(bestAnalysis.transaction_costs)} />
              <CostItem label="Custos de posse (condomínio + IPTU)" value={formatCurrency(bestAnalysis.holding_costs)} />
              <CostItem label="Custo de venda (comissão)" value={formatCurrency(bestAnalysis.selling_costs)} />
              <CostItem label="Contingência (12%)" value={formatCurrency(bestAnalysis.contingency)} />
            </div>
            <div className="mt-4 flex items-center justify-between border-t border-moss/20 pt-3 text-sm">
              <span className="font-semibold">Custo total</span>
              <span className="text-lg font-bold">{formatCurrency(bestAnalysis.total_cost)}</span>
            </div>
            <div className="mt-2 flex items-center justify-between text-sm">
              <span className="font-semibold">Valor de revenda estimado</span>
              <span className="text-lg font-bold text-moss">{formatCurrency(bestAnalysis.estimated_resale_value)}</span>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function ResumoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-moss/20 bg-white p-4">
      <div className="text-sm text-ink/55">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-ink/55">{label}</div>
      <div className="mt-1 font-medium">{value}</div>
    </div>
  );
}

function CostItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-paper p-3">
      <div className="text-xs text-ink/55">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}
