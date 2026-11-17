import Link from 'next/link'
import { ArrowUpRight, BarChart3, BookOpen, FileText, ImageUp, Zap } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/common/primitives'
import { cn } from '@/lib/utils'

const ACTIONS = [
  { label: 'Upload Medical Image', description: 'Start a skin image analysis', href: '/analysis', icon: ImageUp, tone: 'bg-wc-turquoise/12 text-wc-teal dark:text-wc-turquoise' },
  { label: 'Explore Research', description: 'Browse the research library', href: '/library', icon: BookOpen, tone: 'bg-wc-violet/12 text-wc-violet' },
  { label: 'View Reports', description: 'Manage research reports', href: '/reports', icon: FileText, tone: 'bg-wc-pink/12 text-wc-pink' },
  { label: 'Open Research Dashboard', description: 'Model evaluation & analytics', href: '/dashboard', icon: BarChart3, tone: 'bg-wc-blue/12 text-wc-blue' },
]

export function QuickActions() {
  return (
    <Panel className="h-full">
      <PanelHeader title="Quick Actions" description="Jump into common research tasks." icon={Zap} />
      <ul className="grid gap-2 p-5 sm:grid-cols-2 sm:p-6 xl:grid-cols-1">
        {ACTIONS.map((a) => {
          const Icon = a.icon
          return (
            <li key={a.label}>
              <Link
                href={a.href}
                className="group flex items-center gap-3 rounded-xl border border-border p-3 transition-all hover:-translate-y-0.5 hover:border-ring/40 hover:shadow-md hover:shadow-slate-900/5"
              >
                <span className={cn('flex size-10 shrink-0 items-center justify-center rounded-xl', a.tone)}>
                  <Icon className="size-[18px]" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold">{a.label}</span>
                  <span className="block truncate text-xs text-muted-foreground">{a.description}</span>
                </span>
                <ArrowUpRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden />
              </Link>
            </li>
          )
        })}
      </ul>
    </Panel>
  )
}
