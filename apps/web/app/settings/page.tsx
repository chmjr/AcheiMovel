export default function SettingsPage() {
  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-3xl font-semibold">Configurações</h1>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <Setting label="Capital máximo" value="R$ 300.000" />
          <Setting label="Lucro mínimo" value="R$ 80.000" />
          <Setting label="Margem mínima" value="30%" />
          <Setting label="Prazo máximo" value="12 meses" />
        </div>
      </div>
    </main>
  );
}

function Setting({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-moss/20 bg-white p-4">
      <div className="text-sm text-ink/60">{label}</div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
    </div>
  );
}
