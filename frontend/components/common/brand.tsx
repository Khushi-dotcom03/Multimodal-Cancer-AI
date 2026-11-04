import { FlaskConical, ShieldAlert } from 'lucide-react'
import { cn } from '@/lib/utils'

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'relative flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-xl brand-gradient text-white shadow-md shadow-wc-teal/25',
        className,
      )}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M7 3c0 4.5 10 6.5 10 11s-10 2.5-10 7" />
        <path d="M17 3c0 4.5-10 6.5-10 11s10 2.5 10 7" />
        <path d="M8.5 7h7M8.5 17h7" opacity="0.7" />
      </svg>
    </span>
  )
}

export function Logo({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      {!collapsed && (
        <span className="flex flex-col leading-none">
          <span className="text-lg font-bold tracking-tight">
            We<span className="text-wc-teal dark:text-wc-turquoise">Cure</span>
          </span>
          <span className="mt-1 text-[10px] font-medium tracking-wider text-muted-foreground uppercase">Explore · Analyze · Advance</span>
        </span>
      )}
    </span>
  )
}

export const RESEARCH_DISCLAIMER =
  'This platform is an academic AI research prototype. Its outputs are experimental and are not intended for clinical diagnosis or treatment decisions. All medical decisions must be made by qualified healthcare professionals.'

export function ResearchDisclaimer({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <div
      role="note"
      className={cn(
        'flex gap-3 rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm text-amber-900 dark:text-amber-100',
        className,
      )}
    >
      <ShieldAlert className="mt-0.5 size-4.5 shrink-0 text-wc-amber" aria-hidden />
      <div>
        {!compact && <p className="font-semibold">Research Disclaimer</p>}
        <p className={cn('leading-relaxed text-pretty', !compact && 'mt-0.5 text-amber-800/90 dark:text-amber-100/80')}>{RESEARCH_DISCLAIMER}</p>
      </div>
    </div>
  )
}

export function DemoBanner({ message }: { message?: string }) {
  return (
    <div
      role="status"
      className="flex items-center gap-2.5 rounded-xl border border-wc-violet/30 bg-wc-violet/8 px-4 py-2.5 text-sm text-violet-900 dark:text-violet-100"
    >
      <FlaskConical className="size-4 shrink-0 text-wc-violet" aria-hidden />
      <span>
        <span className="font-semibold">Demo Mode — </span>
        {message ?? 'Values shown are illustrative placeholders for UI testing only, not real results.'}
      </span>
    </div>
  )
}
