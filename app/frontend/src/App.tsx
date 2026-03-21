export function App() {
  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--fg-default)] font-[family-name:var(--font-sans)]">
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-6">
          <h1 className="text-3xl font-semibold tracking-tight">
            Stack Bench
          </h1>
          <p className="text-[var(--fg-muted)] text-sm">
            Frontend scaffold loaded.
          </p>
          <div className="flex gap-3 justify-center">
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--accent)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--green)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--red)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--purple)]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[var(--yellow)]" />
          </div>
          <p className="font-[family-name:var(--font-mono)] text-xs text-[var(--fg-subtle)]">
            v0.0.1 &middot; Vite + React + Tailwind 4
          </p>
        </div>
      </div>
    </div>
  );
}
