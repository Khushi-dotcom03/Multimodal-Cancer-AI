'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronsLeft, ChevronsRight, Users, X } from 'lucide-react'
import { Logo } from '@/components/common/brand'
import { isActivePath, MAIN_NAV, SECONDARY_NAV, type NavItem } from '@/lib/navigation'
import { cn } from '@/lib/utils'

interface AppSidebarProps {
  collapsed: boolean
  onToggleCollapsed?: () => void
  onClose?: () => void
}

export function AppSidebar({ collapsed, onToggleCollapsed, onClose }: AppSidebarProps) {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col">
      <div className={cn('flex h-16 items-center border-b border-sidebar-border', collapsed ? 'justify-center px-2' : 'justify-between px-5')}>
        <Link href="/" aria-label="WeCure home" className="rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
          <Logo collapsed={collapsed} />
        </Link>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="flex size-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close navigation"
          >
            <X className="size-5" />
          </button>
        )}
      </div>

      <nav aria-label="Primary" className="flex-1 overflow-y-auto px-3 py-4">
        {!collapsed && <p className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">Research</p>}
        <ul className="flex flex-col gap-1">
          {MAIN_NAV.map((item) => (
            <SidebarLink key={item.href} item={item} active={isActivePath(pathname, item.href)} collapsed={collapsed} />
          ))}
        </ul>
        <div className="my-4 h-px bg-sidebar-border" />
        <ul className="flex flex-col gap-1">
          {SECONDARY_NAV.map((item) => (
            <SidebarLink key={item.href} item={item} active={isActivePath(pathname, item.href)} collapsed={collapsed} />
          ))}
        </ul>
      </nav>

      <div className="flex flex-col gap-3 border-t border-sidebar-border p-3">
        {!collapsed && (
          <div className="relative overflow-hidden rounded-2xl bg-wc-navy p-4 text-white">
            <div className="pointer-events-none absolute -top-10 -right-10 size-32 rounded-full bg-wc-magenta/40 blur-2xl" aria-hidden />
            <div className="pointer-events-none absolute -bottom-12 -left-8 size-32 rounded-full bg-wc-turquoise/40 blur-2xl" aria-hidden />
            <div className="relative">
              <span className="flex size-8 items-center justify-center rounded-lg bg-white/10">
                <Users className="size-4" aria-hidden />
              </span>
              <p className="mt-3 text-sm font-semibold">Research Together</p>
              <p className="mt-1 text-xs leading-relaxed text-white/70">
                Invite collaborators to explore modules and share research reports.
              </p>
              <Link
                href="/about#team"
                className="mt-3 inline-flex h-8 items-center rounded-lg bg-white px-3 text-xs font-semibold text-wc-navy transition-opacity hover:opacity-90"
              >
                Learn more
              </Link>
            </div>
          </div>
        )}

        <div className={cn('flex items-center gap-3 rounded-xl p-2', collapsed && 'justify-center')}>
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-wc-violet to-wc-pink text-sm font-semibold text-white" aria-hidden>
            RU
          </span>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">Research User</p>
              <p className="truncate text-xs text-muted-foreground">Guest workspace</p>
            </div>
          )}
        </div>

        {onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="flex h-9 items-center justify-center gap-2 rounded-lg text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
            {!collapsed && <span>Collapse</span>}
          </button>
        )}
      </div>
    </div>
  )
}

function SidebarLink({ item, active, collapsed }: { item: NavItem; active: boolean; collapsed: boolean }) {
  const Icon = item.icon
  return (
    <li>
      <Link
        href={item.href}
        aria-current={active ? 'page' : undefined}
        title={collapsed ? item.label : undefined}
        className={cn(
          'group relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
          collapsed && 'justify-center px-0',
          active
            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
        )}
      >
        {active && <span className="absolute top-2 bottom-2 left-0 w-1 rounded-r-full bg-wc-turquoise" aria-hidden />}
        <Icon className={cn('size-[18px] shrink-0', active && 'text-wc-teal dark:text-wc-turquoise')} aria-hidden />
        {collapsed ? <span className="sr-only">{item.label}</span> : <span className="truncate">{item.label}</span>}
      </Link>
    </li>
  )
}
