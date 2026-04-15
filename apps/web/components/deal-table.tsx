"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Deal } from "../lib/api";
import { formatCurrency, traduzirCategoria, traduzirDecisao } from "../lib/api";

type SortKey =
  | "score"
  | "title"
  | "city"
  | "purchase_price"
  | "capital_required"
  | "estimated_profit"
  | "margin_pct"
  | "annualized_roi_pct"
  | "source_name"
  | "decision";

type SortDirection = "asc" | "desc";

const SORTERS: Record<SortKey, (deal: Deal) => string | number> = {
  score: (deal) => Number(deal.score),
  title: (deal) => deal.title,
  city: (deal) => deal.city,
  purchase_price: (deal) => Number(deal.purchase_price),
  capital_required: (deal) => Number(deal.capital_required),
  estimated_profit: (deal) => Number(deal.estimated_profit),
  margin_pct: (deal) => Number(deal.margin_pct),
  annualized_roi_pct: (deal) => Number(deal.annualized_roi_pct),
  source_name: (deal) => deal.source_name,
  decision: (deal) => deal.decision,
};

export function DealTable({ deals }: { deals: Deal[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("annualized_roi_pct");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [quickFilter, setQuickFilter] = useState("");
  const [minRoi, setMinRoi] = useState("");
  const [minProfit, setMinProfit] = useState("");

  const visibleDeals = useMemo(() => {
    const normalizedFilter = quickFilter.trim().toLowerCase();
    const roi = Number(minRoi);
    const profit = Number(minProfit);

    return [...deals]
      .filter((deal) => {
        if (normalizedFilter) {
          const haystack = [
            deal.title,
            deal.city,
            deal.neighborhood,
            deal.source_name,
            deal.property_type,
            deal.category,
            deal.decision,
          ]
            .join(" ")
            .toLowerCase();
          if (!haystack.includes(normalizedFilter)) return false;
        }
        if (minRoi && Number(deal.annualized_roi_pct) < roi) return false;
        if (minProfit && Number(deal.estimated_profit) < profit) return false;
        return true;
      })
      .sort((a, b) => {
        const left = SORTERS[sortKey](a);
        const right = SORTERS[sortKey](b);
        const modifier = sortDirection === "asc" ? 1 : -1;

        if (typeof left === "number" && typeof right === "number") {
          return (left - right) * modifier;
        }
        return String(left).localeCompare(String(right), "pt-BR") * modifier;
      });
  }, [deals, minProfit, minRoi, quickFilter, sortDirection, sortKey]);

  function changeSort(nextKey: SortKey) {
    if (nextKey === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection("desc");
  }

  if (deals.length === 0) {
    return (
      <div className="border border-dashed border-moss/30 bg-white p-8 text-center">
        Nenhuma oportunidade passou pelos cortes atuais.
      </div>
    );
  }

  return (
    <div className="border border-moss/20 bg-white">
      <div className="grid gap-3 border-b border-moss/10 p-4 md:grid-cols-4">
        <label className="text-xs font-medium text-ink/65 md:col-span-2">
          Buscar na tabela
          <input
            className="field"
            placeholder="bairro, cidade, fonte, tipo..."
            value={quickFilter}
            onChange={(event) => setQuickFilter(event.target.value)}
          />
        </label>
        <label className="text-xs font-medium text-ink/65">
          ROI a.a. minimo
          <input className="field" type="number" value={minRoi} onChange={(event) => setMinRoi(event.target.value)} />
        </label>
        <label className="text-xs font-medium text-ink/65">
          Lucro minimo
          <input className="field" type="number" value={minProfit} onChange={(event) => setMinProfit(event.target.value)} />
        </label>
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-moss/10 px-4 py-3 text-xs text-ink/60">
        <span>
          {visibleDeals.length} de {deals.length} imoveis
        </span>
        <span>
          Clique nos cabecalhos para ordenar. Ordem atual: {headerLabel(sortKey)}{" "}
          {sortDirection === "asc" ? "crescente" : "decrescente"}.
        </span>
      </div>

      <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead className="bg-moss text-left text-white">
          <tr>
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Nota" sortKey="score" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Imovel" sortKey="title" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Cidade" sortKey="city" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Compra" sortKey="purchase_price" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Capital" sortKey="capital_required" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Lucro" sortKey="estimated_profit" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Margem" sortKey="margin_pct" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="ROI a.a." sortKey="annualized_roi_pct" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Origem" sortKey="source_name" onSort={changeSort} />
            <SortHeader activeKey={sortKey} direction={sortDirection} label="Decisao" sortKey="decision" onSort={changeSort} />
            <th className="p-3">Acao</th>
          </tr>
        </thead>
        <tbody>
          {visibleDeals.map((deal) => (
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
    </div>
  );
}

function SortHeader({
  activeKey,
  direction,
  label,
  sortKey,
  onSort,
}: {
  activeKey: SortKey;
  direction: SortDirection;
  label: string;
  sortKey: SortKey;
  onSort: (key: SortKey) => void;
}) {
  const active = activeKey === sortKey;
  return (
    <th className="p-0">
      <button
        className="flex min-h-12 w-full items-center gap-1 px-3 py-2 text-left font-semibold"
        type="button"
        onClick={() => onSort(sortKey)}
      >
        {label}
        <span className="text-xs opacity-80">{active ? (direction === "asc" ? "^" : "v") : "<>"}</span>
      </button>
    </th>
  );
}

function headerLabel(key: SortKey) {
  return (
    {
      score: "nota",
      title: "imovel",
      city: "cidade",
      purchase_price: "compra",
      capital_required: "capital",
      estimated_profit: "lucro",
      margin_pct: "margem",
      annualized_roi_pct: "ROI a.a.",
      source_name: "origem",
      decision: "decisao",
    }[key] ?? key
  );
}


