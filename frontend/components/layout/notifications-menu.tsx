'use client'

import { useCallback, useState } from 'react'
import Link from 'next/link'
import { Bell, CheckCheck, Cpu, Info, Sparkles } from 'lucide-react'
import { useDismissable } from '@/hooks/use-dismissable'
import { isApiConfigured } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const NOTIFICATIONS = [
  {
    id: 'model',
    icon: Cpu,
    tone: 'text-wc-amber bg-wc-amber/12',
    title: isApiConfigured ? 'Backend API configured' : 'Model integration pending',
    body: isApiConfigured
      ? 'The research backend URL is set. Results will come from the connected API.'
      : 'Connect the FastAPI backend via NEXT_PUBLIC_API_URL to enable analysis.',
    href: '/settings',
  },
  {
    id: 'welcome',
    icon: Sparkles,
    tone: 'text-wc-violet bg-wc-violet/12',
    title: 'Welcome to WeCure',
    body: 'The Skin Cancer research module is available as an initial prototype.',
    href: '/modules',
  },
  {
    id: 'disclaimer',
    icon: Info,
    tone: 'text-wc-cyan bg-wc-cyan/12',
    title: 'Research use only',
    body: 'Outputs are experimental and not intended for clinical decisions.',
    href: '/about',
  },
]

export function NotificationsMenu() {
  const [open, setOpen] = useState(false)
  const [read, setRead] = useState<string[]>([])
  const close = useCallback(() => setOpen(false), [])
  const ref = useDismissable<HTMLDivElement>(open, close)
  const unread = NOTIFICATIONS.filter((n) => !read.includes(n.id)).length

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
        className="relative flex size-10 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground transition-colors hover:text-foreground"
      >
        <Bell className="size-[18px]" aria-hidden />
        {unread > 0 && <span className="absolute top-2 right-2 size-2 rounded-full bg-wc-pink ring-2 ring-card" aria-hidden />}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="absolute top-12 right-0 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-2xl border border-border bg-popover p-2 text-popover-foreground shadow-xl shadow-slate-900/10 animate-in fade-in-0 zoom-in-95"
        >
          <div className="flex items-center justify-between px-3 py-2">
            <p className="text-sm font-semibold">Notifications</p>
            <button
              type="button"
              onClick={() => setRead(NOTIFICATIONS.map((n) => n.id))}
              className="inline-flex items-center gap-1 text-xs font-medium text-wc-teal hover:underline dark:text-wc-turquoise"
            >
              <CheckCheck className="size-3.5" aria-hidden />
              Mark all read
            </button>
          </div>
          <ul className="flex flex-col">
            {NOTIFICATIONS.map((n) => {
              const Icon = n.icon
              const isRead = read.includes(n.id)
              return (
                <li key={n.id}>
                  <Link
                    href={n.href}
                    onClick={() => {
                      setRead((r) => [...new Set([...r, n.id])])
                      setOpen(false)
                    }}
                    className="flex gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-muted"
                  >
                    <span className={cn('flex size-8 shrink-0 items-center justify-center rounded-lg', n.tone)}>
                      <Icon className="size-4" aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={cn('block text-sm', isRead ? 'font-medium text-muted-foreground' : 'font-semibold')}>{n.title}</span>
                      <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">{n.body}</span>
                    </span>
                    {!isRead && <span className="mt-1.5 size-2 shrink-0 rounded-full bg-wc-pink" aria-label="Unread" />}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
