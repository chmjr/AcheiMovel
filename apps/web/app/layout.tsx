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
        <nav className="sticky top-0 z-50 border-b border-moss/20 bg-white px-6 py-3">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <Link href="/" className="text-sm font-bold uppercase tracking-widest text-moss">
              Radar Floripa
            </Link>
            <div className="flex gap-6 text-sm font-medium text-ink/70">
              <Link href="/" className="hover:text-ink">Ranking</Link>
              <Link href="/market" className="hover:text-ink">Mercado</Link>
              <Link href="/scrapers" className="hover:text-ink">Scrapers</Link>
              <Link href="/settings" className="hover:text-ink">Configurações</Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
