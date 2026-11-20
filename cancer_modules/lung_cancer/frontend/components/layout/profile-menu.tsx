'use client'

import { useCallback, useState } from 'react'
import Link from 'next/link'
import { ChevronDown, Info, Monitor, Moon, Settings, Sun, User } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useDismissable } from '@/hooks/use-dismissable'
import { cn } from '@/lib/utils'
import { useMounted } from './theme-toggle'

const THEMES = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
] as const

export function ProfileMenu() {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const ref = useDismissable<HTMLDivElement>(open, close)
  const { theme, setTheme } = useTheme()
  const mounted = useMounted()

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Open profile menu"
        className="flex h-10 items-center gap-2 rounded-xl border border-border bg-card pr-2 pl-1 transition-colors hover:bg-muted"
      >
        <span className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-wc-violet to-wc-pink text-xs font-semibold text-white" aria-hidden>
          RU
        </span>
        <ChevronDown className={cn('hidden size-4 text-muted-foreground transition-transform sm:block', open && 'rotate-180')} aria-hidden />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute top-12 right-0 z-50 w-64 rounded-2xl border border-border bg-popover p-2 text-popover-foreground shadow-xl shadow-slate-900/10 animate-in fade-in-0 zoom-in-95"
        >
          <div className="flex items-center gap-3 px-3 py-2.5">
            <span className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-wc-violet to-wc-pink text-sm font-semibold text-white" aria-hidden>
              RU
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">Research User</p>
              <p className="truncate text-xs text-muted-foreground">Guest workspace</p>
            </div>
          </div>
          <div className="my-1 h-px bg-border" />
          <MenuLink href="/settings" icon={User} label="Profile" onClick={close} />
          <MenuLink href="/settings" icon={Settings} label="Settings" onClick={close} />
          <MenuLink href="/about" icon={Info} label="About WeCure" onClick={close} />
          <div className="my-1 h-px bg-border" />
          <p className="px-3 pt-1.5 pb-1 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">Theme</p>
          <div className="grid grid-cols-3 gap-1 p-1" role="group" aria-label="Theme">
            {THEMES.map((t) => {
              const Icon = t.icon
              const active = mounted && theme === t.value
              return (
                <button
                  key={t.value}
                  type="button"
                  role="menuitemradio"
                  aria-checked={active}
                  onClick={() => setTheme(t.value)}
                  className={cn(
                    'flex flex-col items-center gap-1 rounded-lg py-2 text-xs font-medium transition-colors',
                    active ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                >
                  <Icon className="size-4" aria-hidden />
                  {t.label}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function MenuLink({ href, icon: Icon, label, onClick }: { href: string; icon: typeof User; label: string; onClick: () => void }) {
  return (
    <Link href={href} role="menuitem" onClick={onClick} className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-muted">
      <Icon className="size-4 text-muted-foreground" aria-hidden />
      {label}
    </Link>
  )
}
