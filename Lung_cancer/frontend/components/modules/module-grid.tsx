import Image from 'next/image'
import Link from 'next/link'
import { ArrowRight, Clock, ScanSearch } from 'lucide-react'
import { Badge } from '@/components/common/primitives'
import { ACCENT_STYLES } from '@/lib/modules'
import { cn } from '@/lib/utils'
import type { ResearchModule } from '@/types'

export function ModuleGrid({ modules }: { modules: ResearchModule[] }) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {modules.map((m) => (
        <li key={m.id}>
          <ModuleCard module={m} />
        </li>
      ))}
    </ul>
  )
}

export function ModuleCard({ module: m }: { module: ResearchModule }) {
  const accent = ACCENT_STYLES[m.accent]
  const available = m.status === 'available'

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm shadow-slate-900/[0.03] transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-900/8">
      <div className="relative aspect-[16/10] overflow-hidden bg-wc-navy">
        <Image
          src={m.image}
          alt={`${m.name} research illustration`}
          fill
          sizes="(min-width: 1280px) 25vw, (min-width: 640px) 50vw, 100vw"
          className={cn('object-cover transition-transform duration-500 group-hover:scale-105', !available && 'opacity-80 saturate-75')}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-wc-navy/70 via-transparent to-transparent" aria-hidden />
        <div className="absolute top-3 left-3">
          {available ? (
            <Badge tone="emerald" className="bg-emerald-500/90 text-white ring-0 dark:text-white">
              <span className="size-1.5 rounded-full bg-white" aria-hidden /> Available
            </Badge>
          ) : (
            <Badge tone="amber" className="bg-wc-navy/70 text-amber-200 ring-white/15 backdrop-blur dark:text-amber-200">
              <Clock className="size-3" aria-hidden /> Coming Soon
            </Badge>
          )}
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className={cn('size-2 rounded-full', accent.dot)} aria-hidden />
          <span className={accent.text}>{m.category}</span>
        </div>
        <div>
          <h3 className="text-lg font-semibold">{m.name}</h3>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground text-pretty">{m.description}</p>
        </div>
        <dl className="mt-auto flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <div className="flex gap-1">
            <dt className="sr-only">Status</dt>
            <dd>{m.statusLabel}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="sr-only">Imaging</dt>
            <dd>· {m.imaging}</dd>
          </div>
        </dl>
        {available ? (
          <Link
            href={m.href}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            <ScanSearch className="size-4" aria-hidden />
            Explore Module
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </Link>
        ) : (
          <button
            type="button"
            disabled
            aria-disabled
            className="inline-flex h-10 cursor-not-allowed items-center justify-center gap-2 rounded-xl border border-border bg-muted px-4 text-sm font-semibold text-muted-foreground"
          >
            <Clock className="size-4" aria-hidden />
            In Development
          </button>
        )}
      </div>
    </article>
  )
}
