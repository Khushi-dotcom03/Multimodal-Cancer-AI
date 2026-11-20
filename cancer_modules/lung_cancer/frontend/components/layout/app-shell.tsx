'use client'

import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { AppSidebar } from './app-sidebar'
import { TopNav } from './top-nav'

const COLLAPSE_KEY = 'wecure-sidebar-collapsed'

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    setCollapsed(localStorage.getItem(COLLAPSE_KEY) === 'true')
  }, [])

  useEffect(() => {
    setMobileOpen(false)
  }, [pathname])

  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMobileOpen(false)
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [mobileOpen])

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      localStorage.setItem(COLLAPSE_KEY, String(!prev))
      return !prev
    })
  }

  return (
    <div className="min-h-dvh">
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-30 hidden border-r border-sidebar-border bg-sidebar transition-[width] duration-300 lg:block',
          collapsed ? 'w-[76px]' : 'w-[264px]',
        )}
      >
        <AppSidebar collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />
      </aside>

      <div
        className={cn('fixed inset-0 z-40 lg:hidden', mobileOpen ? 'pointer-events-auto' : 'pointer-events-none')}
        aria-hidden={!mobileOpen}
      >
        <div
          className={cn('absolute inset-0 bg-wc-navy/50 backdrop-blur-sm transition-opacity', mobileOpen ? 'opacity-100' : 'opacity-0')}
          onClick={() => setMobileOpen(false)}
        />
        <aside
          id="mobile-sidebar"
          aria-label="Main navigation"
          className={cn(
            'absolute inset-y-0 left-0 w-[284px] max-w-[85vw] border-r border-sidebar-border bg-sidebar shadow-2xl transition-transform duration-300',
            mobileOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <AppSidebar collapsed={false} onClose={() => setMobileOpen(false)} />
        </aside>
      </div>

      <div className={cn('flex min-h-dvh flex-col transition-[padding] duration-300', collapsed ? 'lg:pl-[76px]' : 'lg:pl-[264px]')}>
        <TopNav onOpenMobileNav={() => setMobileOpen(true)} mobileNavOpen={mobileOpen} />
        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </main>
        <footer className="border-t border-border px-4 py-5 text-center text-xs text-muted-foreground sm:px-6 lg:px-8">
          WeCure · Academic AI research prototype · Not for clinical diagnosis or treatment decisions.
        </footer>
      </div>
    </div>
  )
}
