import Link from "next/link";
import type { Deal } from "../lib/api";
import { formatCurrency, traduzirCategoria, traduzirDecisao } from "../lib/api";

export function DealTable({ deals }: { deals: Deal[] }) {
  if (deals.length === 0) {
    return (
      <div className="border border-dashed border-moss/30 bg-white p-8 text-center">
        Nenhuma oportunidade passou pelos cortes atuais.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-moss/20 bg-white">
      <table className="min-w-full border-collapse text-sm">
        <thead className="bg-moss text-left text-white">
          <tr>
            <th className="p-3">Nota</th>
            <th className="p-3">Imóvel</th>
            <th className="p-3">Cidade</th>
            <th className="p-3">Compra</th>
            <th className="p-3">Capital</th>
            <th className="p-3">Lucro</th>
            <th className="p-3">Margem</th>
            <th className="p-3">ROI a.a.</th>
            <th className="p-3">Origem</th>
            <th className="p-3">Decisão</th>
            <th className="p-3">Ação</th>
          </tr>
        </thead>
        <tbody>
          {deals.map((deal) => (
            <tr key={deal.property_id} className="border-t border-moss/10">
              <td className="p-3 text-lg font-semibold">{Number(deal.score).toFixed(0)}</td>
              <td className="p-3">
                <Link className="font-medium text-clay underline-offset-4 hover:underline" href={`/deals/${deal.property_id}`}>
                  {deal.title}
                </Link>
                <div className="text-xs text-ink/60">
                  {traduzirCategoria(deal.category)} - {deal.property_type}
                </div>
              </td>
              <td className="p-3">
                {deal.city}
                <div className="text-xs text-ink/60">{deal.neighborhood}</div>
              </td>
              <td className="p-3">{formatCurrency(deal.purchase_price)}</td>
              <td className="p-3">{formatCurrency(deal.capital_required)}</td>
              <td className="p-3">{formatCurrency(deal.estimated_profit)}</td>
              <td className="p-3">{Number(deal.margin_pct).toFixed(1)}%</td>
              <td className="p-3">{Number(deal.annualized_roi_pct).toFixed(1)}%</td>
              <td className="p-3">
                {deal.source_name}
                {deal.source_count > 1 && (
                  <div className="text-xs text-ink/50">{deal.source_count} fontes</div>
                )}
                {deal.is_demo && <div className="text-xs text-clay">Demonstração</div>}
              </td>
              <td className="p-3">{traduzirDecisao(deal.decision)}</td>
              <td className="p-3">
                <Link className="font-medium text-clay underline-offset-4 hover:underline" href={`/deals/${deal.property_id}`}>
                  Abrir análise
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
