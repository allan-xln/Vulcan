import { platformPrinciples } from "@repo/domain";

import { PhaseOneOverview } from "@/components/phase-one-overview";

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-16 md:px-12">
      <section className="mx-auto grid max-w-6xl gap-8">
        <div className="rounded-[2rem] border border-ink/10 bg-white/70 p-10 shadow-[0_20px_80px_rgba(20,33,61,0.08)] backdrop-blur">
          <p className="text-sm uppercase tracking-[0.35em] text-accent">
            Phase 1 foundation
          </p>
          <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-tight">
            Telemetry control plane for auditable, tenant-isolated operational intelligence.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-ink/80">
            This repository starts with a minimal control-plane shell. Transactional truth
            lives in Supabase, telemetry analytics live in ClickHouse, and AI services only
            explain structured evidence.
          </p>
        </div>
        <aside className="rounded-[2rem] bg-ink p-8 text-canvas">
          <h2 className="text-xl font-semibold">Non-negotiable principles</h2>
          <ul className="mt-6 space-y-3 text-sm leading-6 text-canvas/85">
            {platformPrinciples.map((principle) => (
              <li key={principle}>{principle}</li>
            ))}
          </ul>
        </aside>
        <PhaseOneOverview />
      </section>
    </main>
  );
}
