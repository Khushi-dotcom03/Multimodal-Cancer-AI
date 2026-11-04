'use client'

import Link from 'next/link'
import { Menu, Settings } from 'lucide-react'
import { LogoMark } from '@/components/common/brand'
import { GlobalSearch } from './global-search'
import { NotificationsMenu } from './notifications-menu'
import { ProfileMenu } from './profile-menu'
import { ThemeToggle } from './theme-toggle'

export function TopNav({ onOpenMobileNav, mobileNavOpen }: { onOpenMobileNav: () => void; mobileNavOpen: boolean }) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={onOpenMobileNav}
          className="flex size-10 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground hover:text-foreground lg:hidden"
          aria-label="Open navigation"
          aria-expanded={mobileNavOpen}
          aria-controls="mobile-sidebar"
        >
          <Menu className="size-5" />
        </button>
        <Link href="/" className="sm:hidden" aria-label="WeCure home">
          <LogoMark className="size-8" />
        </Link>

        <GlobalSearch />

        <div className="ml-auto flex items-center gap-2">
          <NotificationsMenu />
          <ThemeToggle />
          <Link
            href="/settings"
            className="hidden size-10 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground transition-colors hover:text-foreground sm:flex"
            aria-label="Settings"
            title="Settings"
          >
            <Settings className="size-[18px]" />
          </Link>
          <ProfileMenu />
        </div>
      </div>
    </header>
  )
}
