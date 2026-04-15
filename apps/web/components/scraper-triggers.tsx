"use client";

import { useState, useTransition } from "react";
import { triggerScraper, triggerFullAnalysis } from "../app/scrapers/actions";

type Scraper = { id: string; label: string; category: string };
type Status = "idle" | "queued" | "error";

export function ScraperTriggers({ scrapers, backendOk }: { scrapers: Scraper[]; backendOk: boolean }) {
  const [statusMap, setStatusMap] = useState<Record<string, Status>>({});
  const [errorMap, setErrorMap] = useState<Record<string, string>>({});
  const [analysisPending, setAnalysisPending] = useState(false);
  const [, startTransition] = useTransition();

  function setStatus(source: string, s: Status, err?: string) {
    setStatusMap((prev) => ({ ...prev, [source]: s }));
    if (err) setErrorMap((prev) => ({ ...prev, [source]: err }));
  }

  function trigger(source: string) {
    setStatus(source, "idle");
    startTransition(async () => {
      const result = await triggerScraper(source);
      if (result.status === "queued") {
        setStatus(source, "queued");
        setTimeout(() => setStatus(source, "idle"), 5000);
      } else {
        setStatus(source, "error", result.error ?? "Resposta inesperada do servidor");
        setTimeout(() => setStatus(source, "idle"), 8000);
      }
    });
  }

  function runAnalysis() {
    setAnalysisPending(true);
    startTransition(async () => {
      await triggerFullAnalysis();
      setTimeout(() => setAnalysisPending(false), 5000);
    });
  }

  const categories = [...new Set(scrapers.map((s) => s.category))];

  return (
    <div className="space-y-6">
      {/* Backend status banner */}
      {!backendOk && (
        <div className="border border-red-300 bg-red-50 p-4 text-sm text-red-800">
          <strong>Backend inacessível.</strong> Verifique se o servidor FastAPI está rodando em{" "}
          <code className="rounded bg-red-100 px-1">localhost:8000</code>.
          <br />
          <span className="mt-1 block text-xs">
            Comando: <code>cd apps/api &amp;&amp; uvicorn radar.main:app --reload</code>
          </span>
        </div>
      )}

      {/* Full pipeline button */}
      <div className="flex items-center gap-4 rounded border border-moss/20 bg-white p-5 shadow-sm">
        <div className="flex-1">
          <p className="font-semibold">Analisar tudo</p>
          <p className="text-sm text-ink/60">
            Recalcula percentis de mercado e roda as análises financeiras para todos os imóveis coletados.
          </p>
        </div>
        <button
          onClick={runAnalysis}
          disabled={!backendOk || analysisPending}
          className="shrink-0 rounded border border-moss bg-moss px-5 py-2 text-sm font-medium text-white hover:bg-moss/90 disabled:opacity-50"
        >
          {analysisPending ? "Processando…" : "Rodar análise"}
        </button>
      </div>

      {/* Scrapers by category */}
      {categories.map((cat) => (
        <div key={cat}>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-normal text-ink/50">{cat}</h3>
          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
            {scrapers
              .filter((s) => s.category === cat)
              .map((scraper) => {
                const status = statusMap[scraper.id] ?? "idle";
                const errMsg = errorMap[scraper.id];
                return (
                  <div key={scraper.id} className="rounded border border-moss/20 bg-white px-4 py-3 shadow-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{scraper.label}</span>
                      <button
                        onClick={() => trigger(scraper.id)}
                        disabled={!backendOk || status === "queued"}
                        className={`ml-3 shrink-0 rounded border px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                          status === "error"
                            ? "border-red-400 text-red-600"
                            : status === "queued"
                            ? "border-moss/40 text-moss"
                            : "border-clay text-clay hover:bg-clay hover:text-white"
                        }`}
                      >
                        {status === "queued" ? "Disparado ✓" : status === "error" ? "Erro" : "Disparar"}
                      </button>
                    </div>
                    {status === "error" && errMsg && (
                      <p className="mt-1 text-xs text-red-600 break-all">{errMsg}</p>
                    )}
                  </div>
                );
              })}
          </div>
        </div>
      ))}
    </div>
  );
}
