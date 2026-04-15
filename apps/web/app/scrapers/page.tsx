import { ScraperTriggers } from "../../components/scraper-triggers";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.RADAR_API_TOKEN_WEB ?? "dev-token";

const SCRAPERS = [
  { id: "lanceja",          label: "Lance Já",         category: "Leilão" },
  { id: "superbid",         label: "Superbid",          category: "Leilão" },
  { id: "leiloeiro-publico",label: "Leiloeiro Público", category: "Leilão" },
  { id: "mega-leiloes",     label: "Mega Leilões",      category: "Leilão" },
  { id: "caixa",            label: "Caixa (bloqueado)", category: "Banco" },
  { id: "brognoli",         label: "Brognoli",          category: "Imobiliárias" },
  { id: "chaves-na-mao",    label: "Chaves na Mão",     category: "Imobiliárias" },
  { id: "olx",              label: "OLX",               category: "Portais" },
  { id: "vivareal",         label: "Viva Real",         category: "Portais" },
  { id: "zap",              label: "ZAP Imóveis",       category: "Portais" },
  { id: "loft",             label: "Loft",              category: "Portais" },
  { id: "quintoandar",      label: "Quinto Andar",      category: "Portais" },
  { id: "imovelweb",        label: "Imovelweb",         category: "Portais" },
];

type Run = {
  id: string;
  source: string;
  status: string;
  items_collected: number | null;
  items_new: number | null;
  items_updated: number | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
};

async function checkBackend(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

async function fetchRuns(): Promise<Run[]> {
  try {
    const res = await fetch(`${API_URL}/api/v1/scrapers/runs`, {
      headers: { "X-Radar-Token": API_TOKEN },
      cache: "no-store",
    });
    const data = await res.json();
    return data.items ?? [];
  } catch {
    return [];
  }
}

export default async function ScrapersPage() {
  const [runs, backendOk] = await Promise.all([fetchRuns(), checkBackend()]);

  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Coleta</p>
        <h1 className="mt-2 text-3xl font-semibold">Scrapers</h1>
        <p className="mt-2 text-sm text-ink/70">
          Dispare uma ou mais fontes. O sistema coleta os imóveis, calcula estatísticas de mercado
          e gera as análises financeiras automaticamente em seguida.
        </p>

        <div className="mt-8">
          <ScraperTriggers scrapers={SCRAPERS} backendOk={backendOk} />
        </div>

        {/* Run history */}
        <section className="mt-10">
          <h2 className="text-xl font-semibold">Histórico de coletas</h2>
          {runs.length === 0 ? (
            <p className="mt-4 text-sm text-ink/50">
              Nenhuma coleta registrada ainda. Dispare um scraper acima.
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto border border-moss/20 bg-white">
              <table className="min-w-full text-sm">
                <thead className="bg-moss text-left text-white">
                  <tr>
                    <th className="p-3">Fonte</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Coletados</th>
                    <th className="p-3 text-right">Novos</th>
                    <th className="p-3 text-right">Atualizados</th>
                    <th className="p-3">Início</th>
                    <th className="p-3">Duração</th>
                    <th className="p-3">Erro</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => {
                    const duration =
                      run.finished_at && run.started_at
                        ? Math.round(
                            (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000
                          ) + "s"
                        : "—";
                    return (
                      <tr key={run.id} className="border-t border-moss/10">
                        <td className="p-3 font-medium">{run.source}</td>
                        <td className="p-3">
                          <StatusBadge status={run.status} />
                        </td>
                        <td className="p-3 text-right">{run.items_collected ?? "—"}</td>
                        <td className="p-3 text-right text-moss font-medium">{run.items_new ?? "—"}</td>
                        <td className="p-3 text-right">{run.items_updated ?? "—"}</td>
                        <td className="p-3 text-ink/60">
                          {new Date(run.started_at).toLocaleString("pt-BR", {
                            day: "2-digit",
                            month: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="p-3 text-ink/60">{duration}</td>
                        <td className="max-w-xs truncate p-3 text-xs text-red-600">{run.error ?? ""}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    success: "bg-green-100 text-green-800",
    partial: "bg-yellow-100 text-yellow-800",
    running: "bg-blue-100 text-blue-800",
    failed:  "bg-red-100  text-red-700",
  };
  const labels: Record<string, string> = {
    success: "Sucesso",
    partial: "Parcial",
    running: "Rodando",
    failed:  "Falhou",
  };
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${styles[status] ?? "bg-gray-100 text-gray-600"}`}>
      {labels[status] ?? status}
    </span>
  );
}
