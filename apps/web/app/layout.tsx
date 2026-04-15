import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Radar Imobiliario Floripa",
  description: "Ranking pessoal de oportunidades imobiliarias em Floripa e regiao.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <nav className="sticky top-0 z-50 border-b border-moss/15 bg-white/92 px-6 py-3 shadow-sm backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <Link href="/" className="flex items-center gap-3 text-sm font-bold uppercase tracking-normal text-moss">
              <span className="flex h-8 w-8 items-center justify-center rounded border border-moss/25 bg-paper text-xs text-clay">
                RF
              </span>
              Radar Floripa
            </Link>
            <div className="flex gap-2 text-sm font-medium text-ink/70">
              <Link href="/" className="rounded px-3 py-2 hover:bg-paper hover:text-ink">Ranking</Link>
              <Link href="/market" className="rounded px-3 py-2 hover:bg-paper hover:text-ink">Mercado</Link>
              <Link href="/scrapers" className="rounded px-3 py-2 hover:bg-paper hover:text-ink">Scrapers</Link>
              <Link href="/settings" className="hover:text-ink">Configurações</Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
