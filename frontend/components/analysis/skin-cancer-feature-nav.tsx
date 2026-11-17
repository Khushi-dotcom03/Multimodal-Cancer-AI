'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, FileImage, Stethoscope } from 'lucide-react'
import { cn } from '@/lib/utils'

const FEATURES = [
  { href: '/image-analysis', label: 'Image Analysis', icon: FileImage },
  { href: '/clinical-analysis', label: 'Clinical Analysis', icon: Stethoscope },
  { href: '/analysis', label: 'Combined Analysis', icon: Activity },
]

export function SkinCancerFeatureNav() {
  const pathname = usePathname()

  return (
    <nav aria-label="Cancer analysis modules" className="-mx-1 overflow-x-auto px-1">
      <ul className="flex min-w-max gap-2 border-b border-border">
        {FEATURES.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'inline-flex min-h-10 items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors',
                  active ? 'border-wc-turquoise text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="size-4" aria-hidden />
                {label}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
