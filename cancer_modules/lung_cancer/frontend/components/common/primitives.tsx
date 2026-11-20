import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Panel({ className, ...props }: React.ComponentProps<'section'>) {
  return (
    <section
      className={cn('rounded-2xl border border-border bg-card text-card-foreground shadow-sm shadow-slate-900/[0.03] transition-colors', className)}
      {...props}
    />
  )
}

export function PanelHeader({
  title,
  description,
  icon: Icon,
  action,
  className,
}: {
  title: string
  description?: string
  icon?: LucideIcon
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex items-start justify-between gap-4 p-5 pb-0 sm:p-6 sm:pb-0', className)}>
      <div className="flex items-start gap-3">
        {Icon && (
          <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-foreground">
            <Icon className="size-4.5" aria-hidden />
          </span>
        )}
        <div>
          <h2 className="text-base font-semibold text-balance">{title}</h2>
          {description && <p className="mt-0.5 text-sm text-muted-foreground text-pretty">{description}</p>}
        </div>
      </div>
      {action}
    </div>
  )
}

type Tone = 'teal' | 'emerald' | 'amber' | 'violet' | 'blue' | 'pink' | 'cyan' | 'neutral' | 'red'

const TONES: Record<Tone, string> = {
  teal: 'bg-wc-turquoise/12 text-wc-teal ring-wc-turquoise/30 dark:text-wc-turquoise',
  emerald: 'bg-wc-emerald/12 text-emerald-700 ring-wc-emerald/30 dark:text-emerald-300',
  amber: 'bg-wc-amber/12 text-amber-700 ring-wc-amber/30 dark:text-amber-300',
  violet: 'bg-wc-violet/12 text-violet-700 ring-wc-violet/30 dark:text-violet-300',
  blue: 'bg-wc-blue/12 text-blue-700 ring-wc-blue/30 dark:text-blue-300',
  pink: 'bg-wc-pink/12 text-pink-700 ring-wc-pink/30 dark:text-pink-300',
  cyan: 'bg-wc-cyan/12 text-cyan-700 ring-wc-cyan/30 dark:text-cyan-300',
  red: 'bg-red-500/12 text-red-700 ring-red-500/30 dark:text-red-300',
  neutral: 'bg-muted text-muted-foreground ring-border',
}

export function Badge({ tone = 'neutral', className, children }: { tone?: Tone; className?: string; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: LucideIcon
  title: string
  description: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center rounded-xl border border-dashed border-border px-6 py-10 text-center', className)}>
      <span className="flex size-11 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
        <Icon className="size-5" aria-hidden />
      </span>
      <p className="mt-3 text-sm font-semibold">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground text-pretty">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: React.ReactNode
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        {eyebrow && <p className="text-xs font-semibold tracking-wider text-wc-teal uppercase dark:text-wc-turquoise">{eyebrow}</p>}
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-balance sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 text-sm leading-relaxed text-muted-foreground text-pretty sm:text-base">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

export function Switch({
  checked,
  onCheckedChange,
  label,
  id,
}: {
  checked: boolean
  onCheckedChange: (value: boolean) => void
  label: string
  id?: string
}) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
        checked ? 'bg-primary' : 'bg-muted ring-1 ring-inset ring-border',
      )}
    >
      <span
        className={cn(
          'inline-block size-5 rounded-full bg-white shadow-sm transition-transform',
          checked ? 'translate-x-5.5' : 'translate-x-0.5',
        )}
      />
    </button>
  )
}

export const inputClass =
  'h-10 w-full rounded-xl border border-input bg-card px-3 text-sm text-foreground placeholder:text-muted-foreground outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30'
