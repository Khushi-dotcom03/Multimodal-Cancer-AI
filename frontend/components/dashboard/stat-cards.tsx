'use client'

import { Activity, Cpu, FileText, Layers, type LucideIcon } from 'lucide-react'
import { Badge, Panel } from '@/components/common/primitives'
import { useDemoMode } from '@/components/providers'
import { isApiConfigured } from '@/lib/api-client'
import { DEMO_REPORTS } from '@/lib/demo-data'
import { RESEARCH_MODULES } from '@/lib/modules'
import { cn } from '@/lib/utils'

interface Stat {
  label: string
  value: string
  note: string
  icon: LucideIcon
  iconClass: string
  glow: string
  live: boolean
}

export function StatCards() {
  const { demoMode } = useDemoMode()
  const available = RESEARCH_MODULES.filter((m) => m.status === 'available').length

  const stats: Stat[] = [
    {
      label: 'Total Research Analyses',
      value: demoMode ? '120' : '0',
      note: demoMode ? 'Demo value' : 'No analyses recorded yet',
      icon: Activity,
      iconClass: 'bg-wc-blue/12 text-wc-blue',
      glow: 'from-wc-blue/15',
      live: false,
    },
    {
      label: 'Available Research Modules',
      value: `${available} / ${RESEARCH_MODULES.length}`,
      note: `${RESEARCH_MODULES.length - available} modules coming soon`,
      icon: Layers,
      iconClass: 'bg-wc-turquoise/12 text-wc-teal dark:text-wc-turquoise',
      glow: 'from-wc-turquoise/15',
      live: true,
    },
    {
      label: 'Models Integrated',
      value: '0',
      note: isApiConfigured ? 'Awaiting model registration' : 'Model integration pending',
      icon: Cpu,
      iconClass: 'bg-wc-violet/12 text-wc-violet',
      glow: 'from-wc-violet/15',
      live: true,
    },
    {
      label: 'Research Reports',
      value: demoMode ? String(DEMO_REPORTS.length) : '0',
      note: demoMode ? 'Demo value' : 'No reports generated yet',
      icon: FileText,
      iconClass: 'bg-wc-pink/12 text-wc-pink',
      glow: 'from-wc-pink/15',
      live: false,
    },
  ]

  return (
    <section aria-label="Platform statistics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((s) => {
        const Icon = s.icon
        return (
          <Panel key={s.label} className="relative overflow-hidden p-5">
            <div className={cn('pointer-events-none absolute -top-12 -right-12 size-32 rounded-full bg-gradient-to-br to-transparent blur-2xl', s.glow)} aria-hidden />
            <div className="relative flex items-start justify-between gap-3">
              <span className={cn('flex size-11 items-center justify-center rounded-xl', s.iconClass)}>
                <Icon className="size-5" aria-hidden />
              </span>
              {demoMode && !s.live && <Badge tone="violet">Demo</Badge>}
            </div>
            <p className="relative mt-4 text-sm font-medium text-muted-foreground">{s.label}</p>
            <p className="relative mt-1 font-mono text-3xl font-bold tracking-tight">{s.value}</p>
            <p className="relative mt-1 text-xs text-muted-foreground">{s.note}</p>
          </Panel>
        )
      })}
    </section>
  )
}
