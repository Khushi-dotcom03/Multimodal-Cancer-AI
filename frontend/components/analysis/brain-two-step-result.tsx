import type { ReactNode } from 'react'

export function BrainCancerScreeningStep({
  status,
  note,
}: {
  status: 'CANCER' | 'NON-CANCER'
  note: string
}) {
  const isCancer = status === 'CANCER'
  return (
    <section className={`rounded-xl border p-4 ${isCancer ? 'border-wc-violet/30 bg-wc-violet/5' : 'border-wc-turquoise/35 bg-wc-turquoise/8'}`} aria-label="Step 1 cancer screening">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">STEP 1 — CANCER SCREENING</p>
      <p className={`mt-1 text-2xl font-bold ${isCancer ? 'text-wc-violet' : 'text-wc-teal dark:text-wc-turquoise'}`}>{status}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{note}</p>
    </section>
  )
}

export function BrainClassificationStep({ title, note, children }: { title: string; note?: string; children?: ReactNode }) {
  return (
    <section className="rounded-xl border border-border p-4" aria-label="Step 2 cancer type or classification">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">STEP 2 — CANCER TYPE / CLASSIFICATION</p>
      <h3 className="mt-1 text-xl font-bold">{title}</h3>
      {note && <p className="mt-1 text-xs leading-5 text-muted-foreground">{note}</p>}
      {children && <div className="mt-4">{children}</div>}
    </section>
  )
}
